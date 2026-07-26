"""report cost tracking

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("input_tokens", sa.Integer(), nullable=True))
    op.add_column("reports", sa.Column("output_tokens", sa.Integer(), nullable=True))
    op.add_column("reports", sa.Column("cost_usd", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "cost_usd")
    op.drop_column("reports", "output_tokens")
    op.drop_column("reports", "input_tokens")
