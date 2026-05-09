from typing import Optional, Sequence

from sqlalchemy import select

from loyalty_bot.domain.models import City

from .base import AbstractRepository


class CityRepository(AbstractRepository[City]):
    model = City

    async def get_all(self) -> Sequence[City]:
        stmt = select(City).order_by(City.name.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, city_id: int) -> Optional[City]:
        return await self.get(city_id)

    async def get_by_name(self, name: str) -> Optional[City]:
        stmt = select(City).where(City.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
