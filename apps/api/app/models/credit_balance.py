"""Credit balance — a per-user CACHE of the ledger, for fast atomic spend checks.

`available` is spendable now; `held` is reserved for in-flight reports. Both are
mutated only inside the same transaction as the ledger write that justifies them,
and a CHECK constraint makes a negative balance structurally impossible.
`available` must always equal SUM(credit_ledger.amount) for the user.
"""
from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CreditBalance(TimestampMixin, Base):
    __tablename__ = "credit_balances"
    __table_args__ = (
        CheckConstraint("available >= 0", name="ck_credit_available_nonneg"),
        CheckConstraint("held >= 0", name="ck_credit_held_nonneg"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    available: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    held: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
