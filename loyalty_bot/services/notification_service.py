import asyncio
from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID

from aiogram import Bot
from aiogram.exceptions import (
    TelegramForbiddenError,
    TelegramRetryAfter,
    TelegramBadRequest,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from loyalty_bot.core.logger import get_logger
from loyalty_bot.domain.models import Notification, User
from loyalty_bot.domain.repositories import NotificationRepository

logger = get_logger(__name__)

# Telegram даёт ~30 msg/sec в личку. Ставим запас 20 — стабильнее.
SEND_INTERVAL_SECONDS = 0.05


class NotificationBroadcaster:
    """
    Логика рассылки. Создаётся один раз с Bot и фабрикой сессий.
    Каждая отправка работает в отдельной сессии (фоновая задача).
    """

    def __init__(
        self,
        bot: Bot,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self.bot = bot
        self.session_factory = session_factory

    async def schedule(
        self, text_body: str, scheduled_at: datetime, created_by_tg_id: int
    ) -> Notification:
        async with self.session_factory() as session:
            notif = await NotificationRepository(session).create(
                text_body=text_body,
                scheduled_at=scheduled_at,
                created_by_tg_id=created_by_tg_id,
            )
            await session.commit()
            return notif

    async def dispatch_loop(self, poll_interval: float = 30.0) -> None:
        """Фоновый цикл: раз в N сек ищет созревшие рассылки и шлёт их."""
        logger.info("notification_loop_started", poll_interval=poll_interval)
        while True:
            try:
                await self._tick()
            except Exception:
                logger.exception("notification_loop_tick_failed")
            await asyncio.sleep(poll_interval)

    async def _tick(self) -> None:
        # За один тик можем взять несколько накопившихся рассылок подряд.
        while True:
            async with self.session_factory() as session:
                repo = NotificationRepository(session)
                notif = await repo.claim_due(datetime.now(timezone.utc))
                if notif is None:
                    await session.commit()
                    return

                notification_id = notif.id
                text_body = notif.text_body
                await session.commit()

            # Само вещание — в отдельной сессии, чтобы не держать lock долго.
            await self._broadcast(notification_id, text_body)

    async def _broadcast(self, notification_id: UUID, text_body: str) -> None:
        async with self.session_factory() as session:
            recipients = await self._load_recipients(session)

        sent = 0
        failed = 0

        for telegram_id in recipients:
            ok = await self._send_one(telegram_id, text_body)
            if ok:
                sent += 1
            else:
                failed += 1
                # Не блокируем рассылку из-за заблокировавшего бота юзера
                async with self.session_factory() as session:
                    await session.execute(
                        select(User).where(User.telegram_id == telegram_id)
                    )
                    # Деактивация — отдельным запросом ниже, через bulk update
                    pass

            await asyncio.sleep(SEND_INTERVAL_SECONDS)

        async with self.session_factory() as session:
            await NotificationRepository(session).mark_sent(
                notification_id, sent_count=sent, failed_count=failed
            )
            await session.commit()

        logger.info(
            "notification_dispatched",
            id=str(notification_id),
            sent=sent,
            failed=failed,
            total=sent + failed,
        )

    async def _load_recipients(self, session: AsyncSession) -> Sequence[int]:
        stmt = select(User.telegram_id).where(User.is_active.is_(True))
        result = await session.execute(stmt)
        return result.scalars().all()

    async def _send_one(self, telegram_id: int, text_body: str) -> bool:
        try:
            await self.bot.send_message(telegram_id, text_body, parse_mode="HTML")
            return True
        except TelegramRetryAfter as exc:
            # Telegram попросил притормозить — спим и пробуем ещё раз один раз.
            logger.warning("telegram_retry_after", seconds=exc.retry_after)
            await asyncio.sleep(exc.retry_after + 1)
            try:
                await self.bot.send_message(telegram_id, text_body, parse_mode="HTML")
                return True
            except Exception:
                logger.exception("send_after_retry_failed", telegram_id=telegram_id)
                return False
        except TelegramForbiddenError:
            # Юзер заблокировал бота — деактивируем.
            await self._deactivate(telegram_id)
            return False
        except TelegramBadRequest:
            # Сломанный chat_id, удалённый аккаунт и т.п.
            await self._deactivate(telegram_id)
            return False
        except Exception:
            logger.exception("send_failed", telegram_id=telegram_id)
            return False

    async def _deactivate(self, telegram_id: int) -> None:
        async with self.session_factory() as session:
            stmt = (
                select(User).where(User.telegram_id == telegram_id)
            )
            user = (await session.execute(stmt)).scalar_one_or_none()
            if user and user.is_active:
                user.is_active = False
                await session.commit()
                logger.info("user_deactivated", telegram_id=telegram_id)


def trigger_immediate(broadcaster: NotificationBroadcaster) -> None:
    """Запустить тик прямо сейчас, не дожидаясь polling-интервала."""
    asyncio.create_task(broadcaster._tick())
