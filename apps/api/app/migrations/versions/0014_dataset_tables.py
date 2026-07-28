"""multi-table datasets: per-table profiles

A dataset may now hold several CSVs as separate queryable tables. For a single
table this column stays NULL and the dataset behaves exactly as before; when set,
it holds one entry per table (name, filename, parquet_path, counts, columns).

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "datasets",
        sa.Column("tables", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("datasets", "tables")
