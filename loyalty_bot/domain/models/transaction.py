import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from loyalty_bot.core.database import Base

if TYPE_CHECKING:
    from .card import LoyaltyCard


class TransactionType(str, enum.Enum):
    """Тип бонусной операции. Значения совпадают с CHECK-констрейнтом в БД."""
    ACCRUAL = "accrual"
    REDEMPTION = "redemption"


class BonusTransaction(Base):
    __tablename__ = "bonus_transactions"
    __table_args__ = (
        CheckConstraint(
            "type IN ('accrual', 'redemption')",
            name="ck_bonus_transactions_type",
        ),
        Index("idx_transactions_card_id", "card_id"),
        Index("idx_transactions_created", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loyalty_cards.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    card: Mapped["LoyaltyCard"] = relationship(back_populates="transactions")

    def __repr__(self) -> str:
        return (
            f"<BonusTransaction card={self.card_id} "
            f"amount={self.amount} type={self.type}>"
        )
