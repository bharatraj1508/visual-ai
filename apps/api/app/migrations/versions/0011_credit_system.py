"""credit system: ledger, balances, packs, purchases, stripe events + seeds

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-27
"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- enum types (created explicitly below; create_type=False stops create_table
# from auto-emitting a second CREATE TYPE) ------------------------------------
ledger_entry_type = postgresql.ENUM(
    "signup_bonus", "promo_grant", "referral_reward", "purchase", "report_hold",
    "report_capture", "report_release", "refund_reversal", "chargeback_reversal",
    "expiry", "admin_grant", "admin_removal", "adjustment",
    name="ledgerentrytype", create_type=False,
)
credit_bucket = postgresql.ENUM(
    "free", "promo", "purchased", name="creditbucket", create_type=False
)
purchase_status = postgresql.ENUM(
    "pending", "completed", "failed", "refunded", "disputed",
    name="purchasestatus", create_type=False,
)
report_credit_state = postgresql.ENUM(
    "none", "held", "captured", "released",
    name="reportcreditstate", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum in (ledger_entry_type, credit_bucket, purchase_status, report_credit_state):
        enum.create(bind, checkfirst=True)

    # --- credit_packs -------------------------------------------------------
    op.create_table(
        "credit_packs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("slug", sa.String(length=50), nullable=False, unique=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("base_credits", sa.Integer(), nullable=False),
        sa.Column("bonus_credits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="inr"),
        sa.Column("badge", sa.String(length=40), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- purchases ----------------------------------------------------------
    op.create_table(
        "purchases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("pack_id", sa.Uuid(), sa.ForeignKey("credit_packs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("stripe_checkout_session_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_payment_intent_id", sa.String(length=255), nullable=True),
        sa.Column("credits_granted", sa.Integer(), nullable=False),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", purchase_status, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_purchases_checkout_session",
        "purchases",
        ["stripe_checkout_session_id"],
        unique=True,
    )

    # --- credit_balances (cache) -------------------------------------------
    op.create_table(
        "credit_balances",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("available", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("held", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("available >= 0", name="ck_credit_available_nonneg"),
        sa.CheckConstraint("held >= 0", name="ck_credit_held_nonneg"),
    )

    # --- credit_ledger (source of truth) -----------------------------------
    op.create_table(
        "credit_ledger",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("entry_type", ledger_entry_type, nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("bucket", credit_bucket, nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("related_report_id", sa.Uuid(), sa.ForeignKey("reports.id", ondelete="SET NULL"), nullable=True),
        sa.Column("related_purchase_id", sa.Uuid(), sa.ForeignKey("purchases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("related_hold_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True, unique=True),
        sa.Column("actor", sa.String(length=64), nullable=False, server_default="system"),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- stripe_events (webhook dedupe) ------------------------------------
    op.create_table(
        "stripe_events",
        sa.Column("event_id", sa.String(length=255), primary_key=True),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- reports credit columns --------------------------------------------
    op.add_column("reports", sa.Column("credit_cost", sa.Integer(), nullable=True))
    op.add_column(
        "reports",
        sa.Column("credit_state", report_credit_state, nullable=False, server_default="none"),
    )
    op.add_column("reports", sa.Column("credit_hold_id", sa.Uuid(), nullable=True))

    # --- seed the credit packs (credits + bonus; prices illustrative INR) --
    now_packs = [
        ("starter", "Starter", 100, 0, 49900, None, 1),
        ("analyst", "Analyst", 300, 30, 129900, "Most popular", 2),
        ("pro", "Pro", 750, 125, 279900, "Best value", 3),
        ("studio", "Studio", 2000, 500, 699900, None, 4),
    ]
    packs_table = sa.table(
        "credit_packs",
        sa.column("id", sa.Uuid()),
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("base_credits", sa.Integer()),
        sa.column("bonus_credits", sa.Integer()),
        sa.column("price_minor", sa.Integer()),
        sa.column("currency", sa.String()),
        sa.column("badge", sa.String()),
        sa.column("sort_order", sa.Integer()),
        sa.column("active", sa.Boolean()),
    )
    op.bulk_insert(
        packs_table,
        [
            {
                "id": uuid.uuid4(),
                "slug": slug,
                "name": name,
                "base_credits": base,
                "bonus_credits": bonus,
                "price_minor": price,
                "currency": "inr",
                "badge": badge,
                "sort_order": order,
                "active": True,
            }
            for slug, name, base, bonus, price, badge, order in now_packs
        ],
    )


def downgrade() -> None:
    op.drop_column("reports", "credit_hold_id")
    op.drop_column("reports", "credit_state")
    op.drop_column("reports", "credit_cost")
    op.drop_table("stripe_events")
    op.drop_table("credit_ledger")
    op.drop_table("credit_balances")
    op.drop_index("ix_purchases_checkout_session", table_name="purchases")
    op.drop_table("purchases")
    op.drop_table("credit_packs")
    bind = op.get_bind()
    for enum in (report_credit_state, purchase_status, credit_bucket, ledger_entry_type):
        enum.drop(bind, checkfirst=True)
