from datetime import datetime
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, update

from loyalty_bot.core.logger import get_logger
from loyalty_bot.domain.models import Notification, NotificationStatus

from .base import AbstractRepository

logger = get_logger(__name__)


class NotificationRepository(AbstractRepository[Notification]):
    model = Notification

    async def create(
        self, text_body: str, scheduled_at: datetime, created_by_tg_id: int
    ) -> Notification:
        notif = Notification(
            text_body=text_body,
            scheduled_at=scheduled_at,
            created_by_tg_id=created_by_tg_id,
            status=NotificationStatus.PENDING.value,
        )
        await self.add(notif)
        logger.info(
            "notification_scheduled",
            id=str(notif.id),
            scheduled_at=scheduled_at.isoformat(),
        )
        return notif

    async def list_recent(self, limit: int = 10) -> Sequence[Notification]:
        stmt = (
            select(Notification)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def claim_due(self, now: datetime) -> Optional[Notification]:
        """
        Атомарно "захватывает" одну созревшую pending-рассылку, переводя её
        в статус 'sending'. Возвращает None если очередь пуста.

        SELECT ... FOR UPDATE SKIP LOCKED + UPDATE гарантирует, что одна и та
        же рассылка не уйдёт двум воркерам, если запустим горизонтально.
        """
        stmt = (
            select(Notification)
            .where(
                Notification.status == NotificationStatus.PENDING.value,
                Notification.scheduled_at <= now,
            )
            .order_by(Notification.scheduled_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)
        notif = result.scalar_one_or_none()
        if notif is None:
            return None

        notif.status = NotificationStatus.SENDING.value
        await self.session.flush()
        return notif

    async def mark_sent(
        self, notification_id: UUID, sent_count: int, failed_count: int
    ) -> None:
        stmt = (
            update(Notification)
            .where(Notification.id == notification_id)
            .values(
                status=NotificationStatus.SENT.value,
                sent_count=sent_count,
                failed_count=failed_count,
                sent_at=datetime.now(tz=None).astimezone(),
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def mark_failed(self, notification_id: UUID) -> None:
        stmt = (
            update(Notification)
            .where(Notification.id == notification_id)
            .values(status=NotificationStatus.FAILED.value)
        )
        await self.session.execute(stmt)
        await self.session.flush()
