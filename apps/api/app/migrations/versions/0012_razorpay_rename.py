"""switch payments to razorpay: provider-neutral column/table names

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-27
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "purchases", "stripe_checkout_session_id", new_column_name="provider_ref"
    )
    op.alter_column(
        "purchases", "stripe_payment_intent_id", new_column_name="provider_payment_id"
    )
    op.execute("ALTER INDEX ix_purchases_checkout_session RENAME TO ix_purchases_provider_ref")
    op.rename_table("stripe_events", "webhook_events")


def downgrade() -> None:
    op.rename_table("webhook_events", "stripe_events")
    op.execute("ALTER INDEX ix_purchases_provider_ref RENAME TO ix_purchases_checkout_session")
    op.alter_column(
        "purchases", "provider_payment_id", new_column_name="stripe_payment_intent_id"
    )
    op.alter_column(
        "purchases", "provider_ref", new_column_name="stripe_checkout_session_id"
    )
