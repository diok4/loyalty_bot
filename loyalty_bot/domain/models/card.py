import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
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
    from .user import User
    from .transaction import BonusTransaction


class LoyaltyCard(Base):
    __tablename__ = "loyalty_cards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    card_number: Mapped[str] = mapped_column(
        String(16), unique=True, nullable=False
    )
    barcode_path: Mapped[Optional[str]] = mapped_column(Text)
    bonus_balance: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default=text("0"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="card", lazy="joined")
    transactions: Mapped[List["BonusTransaction"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
        lazy="raise",
        order_by="desc(BonusTransaction.created_at)",
    )

    def __repr__(self) -> str:
        return f"<LoyaltyCard number={self.card_number} balance={self.bonus_balance}>"
