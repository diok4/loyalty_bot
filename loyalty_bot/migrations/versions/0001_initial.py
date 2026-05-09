"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # gen_random_uuid() — на PG 13+ extension встроен, но IF NOT EXISTS безопасно.
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "cities",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("telegram_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("phone", sa.String(20), nullable=False, unique=True),
        sa.Column("full_name", sa.String(100)),
        sa.Column("gender", sa.String(10)),
        sa.Column(
            "city_id",
            sa.Integer,
            sa.ForeignKey("cities.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "language", sa.String(5), nullable=False, server_default=sa.text("'ru'")
        ),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("gender IN ('male','female')", name="ck_users_gender"),
    )

    op.create_table(
        "loyalty_cards",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("card_number", sa.String(16), nullable=False, unique=True),
        sa.Column("barcode_path", sa.Text),
        sa.Column(
            "bonus_balance",
            sa.Numeric(10, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "bonus_transactions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "card_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("loyalty_cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "type IN ('accrual','redemption')", name="ck_bonus_transactions_type"
        ),
    )

    op.create_index("idx_transactions_card_id", "bonus_transactions", ["card_id"])
    op.create_index(
        "idx_transactions_created",
        "bonus_transactions",
        [sa.text("created_at DESC")],
    )

    op.bulk_insert(
        sa.table(
            "cities", sa.column("id", sa.Integer), sa.column("name", sa.String)
        ),
        [
            {"id": 1, "name": "Ташкент"},
            {"id": 2, "name": "Самарканд"},
            {"id": 3, "name": "Бухара"},
            {"id": 4, "name": "Андижан"},
            {"id": 5, "name": "Фергана"},
        ],
    )
    op.execute("SELECT setval('cities_id_seq', (SELECT MAX(id) FROM cities))")


def downgrade() -> None:
    op.drop_index("idx_transactions_created", table_name="bonus_transactions")
    op.drop_index("idx_transactions_card_id", table_name="bonus_transactions")
    op.drop_table("bonus_transactions")
    op.drop_table("loyalty_cards")
    op.drop_table("users")
    op.drop_table("cities")
