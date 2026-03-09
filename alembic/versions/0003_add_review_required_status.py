"""no-op: review_required status supported by existing VARCHAR column

Revision ID: 0003_add_review_required_status
Revises: 0002_add_scorer_columns
Create Date: 2026-03-09 00:00:00.000000

"""
from typing import Sequence, Union

revision: str = "0003_add_review_required_status"
down_revision: Union[str, None] = "0002_add_scorer_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
