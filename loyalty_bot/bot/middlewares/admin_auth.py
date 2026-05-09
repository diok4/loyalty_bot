from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from loyalty_bot.services.admin_auth import AdminAuth


class AdminAuthMiddleware(BaseMiddleware):
    """Кладёт в data:
       - is_admin: bool — текущий статус юзера
       - auth: AdminAuth — для хендлеров /logadmin и кнопки выхода
    """

    def __init__(self, auth: AdminAuth) -> None:
        self.auth = auth

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        data["auth"] = self.auth
        data["is_admin"] = bool(user and await self.auth.is_admin(user.id))
        return await handler(event, data)
