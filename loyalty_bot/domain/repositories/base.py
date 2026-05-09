from abc import ABC
from typing import Any, Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from loyalty_bot.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class AbstractRepository(ABC, Generic[ModelT]):
    """
    Базовый репозиторий. Не вызывает commit/rollback —
    это ответственность middleware/сервиса (unit of work).
    flush() используется только когда нужны server-side значения до commit'а.
    """

    model: Type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        if not hasattr(self, "model"):
            raise TypeError(
                f"{self.__class__.__name__} must define class attribute `model`"
            )
        self.session = session

    async def get(self, entity_id: Any) -> Optional[ModelT]:
        return await self.session.get(self.model, entity_id)

    async def list_all(self, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()
