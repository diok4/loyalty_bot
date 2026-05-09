from redis.asyncio import Redis

from loyalty_bot.core.config import settings
from loyalty_bot.core.logger import get_logger

logger = get_logger(__name__)


class AdminAuth:
    """
    Логин/логаут админов через креды + проверка статуса.

    Хранит активные сессии в Redis (admin:session:<tg_id> → "1" с TTL).
    Статические админы из settings.ADMIN_IDS — всегда админы, независимо от сессии.
    """

    SESSION_KEY_PREFIX = "admin:session:"

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def login(
        self, telegram_id: int, username: str, password: str
    ) -> bool:
        if (
            username != settings.ADMIN_USERNAME
            or password != settings.ADMIN_PASSWORD
        ):
            logger.warning("admin_login_failed", telegram_id=telegram_id, username=username)
            return False

        await self.redis.set(
            self._key(telegram_id),
            "1",
            ex=settings.ADMIN_SESSION_TTL_SECONDS,
        )
        logger.info("admin_login_success", telegram_id=telegram_id)
        return True

    async def logout(self, telegram_id: int) -> None:
        await self.redis.delete(self._key(telegram_id))
        logger.info("admin_logout", telegram_id=telegram_id)

    async def is_admin(self, telegram_id: int) -> bool:
        # Статические админы из ENV — всегда true (для аварийного доступа)
        if telegram_id in settings.ADMIN_IDS:
            return True
        return bool(await self.redis.exists(self._key(telegram_id)))

    def _key(self, telegram_id: int) -> str:
        return f"{self.SESSION_KEY_PREFIX}{telegram_id}"
