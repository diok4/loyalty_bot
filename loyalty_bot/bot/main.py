import asyncio
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from loyalty_bot.bot.handlers import (
    admin,
    auth,
    bonuses,
    card,
    notifications,
    profile,
    registration,
    start,
)
from loyalty_bot.bot.middlewares.admin_auth import AdminAuthMiddleware
from loyalty_bot.bot.middlewares.db_session import DbSessionMiddleware
from loyalty_bot.bot.middlewares.throttling import ThrottlingMiddleware
from loyalty_bot.core.config import settings
from loyalty_bot.core.database import dispose_engine, session_factory
from loyalty_bot.core.logger import configure_logging, get_logger
from loyalty_bot.services.admin_auth import AdminAuth
from loyalty_bot.services.notification_service import NotificationBroadcaster

configure_logging()
logger = get_logger(__name__)


def _build_dispatcher(
    redis: Redis,
    broadcaster: NotificationBroadcaster,
    admin_auth: AdminAuth,
) -> Dispatcher:
    storage = RedisStorage(redis=redis)
    dp = Dispatcher(storage=storage)

    # DI через workflow_data — доступно в хендлерах как параметры с такими же именами.
    dp["broadcaster"] = broadcaster

    # Middleware: db_session инжектит session, admin_auth — is_admin/auth.
    # Throttling ставим раньше — отбивает флуд до тяжёлых операций.
    dp.message.middleware(ThrottlingMiddleware(redis=redis))
    dp.callback_query.middleware(ThrottlingMiddleware(redis=redis))
    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(AdminAuthMiddleware(admin_auth))

    dp.include_router(auth.router)              # /login
    dp.include_router(start.router)
    dp.include_router(registration.router)
    dp.include_router(admin.router)
    dp.include_router(notifications.router)
    dp.include_router(card.router)
    dp.include_router(bonuses.router)
    dp.include_router(profile.router)
    return dp


async def main() -> None:
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)

    admin_auth = AdminAuth(redis=redis)
    broadcaster = NotificationBroadcaster(bot=bot, session_factory=session_factory)
    dp = _build_dispatcher(redis, broadcaster, admin_auth)

    dispatch_task = asyncio.create_task(broadcaster.dispatch_loop(poll_interval=30.0))

    logger.info("bot_started", env=settings.ENV)
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("bot_shutting_down")
        dispatch_task.cancel()
        with suppress(asyncio.CancelledError):
            await dispatch_task
        with suppress(Exception):
            await bot.session.close()
        with suppress(Exception):
            await redis.aclose()
        await dispose_engine()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("bot_stopped")
