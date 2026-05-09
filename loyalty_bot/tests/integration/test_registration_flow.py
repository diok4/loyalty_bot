"""
Интеграционный тест happy-path регистрации.
Aiogram 3.x не имеет встроенного TestClient — гоняем сервисный слой.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from loyalty_bot.domain.models import City
from loyalty_bot.domain.repositories import CardRepository, UserRepository
from loyalty_bot.domain.schemas import UserCreate
from loyalty_bot.services.barcode_service import BarcodeService
from loyalty_bot.services.bitrix_service import BitrixService
from loyalty_bot.services.card_service import CardService
from loyalty_bot.services.user_service import UserService


@pytest.mark.asyncio
async def test_full_registration_flow(session: AsyncSession, tmp_storage):
    session.add(City(id=1, name="Ташкент"))
    await session.commit()

    user_repo = UserRepository(session)
    card_repo = CardRepository(session)
    service = UserService(
        user_repo,
        CardService(card_repo, BarcodeService(storage_path=tmp_storage)),
        BitrixService(),
    )

    user = await service.register(UserCreate(
        telegram_id=777, phone="+998935557788", full_name="Тест Тестов",
        gender="female", city_id=1, language="ru",
    ))
    await session.commit()

    fetched = await user_repo.get_by_telegram_id(777)
    assert fetched is not None
    assert fetched.card is not None
    assert fetched.card.barcode_path is not None
    assert (tmp_storage / f"{fetched.id}.png").exists()
