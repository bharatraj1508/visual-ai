"""Purchase — one credit-pack buy via the payment provider (Razorpay).

Created in `pending` when the payment link is opened; flipped to `completed`
by the verified webhook, which is also where the credits are granted. Storing it
up front lets a reconciliation job settle purchases even if a webhook is lost.
Provider references are named generically so the provider can change without a
schema churn.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class PurchaseStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"
    disputed = "disputed"


class Purchase(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "purchases"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    pack_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("credit_packs.id", ondelete="RESTRICT"), nullable=False
    )
    # Provider's hosted-checkout / payment-link id (Razorpay plink_...).
    provider_ref: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    # Provider's captured-payment id (Razorpay pay_...).
    provider_payment_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    # Credits + price snapshotted at purchase time so later pack edits don't
    # rewrite history.
    credits_granted: Mapped[int] = mapped_column(Integer, nullable=False)
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[PurchaseStatus] = mapped_column(
        SAEnum(PurchaseStatus, name="purchasestatus"),
        default=PurchaseStatus.pending,
        nullable=False,
    )
