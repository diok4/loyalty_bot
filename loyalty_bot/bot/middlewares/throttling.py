from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from redis.asyncio import Redis

from loyalty_bot.core.config import settings
from loyalty_bot.core.logger import get_logger

logger = get_logger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """1 запрос/сек на telegram_id через Redis SET NX EX."""

    def __init__(
        self,
        redis: Redis,
        rate_seconds: float = settings.THROTTLE_RATE_SECONDS,
    ) -> None:
        self.redis = redis
        self.rate_seconds = rate_seconds

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        key = f"throttle:{user.id}"
        # SET NX EX: True если ключа не было — пропускаем; False — троттлим.
        acquired = await self.redis.set(
            key, "1", nx=True, ex=max(1, int(self.rate_seconds))
        )
        if not acquired:
            logger.info("throttled", telegram_id=user.id)
            if isinstance(event, Message):
                await event.answer("⏳ Слишком много запросов. Попробуйте через секунду.")
            return None
        return await handler(event, data)
