import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from loyalty_bot.core.exceptions import UserAlreadyExistsError
from loyalty_bot.domain.models import City
from loyalty_bot.domain.repositories import CardRepository, UserRepository
from loyalty_bot.domain.schemas import UserCreate
from loyalty_bot.services.barcode_service import BarcodeService
from loyalty_bot.services.bitrix_service import BitrixService
from loyalty_bot.services.card_service import CardService
from loyalty_bot.services.user_service import UserService


def _build(session, storage):
    return UserService(
        UserRepository(session),
        CardService(CardRepository(session), BarcodeService(storage_path=storage)),
        BitrixService(),
    )


@pytest.mark.asyncio
async def test_register_creates_user_and_card(session: AsyncSession, tmp_storage):
    session.add(City(id=1, name="Ташкент"))
    await session.commit()

    service = _build(session, tmp_storage)
    user = await service.register(UserCreate(
        telegram_id=42, phone="+998901234567", full_name="Иван",
        gender="male", city_id=1, language="ru",
    ))
    await session.commit()

    assert user.id is not None
    assert user.card is not None
    assert user.card.card_number.startswith("LC")
    assert len(user.card.card_number) == 16


@pytest.mark.asyncio
async def test_register_rejects_duplicate_phone(session: AsyncSession, tmp_storage):
    session.add(City(id=1, name="Ташкент"))
    await session.commit()
    service = _build(session, tmp_storage)

    base = UserCreate(telegram_id=1, phone="+998901111111",
                      full_name="A", gender="male", city_id=1, language="ru")
    await service.register(base)
    await session.commit()

    with pytest.raises(UserAlreadyExistsError):
        await service.register(base.model_copy(update={"telegram_id": 2}))
