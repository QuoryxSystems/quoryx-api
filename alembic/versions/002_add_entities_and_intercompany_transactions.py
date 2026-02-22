"""add entities and intercompany_transactions tables

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 00:00:01.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "entities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False, unique=True),
        sa.Column("org_name", sa.String(255), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("country_code", sa.String(3), nullable=True),
        sa.Column("connected_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "intercompany_transactions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "source_entity_id",
            sa.Uuid(),
            sa.ForeignKey("entities.id"),
            nullable=False,
        ),
        sa.Column(
            "target_entity_id",
            sa.Uuid(),
            sa.ForeignKey("entities.id"),
            nullable=True,
        ),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("transaction_date", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="unmatched"),
        sa.Column("source_transaction_id", sa.String(255), nullable=True),
        sa.Column("target_transaction_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("intercompany_transactions")
    op.drop_table("entities")
