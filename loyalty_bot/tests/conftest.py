import asyncio
import os
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Дефолты до импорта settings
os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://loyalty_user:test@localhost:5432/loyalty_test",
)
os.environ.setdefault("ADMIN_IDS", "1")

from loyalty_bot.core.database import Base  # noqa: E402
import loyalty_bot.domain.models  # noqa: F401, E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    from loyalty_bot.core.config import settings

    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.fixture
def tmp_storage(tmp_path: Path) -> Path:
    p = tmp_path / "barcodes"
    p.mkdir()
    return p
