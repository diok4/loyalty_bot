from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from loyalty_bot.core.logger import get_logger
from loyalty_bot.domain.models import BonusTransaction, LoyaltyCard
from loyalty_bot.domain.schemas import CardCreate

from .base import AbstractRepository

logger = get_logger(__name__)


class CardRepository(AbstractRepository[LoyaltyCard]):
    model = LoyaltyCard

    async def get_by_user_id(self, user_id: UUID) -> Optional[LoyaltyCard]:
        stmt = select(LoyaltyCard).where(LoyaltyCard.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_card_number(self, card_number: str) -> Optional[LoyaltyCard]:
        stmt = select(LoyaltyCard).where(LoyaltyCard.card_number == card_number)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_transactions(
        self, card_id: UUID, limit: int = 20
    ) -> Optional[LoyaltyCard]:
        stmt = (
            select(LoyaltyCard)
            .where(LoyaltyCard.id == card_id)
            .options(selectinload(LoyaltyCard.transactions))
        )
        result = await self.session.execute(stmt)
        card = result.scalar_one_or_none()
        if card is not None:
            card.transactions = list(card.transactions)[:limit]
        return card

    async def list_transactions(
        self, card_id: UUID, limit: int = 20, offset: int = 0
    ) -> Sequence[BonusTransaction]:
        stmt = (
            select(BonusTransaction)
            .where(BonusTransaction.card_id == card_id)
            .order_by(BonusTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, data: CardCreate) -> LoyaltyCard:
        card = LoyaltyCard(
            user_id=data.user_id,
            card_number=data.card_number,
        )
        await self.add(card)
        logger.info(
            "card_created",
            card_id=str(card.id),
            card_number=card.card_number,
            user_id=str(card.user_id),
        )
        return card

    async def set_barcode_path(self, card: LoyaltyCard, path: str) -> LoyaltyCard:
        card.barcode_path = path
        await self.session.flush()
        return card

    async def add_transaction(
        self, transaction: BonusTransaction
    ) -> BonusTransaction:
        self.session.add(transaction)
        await self.session.flush()
        await self.session.refresh(transaction)
        return transaction
