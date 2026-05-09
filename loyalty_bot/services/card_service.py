import random
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Sequence
from uuid import UUID

from loyalty_bot.core.config import settings
from loyalty_bot.core.exceptions import (
    CardAlreadyExistsError,
    CardNotFoundError,
    InsufficientBonusesError,
)
from loyalty_bot.core.logger import get_logger
from loyalty_bot.domain.models import (
    BonusTransaction,
    LoyaltyCard,
    TransactionType,
)
from loyalty_bot.domain.repositories import CardRepository
from loyalty_bot.domain.schemas import CardCreate

from .barcode_service import BarcodeService

logger = get_logger(__name__)

# Каталог "товаров" для фейковой истории (dev only). Магазин — мебель.
_FAKE_PURCHASES = [
    "Покупка: диван угловой",
    "Покупка: кресло",
    "Покупка: обеденный стол",
    "Покупка: стулья (комплект 4 шт.)",
    "Покупка: шкаф-купе",
    "Покупка: кровать двуспальная",
    "Покупка: матрас ортопедический",
    "Покупка: прикроватная тумба",
    "Покупка: комод",
    "Покупка: журнальный столик",
    "Покупка: офисное кресло",
    "Покупка: компьютерный стол",
    "Покупка: пуф",
    "Покупка: полка настенная",
    "Покупка: гардеробная система",
    "Покупка: ТВ-тумба",
    "Покупка: барный стул",
    "Покупка: вешалка напольная",
]


class CardService:
    """Бизнес-логика карт: выпуск, штрихкод, начисление/списание бонусов."""

    def __init__(
        self,
        card_repo: CardRepository,
        barcode_service: BarcodeService,
    ) -> None:
        self.card_repo = card_repo
        self.barcode_service = barcode_service

    async def get_for_user(self, user_id: UUID) -> Optional[LoyaltyCard]:
        return await self.card_repo.get_by_user_id(user_id)

    async def create_for_user(self, user_id: UUID) -> LoyaltyCard:
        if await self.card_repo.get_by_user_id(user_id):
            raise CardAlreadyExistsError(str(user_id))

        card_number = self._generate_card_number()
        card = await self.card_repo.create(
            CardCreate(user_id=user_id, card_number=card_number)
        )

        barcode_path = await self.barcode_service.generate(
            card_number=card.card_number, user_id=user_id
        )
        await self.card_repo.set_barcode_path(card, str(barcode_path))

        if settings.SEED_FAKE_HISTORY:
            await self._seed_fake_history(card)

        logger.info("card_issued", card_number=card.card_number, user_id=str(user_id))
        return card

    async def _seed_fake_history(self, card: LoyaltyCard) -> None:
        """
        DEV ONLY: 2-3 случайные покупки на свежую карту, чтобы было что
        показать в "Балансе". Включается флагом SEED_FAKE_HISTORY=true.
        """
        n = random.randint(2, 3)
        descriptions = random.sample(_FAKE_PURCHASES, n)
        now = datetime.now(timezone.utc)
        total = Decimal(0)

        for desc in descriptions:
            days_ago = random.randint(1, 60)
            # Бонусы 1% от чека: чек 50 000–500 000 → бонусы 500–5 000.
            amount = Decimal(random.randint(500, 5000))
            tx = BonusTransaction(
                card_id=card.id,
                amount=amount,
                type=TransactionType.ACCRUAL.value,
                description=desc,
                created_at=now - timedelta(days=days_ago),
            )
            await self.card_repo.add_transaction(tx)
            total += amount

        card.bonus_balance = Decimal(card.bonus_balance) + total
        logger.info(
            "fake_history_seeded",
            card_id=str(card.id),
            count=n,
            total=str(total),
        )

    async def accrue(
        self,
        card_id: UUID,
        amount: Decimal,
        description: str = "",
    ) -> BonusTransaction:
        card = await self.card_repo.get(card_id)
        if card is None:
            raise CardNotFoundError(str(card_id))

        card.bonus_balance = Decimal(card.bonus_balance) + amount
        tx = BonusTransaction(
            card_id=card.id,
            amount=amount,
            type=TransactionType.ACCRUAL.value,
            description=description,
        )
        await self.card_repo.add_transaction(tx)
        logger.info(
            "bonuses_accrued",
            card_id=str(card.id),
            amount=str(amount),
            balance=str(card.bonus_balance),
        )
        return tx

    async def redeem(
        self,
        card_id: UUID,
        amount: Decimal,
        description: str = "",
    ) -> BonusTransaction:
        card = await self.card_repo.get(card_id)
        if card is None:
            raise CardNotFoundError(str(card_id))

        if Decimal(card.bonus_balance) < amount:
            raise InsufficientBonusesError(card.bonus_balance, amount)

        card.bonus_balance = Decimal(card.bonus_balance) - amount
        tx = BonusTransaction(
            card_id=card.id,
            amount=amount,
            type=TransactionType.REDEMPTION.value,
            description=description,
        )
        await self.card_repo.add_transaction(tx)
        logger.info(
            "bonuses_redeemed",
            card_id=str(card.id),
            amount=str(amount),
            balance=str(card.bonus_balance),
        )
        return tx

    async def history(
        self, card_id: UUID, limit: int = 20
    ) -> Sequence[BonusTransaction]:
        return await self.card_repo.list_transactions(card_id, limit=limit)

    @staticmethod
    def _generate_card_number() -> str:
        # "LC" + epoch (10 цифр) + 4 случайных = 16 символов.
        # secrets — криптостойкий рандом, снижает шанс коллизий.
        ts = int(datetime.now(timezone.utc).timestamp())
        rnd = secrets.randbelow(10_000)
        return f"LC{ts:010d}{rnd:04d}"
