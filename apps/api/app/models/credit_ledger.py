"""Credit ledger — the immutable, append-only source of truth for credits.

`amount` is the signed delta to the user's AVAILABLE balance:
  grant / purchase / release / refund_reversal -> +/-
  report_hold                                  -> -cost  (reserve)
  report_capture                               ->  0     (finalize a hold)
  report_release                               -> +cost  (auto-refund a hold)
So SUM(amount) for a user == their available balance, which the
`credit_balances` cache mirrors for fast, atomic spend checks.

Rows are never updated or deleted (enforced by convention + the service layer).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class LedgerEntryType(str, enum.Enum):
    signup_bonus = "signup_bonus"
    promo_grant = "promo_grant"
    referral_reward = "referral_reward"
    purchase = "purchase"
    report_hold = "report_hold"
    report_capture = "report_capture"
    report_release = "report_release"
    refund_reversal = "refund_reversal"
    chargeback_reversal = "chargeback_reversal"
    expiry = "expiry"
    admin_grant = "admin_grant"
    admin_removal = "admin_removal"
    adjustment = "adjustment"


class CreditBucket(str, enum.Enum):
    free = "free"
    promo = "promo"
    purchased = "purchased"


class CreditLedger(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "credit_ledger"

    # user_id today; a future team/org rollout would generalize this to an
    # account_id (see the credit-system design). Kept as user_id to match the
    # current single-owner model.
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    entry_type: Mapped[LedgerEntryType] = mapped_column(
        SAEnum(LedgerEntryType, name="ledgerentrytype"), nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    bucket: Mapped[CreditBucket] = mapped_column(
        SAEnum(CreditBucket, name="creditbucket"), nullable=False
    )
    # Available balance immediately after this entry (audit + fast display).
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    related_report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reports.id", ondelete="SET NULL"), nullable=True
    )
    related_purchase_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("purchases.id", ondelete="SET NULL"), nullable=True
    )
    # Links a capture/release back to its originating report_hold entry.
    related_hold_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    # Guards against double-writes on retries (e.g. duplicate webhook / request).
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    # "system" | "razorpay" | "admin:<id>" — who caused the movement.
    actor: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
