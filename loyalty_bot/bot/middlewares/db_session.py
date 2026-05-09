from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from loyalty_bot.core.database import session_factory
from loyalty_bot.core.logger import get_logger

logger = get_logger(__name__)


class DbSessionMiddleware(BaseMiddleware):
    """Открывает AsyncSession на handler, коммитит при успехе, rollback на исключении."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with session_factory() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                logger.exception("handler_failed_rollback")
                raise
