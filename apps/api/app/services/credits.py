"""Credit engine: balances, grants, and the reserve -> capture/release spend flow.

Invariants this module enforces:
- credits are integers; a balance can never go negative (atomic conditional
  UPDATE + DB CHECK constraint);
- every balance mutation is written together with an immutable ledger row in the
  same transaction, so SUM(credit_ledger.amount) == credit_balances.available;
- grants are idempotent by `idempotency_key` (safe under webhook/request retry).
"""
from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.credit_balance import CreditBalance
from app.models.credit_ledger import CreditBucket, CreditLedger, LedgerEntryType
from app.models.dataset import Dataset


class InsufficientCreditsError(Exception):
    """Raised when a spend/reserve would take the balance negative."""

    def __init__(self, needed: int, available: int) -> None:
        super().__init__(f"needs {needed}, has {available}")
        self.needed = needed
        self.available = available


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- cost model --------------------------------------------------------------

_CLASS_COST = {
    "quick": lambda: settings.REPORT_COST_QUICK,
    "standard": lambda: settings.REPORT_COST_STANDARD,
    "deep": lambda: settings.REPORT_COST_DEEP,
}


def estimate_report_cost(dataset: Dataset, report_class: str = "standard") -> int:
    """Deterministic credit cost = base(class) x large-dataset multiplier.

    Quoted before generation and honored regardless of actual runtime, so the
    user always knows the price up front and we absorb the variance.
    """
    base = _CLASS_COST.get(report_class, _CLASS_COST["standard"])()
    rows = dataset.row_count or 0
    if rows >= settings.LARGE_DATASET_ROW_THRESHOLD:
        return math.ceil(base * settings.LARGE_DATASET_MULTIPLIER)
    return base


def regen_cost(original_cost: int) -> int:
    """Regeneration is cheaper — original / divisor, rounded, minimum 1."""
    if original_cost <= 0:
        return 0
    return max(1, round(original_cost / settings.REPORT_REGEN_DIVISOR))


# --- balance -----------------------------------------------------------------

async def get_or_create_balance(
    db: AsyncSession, user_id: uuid.UUID
) -> CreditBalance:
    balance = await db.get(CreditBalance, user_id)
    if balance is None:
        balance = CreditBalance(user_id=user_id, available=0, held=0)
        db.add(balance)
        await db.flush()
    return balance


# --- grants (credits in) -----------------------------------------------------

async def grant_credits(
    db: AsyncSession,
    user_id: uuid.UUID,
    amount: int,
    *,
    entry_type: LedgerEntryType,
    bucket: CreditBucket,
    actor: str = "system",
    reason: str | None = None,
    idempotency_key: str | None = None,
    expires_at: datetime | None = None,
    related_purchase_id: uuid.UUID | None = None,
) -> bool:
    """Add credits and append a ledger row, atomically. Returns False (no-op) if
    an entry with the same idempotency_key already exists."""
    if amount <= 0:
        raise ValueError("grant amount must be positive")
    if idempotency_key is not None:
        exists = await db.scalar(
            select(CreditLedger.id).where(
                CreditLedger.idempotency_key == idempotency_key
            )
        )
        if exists is not None:
            return False

    balance = await get_or_create_balance(db, user_id)
    balance.available += amount
    await db.flush()
    db.add(
        CreditLedger(
            user_id=user_id,
            entry_type=entry_type,
            amount=amount,
            bucket=bucket,
            balance_after=balance.available,
            expires_at=expires_at,
            related_purchase_id=related_purchase_id,
            idempotency_key=idempotency_key,
            actor=actor,
            reason=reason,
        )
    )
    await db.commit()
    return True


