from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

TransactionTypeStr = Literal["accrual", "redemption"]


class CardCreate(BaseModel):
    user_id: UUID
    card_number: str = Field(..., min_length=10, max_length=16)


class CardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    card_number: str
    barcode_path: Optional[str]
    bonus_balance: Decimal
    created_at: datetime


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    card_id: UUID
    amount: Decimal
    type: TransactionTypeStr
    description: Optional[str]
    created_at: datetime
