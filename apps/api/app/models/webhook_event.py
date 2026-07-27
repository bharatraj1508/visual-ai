"""Webhook event dedupe log — the payment-provider idempotency spine.

Every inbound event id is inserted here BEFORE processing; the unique PK makes a
duplicate delivery (providers retry) a no-op. Doubles as an audit trail.
Razorpay sends a unique `X-Razorpay-Event-Id` header we key on.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    # Provider's unique event id.
    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
