import asyncio
from typing import Optional
from uuid import UUID

from loyalty_bot.core.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
)
from loyalty_bot.core.logger import get_logger
from loyalty_bot.domain.models import User
from loyalty_bot.domain.repositories import UserRepository
from loyalty_bot.domain.schemas import UserCreate, UserRead, UserUpdate

from .bitrix_service import BitrixService
from .card_service import CardService

logger = get_logger(__name__)


class UserService:
    """Координирует регистрацию: User + LoyaltyCard + Bitrix-контакт."""

    def __init__(
        self,
        user_repo: UserRepository,
        card_service: CardService,
        bitrix: BitrixService,
    ) -> None:
        self.user_repo = user_repo
        self.card_service = card_service
        self.bitrix = bitrix

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        return await self.user_repo.get_by_telegram_id(telegram_id)

    async def get_by_phone(self, phone: str) -> Optional[User]:
        return await self.user_repo.get_by_phone(phone)

    async def register(self, data: UserCreate) -> User:
        # Проверяем дубль до insert — лучше осмысленная ошибка, чем IntegrityError.
        if await self.user_repo.get_by_phone(data.phone):
            raise UserAlreadyExistsError(data.phone)

        user = await self.user_repo.create(data)
        card = await self.card_service.create_for_user(user.id)
        # selectin-relationship уже закеширована как None при refresh(user) —
        # привязываем созданную карту явно, чтобы хендлер видел её через user.card.
        user.card = card

        # Bitrix вызываем не блокируя ответ боту: лаги/падения внешней системы
        # не должны ломать UX.
        asyncio.create_task(
            self._sync_to_bitrix(UserRead.model_validate(user), card.card_number)
        )

        logger.info(
            "user_registered",
            user_id=str(user.id),
            card_number=card.card_number,
        )
        return user

    async def update_profile(self, user_id: UUID, data: UserUpdate) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))
        return await self.user_repo.update(user, data)

    async def _sync_to_bitrix(self, user: UserRead, card_number: str) -> None:
        try:
            await self.bitrix.create_contact(user, card_number=card_number)
        except Exception:
            # Не валим регистрацию — Bitrix синхронизируется отдельным воркером.
            logger.exception("bitrix_sync_failed", user_id=str(user.id))
