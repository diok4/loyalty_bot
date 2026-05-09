import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from loyalty_bot.core.database import Base


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"      # ждёт времени отправки
    SENDING = "sending"      # сейчас рассылается (lock)
    SENT = "sent"            # доставка завершена
    FAILED = "failed"        # критический сбой


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        # Индекс по pending-задачам, отсортированным по времени запуска —
        # фоновый воркер только их и читает.
        Index(
            "idx_notifications_pending",
            "scheduled_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    text_body: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'")
    )
    sent_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    failed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    created_by_tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} status={self.status} scheduled={self.scheduled_at}>"
