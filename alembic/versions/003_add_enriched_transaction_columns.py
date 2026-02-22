"""add enriched transaction columns

Revision ID: 003
Revises: 002
Create Date: 2024-01-01 00:00:02.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("entity_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_transactions_entity_id",
        "transactions",
        "entities",
        ["entity_id"],
        ["id"],
    )
    op.add_column(
        "transactions", sa.Column("contact_name", sa.String(255), nullable=True)
    )
    op.add_column(
        "transactions", sa.Column("account_code", sa.String(50), nullable=True)
    )
    op.add_column(
        "transactions", sa.Column("transaction_type", sa.String(50), nullable=True)
    )
    op.add_column(
        "transactions", sa.Column("reference", sa.String(255), nullable=True)
    )
    op.add_column("transactions", sa.Column("raw_payload", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("transactions", "raw_payload")
    op.drop_column("transactions", "reference")
    op.drop_column("transactions", "transaction_type")
    op.drop_column("transactions", "account_code")
    op.drop_column("transactions", "contact_name")
    op.drop_constraint("fk_transactions_entity_id", "transactions", type_="foreignkey")
    op.drop_column("transactions", "entity_id")