async def grant_signup_bonus(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """The one-time welcome grant, given at email verification. Idempotent."""
    return await grant_credits(
        db,
        user_id,
        settings.SIGNUP_BONUS_CREDITS,
        entry_type=LedgerEntryType.signup_bonus,
        bucket=CreditBucket.free,
        reason="Welcome credits",
        idempotency_key=f"signup_bonus:{user_id}",
        expires_at=_now() + timedelta(days=settings.FREE_CREDIT_TTL_DAYS),
    )


async def admin_adjust(
    db: AsyncSession,
    user_id: uuid.UUID,
    amount: int,
    *,
    admin_id: uuid.UUID,
    reason: str,
) -> None:
    """Admin grant (amount > 0) or removal (amount < 0). Removal is clamped to
    the available balance so it can't create a negative."""
    if amount == 0:
        return
    actor = f"admin:{admin_id}"
    if amount > 0:
        await grant_credits(
            db, user_id, amount,
            entry_type=LedgerEntryType.admin_grant,
            bucket=CreditBucket.promo, actor=actor, reason=reason,
        )
        return
    balance = await get_or_create_balance(db, user_id)
    take = min(-amount, balance.available)
    if take == 0:
        return
    balance.available -= take
    await db.flush()
    db.add(
        CreditLedger(
            user_id=user_id,
            entry_type=LedgerEntryType.admin_removal,
            amount=-take,
            bucket=CreditBucket.promo,
            balance_after=balance.available,
            actor=actor,
            reason=reason,
        )
    )
    await db.commit()


# --- spend (reserve -> capture / release) ------------------------------------

async def reserve_credits(
    db: AsyncSession,
    user_id: uuid.UUID,
    amount: int,
    *,
    report_id: uuid.UUID,
    idempotency_key: str | None = None,
) -> CreditLedger:
    """Atomically move `amount` from available -> held and record a report_hold.
    Raises InsufficientCreditsError (no mutation) if the balance is too low."""
    await get_or_create_balance(db, user_id)
    # Single atomic conditional decrement — the real race/negative guard.
    result = await db.execute(
        update(CreditBalance)
        .where(
            CreditBalance.user_id == user_id,
            CreditBalance.available >= amount,
        )
        .values(
            available=CreditBalance.available - amount,
            held=CreditBalance.held + amount,
        )
    )
    if result.rowcount == 0:
        balance = await db.get(CreditBalance, user_id)
        raise InsufficientCreditsError(amount, balance.available if balance else 0)

    balance = await db.get(CreditBalance, user_id)
    hold = CreditLedger(
        user_id=user_id,
        entry_type=LedgerEntryType.report_hold,
        amount=-amount,
        bucket=CreditBucket.purchased,
        balance_after=balance.available,
        related_report_id=report_id,
        idempotency_key=idempotency_key,
        actor="system",
        reason="Report generation (reserved)",
    )
    db.add(hold)
    await db.commit()
    await db.refresh(hold)
    return hold


async def capture_credits(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    amount: int,
    hold_id: uuid.UUID,
    report_id: uuid.UUID,
) -> None:
    """Finalize a hold: the reserved credits are now spent (held -> gone).
    available is unchanged (it dropped at reserve time)."""
    balance = await db.get(CreditBalance, user_id)
    if balance is not None:
        balance.held = max(0, balance.held - amount)
        await db.flush()
    db.add(
        CreditLedger(
            user_id=user_id,
            entry_type=LedgerEntryType.report_capture,
            amount=0,
            bucket=CreditBucket.purchased,
            balance_after=balance.available if balance else 0,
            related_report_id=report_id,
            related_hold_id=hold_id,
            actor="system",
            reason="Report generation (charged)",
        )
    )
    await db.commit()


async def release_credits(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    amount: int,
    hold_id: uuid.UUID,
    report_id: uuid.UUID,
    reason: str = "Report generation failed (refunded)",
) -> None:
    """Return a hold to available — the automatic refund when we don't deliver."""
    balance = await db.get(CreditBalance, user_id)
    if balance is not None:
        balance.held = max(0, balance.held - amount)
        balance.available += amount
        await db.flush()
    db.add(
        CreditLedger(
            user_id=user_id,
            entry_type=LedgerEntryType.report_release,
            amount=amount,
            bucket=CreditBucket.purchased,
            balance_after=balance.available if balance else amount,
            related_report_id=report_id,
            related_hold_id=hold_id,
            actor="system",
            reason=reason,
        )
    )
    await db.commit()
