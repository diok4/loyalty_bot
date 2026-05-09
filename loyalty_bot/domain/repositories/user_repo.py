from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from loyalty_bot.core.logger import get_logger
from loyalty_bot.domain.models import User
from loyalty_bot.domain.schemas import UserCreate, UserUpdate

from .base import AbstractRepository

logger = get_logger(__name__)


class UserRepository(AbstractRepository[User]):
    model = User

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        return await self.get(user_id)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        stmt = (
            select(User)
            .where(User.telegram_id == telegram_id)
            .options(selectinload(User.card))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[User]:
        stmt = (
            select(User)
            .where(User.phone == phone)
            .options(selectinload(User.card))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: UserCreate) -> User:
        user = User(
            telegram_id=data.telegram_id,
            phone=data.phone,
            full_name=data.full_name,
            gender=data.gender,
            city_id=data.city_id,
            language=data.language,
        )
        await self.add(user)
        logger.info("user_created", user_id=str(user.id), telegram_id=user.telegram_id)
        return user

    async def update(self, user: User, data: UserUpdate) -> User:
        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(user, field, value)
        await self.session.flush()
        await self.session.refresh(user)
        logger.info("user_updated", user_id=str(user.id), fields=list(changes.keys()))
        return user
