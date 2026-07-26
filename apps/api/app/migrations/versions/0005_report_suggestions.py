"""report suggestions

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    suggestion_status = sa.Enum(
        "suggested", "generated", "dismissed", name="suggestionstatus"
    )
    op.create_table(
        "report_suggestions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "chart_types", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "status", suggestion_status, server_default="suggested", nullable=False
        ),
        sa.Column("report_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["dataset_id"], ["datasets.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["report_id"], ["reports.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_report_suggestions_user_id", "report_suggestions", ["user_id"]
    )
    op.create_index(
        "ix_report_suggestions_dataset_id", "report_suggestions", ["dataset_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_suggestions_dataset_id", table_name="report_suggestions"
    )
    op.drop_index(
        "ix_report_suggestions_user_id", table_name="report_suggestions"
    )
    op.drop_table("report_suggestions")
    sa.Enum(name="suggestionstatus").drop(op.get_bind())
