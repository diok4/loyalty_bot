from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Gender = Literal["male", "female"]


class UserCreate(BaseModel):
    """Входные данные для регистрации. Валидация телефона — на стороне фильтра."""
    telegram_id: int = Field(..., gt=0)
    phone: str = Field(..., min_length=10, max_length=20)
    full_name: str = Field(..., min_length=2, max_length=100)
    gender: Gender
    city_id: int = Field(..., gt=0)
    language: str = Field(default="ru", min_length=2, max_length=5)


class UserUpdate(BaseModel):
    """Частичное обновление профиля."""
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    gender: Optional[Gender] = None
    city_id: Optional[int] = Field(default=None, gt=0)
    language: Optional[str] = Field(default=None, min_length=2, max_length=5)
    is_active: Optional[bool] = None


class UserRead(BaseModel):
    """Сериализация пользователя из ORM."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    telegram_id: int
    phone: str
    full_name: Optional[str]
    gender: Optional[Gender]
    city_id: Optional[int]
    language: str
    is_active: bool
    created_at: datetime
