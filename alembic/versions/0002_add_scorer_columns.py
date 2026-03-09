"""add scorer columns to intercompany_transactions

Revision ID: 0002_add_scorer_columns
Revises: 003
Create Date: 2026-02-23 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_scorer_columns"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "intercompany_transactions",
        sa.Column("confidence_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "intercompany_transactions",
        sa.Column("match_type", sa.String(20), nullable=True),
    )
    op.add_column(
        "intercompany_transactions",
        sa.Column("amount_difference", sa.Float(), nullable=True),
    )
    op.add_column(
        "intercompany_transactions",
        sa.Column("days_difference", sa.Integer(), nullable=True),
    )
    op.add_column(
        "intercompany_transactions",
        sa.Column("match_reasons", sa.Text(), nullable=True),
    )
    op.add_column(
        "intercompany_transactions",
        sa.Column("llm_reasoning", sa.Text(), nullable=True),
    )
    op.add_column(
        "intercompany_transactions",
        sa.Column(
            "review_required",
            sa.Boolean(),
            nullable=True,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "intercompany_transactions",
        sa.Column(
            "reviewed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "intercompany_transactions",
        sa.Column("reviewed_by", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("intercompany_transactions", "reviewed_by")
    op.drop_column("intercompany_transactions", "reviewed_at")
    op.drop_column("intercompany_transactions", "review_required")
    op.drop_column("intercompany_transactions", "match_reasons")
    op.drop_column("intercompany_transactions", "llm_reasoning")
    op.drop_column("intercompany_transactions", "days_difference")
    op.drop_column("intercompany_transactions", "amount_difference")
    op.drop_column("intercompany_transactions", "match_type")
    op.drop_column("intercompany_transactions", "confidence_score")
