"""user profile / signup intake fields

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(length=200), nullable=True))
    op.add_column(
        "users", sa.Column("referral_source", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("referral_source_other", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "users", sa.Column("use_purpose", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "marketing_opt_in",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "users",
        sa.Column("signup_metadata", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    for col in (
        "signup_metadata",
        "marketing_opt_in",
        "use_purpose",
        "referral_source_other",
        "referral_source",
        "full_name",
    ):
        op.drop_column("users", col)
