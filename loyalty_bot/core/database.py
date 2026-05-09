from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import settings
from .logger import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей домена."""


def _build_engine() -> AsyncEngine:
    return create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=settings.DB_POOL_RECYCLE,
        echo=not settings.is_production,
    )


engine: AsyncEngine = _build_engine()

session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Контекстный менеджер для скриптов/воркеров. В хендлерах сессию инжектит middleware."""
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("db_session_rollback")
        raise
    finally:
        await session.close()


async def dispose_engine() -> None:
    await engine.dispose()
    logger.info("db_engine_disposed")
