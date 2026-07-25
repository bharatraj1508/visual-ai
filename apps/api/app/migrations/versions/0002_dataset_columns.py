"""dataset column profiles

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dataset_columns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("dtype", sa.String(length=32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("null_count", sa.Integer(), nullable=False),
        sa.Column("distinct_count", sa.Integer(), nullable=False),
        sa.Column("min_value", sa.String(length=255), nullable=True),
        sa.Column("max_value", sa.String(length=255), nullable=True),
        sa.Column(
            "sample_values",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"], ["datasets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dataset_columns_dataset_id", "dataset_columns", ["dataset_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dataset_columns_dataset_id", table_name="dataset_columns"
    )
    op.drop_table("dataset_columns")
