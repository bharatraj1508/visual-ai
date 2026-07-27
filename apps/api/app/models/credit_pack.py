"""Credit pack — a purchasable bundle. The app shows only credits + bonus; the
currency price lives here and surfaces only inside the provider's checkout.

`price_minor` is in the currency's smallest unit (paise for INR, cents for USD).
"""
from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class CreditPack(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "credit_packs"

    # Stable machine key (e.g. "starter") for seeding/lookup, independent of id.
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_credits: Mapped[int] = mapped_column(Integer, nullable=False)
    bonus_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="inr")
    # Optional marketing badge shown on the pack card ("Most popular").
    badge: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    @property
    def total_credits(self) -> int:
        return self.base_credits + self.bonus_credits
