"""User model — owns datasets and chat sessions."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.dataset import Dataset
    from app.models.email_verification_token import EmailVerificationToken


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(320), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # --- Profile / signup intake (nullable so pre-existing rows are valid) ---
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Marketing attribution: how the user found us (e.g. "instagram", "friend").
    referral_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Free text captured when referral_source == "other".
    referral_source_other: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    # Segmentation: what they'll use Visual AI for (e.g. "professional").
    use_purpose: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Explicit consent for marketing email (default off — GDPR-friendly).
    marketing_opt_in: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    # Open-ended bucket for future signup context (UTM params, landing page,
    # experiment variant, …) without needing a migration per new key.
    signup_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    # Set when the user clicks their verification link. NULL = unverified.
    # This gates the free-credit grant (and later, report generation) —
    # distinct from is_active, which is the admin enable/disable switch.
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    datasets: Mapped[list["Dataset"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    verification_tokens: Mapped[list["EmailVerificationToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None
