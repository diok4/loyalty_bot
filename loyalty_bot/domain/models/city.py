from typing import TYPE_CHECKING, List

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from loyalty_bot.core.database import Base

if TYPE_CHECKING:
    from .user import User


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    users: Mapped[List["User"]] = relationship(
        back_populates="city",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<City id={self.id} name={self.name!r}>"
