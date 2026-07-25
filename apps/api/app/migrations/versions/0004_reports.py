"""reports

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    report_status = sa.Enum("running", "completed", "failed", name="reportstatus")
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column(
            "status", report_status, server_default="running", nullable=False
        ),
        sa.Column(
            "content", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("error", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["dataset_id"], ["datasets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_user_id", "reports", ["user_id"])
    op.create_index("ix_reports_dataset_id", "reports", ["dataset_id"])


def downgrade() -> None:
    op.drop_index("ix_reports_dataset_id", table_name="reports")
    op.drop_index("ix_reports_user_id", table_name="reports")
    op.drop_table("reports")
    sa.Enum(name="reportstatus").drop(op.get_bind())
