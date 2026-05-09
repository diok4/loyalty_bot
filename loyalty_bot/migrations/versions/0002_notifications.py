"""notifications table

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("text_body", sa.Text, nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column("sent_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column(
            "failed_count", sa.Integer, nullable=False, server_default=sa.text("0")
        ),
        sa.Column("created_by_tg_id", sa.BigInteger, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # Партиальный индекс — воркер читает только pending по времени.
    op.create_index(
        "idx_notifications_pending",
        "notifications",
        ["scheduled_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("idx_notifications_pending", table_name="notifications")
    op.drop_table("notifications")
