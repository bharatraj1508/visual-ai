"""archive flags for datasets and reports

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("datasets", "reports"):
        op.add_column(
            table,
            sa.Column(
                "archived", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
        )


def downgrade() -> None:
    for table in ("reports", "datasets"):
        op.drop_column(table, "archived")
