"""Credit + billing endpoints: balance, ledger, packs, checkout, purchases,
the Razorpay webhook, and an admin grant/remove.

Everything except the webhook is authenticated and scoped to the current user.
The webhook is unauthenticated but signature-verified inside the service.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import logger
from app.core.security import get_current_user
from app.models.credit_balance import CreditBalance
from app.models.credit_ledger import CreditLedger
from app.models.credit_pack import CreditPack
from app.models.purchase import Purchase
from app.models.user import User
from app.schemas.credits import (
    AdminGrantRequest,
    BalanceRead,
    CheckoutRequest,
    CheckoutResponse,
    LedgerEntryRead,
    PackRead,
    PurchaseRead,
)
from app.services import credits, razorpay_service

router = APIRouter()


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Gate admin routes on an email allowlist (ADMIN_EMAILS in settings)."""
    if user.email.lower() not in settings.admin_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return user


@router.get("/balance", response_model=BalanceRead)
async def get_balance(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    balance = await db.get(CreditBalance, user.id)
    available = balance.available if balance else 0
    held = balance.held if balance else 0
    return BalanceRead(available=available, held=held, total=available + held)


@router.get("/ledger", response_model=list[LedgerEntryRead])
async def get_ledger(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = await db.scalars(
        select(CreditLedger)
        .where(CreditLedger.user_id == user.id)
        .order_by(CreditLedger.created_at.desc())
        .limit(min(limit, 200))
        .offset(offset)
    )
    return list(rows)


@router.get("/packs", response_model=list[PackRead])
async def list_packs(db: AsyncSession = Depends(get_db)):
    rows = await db.scalars(
        select(CreditPack)
        .where(CreditPack.active.is_(True))
        .order_by(CreditPack.sort_order.asc())
    )
    return list(rows)


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    payload: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pack = await db.get(CreditPack, payload.pack_id)
    if pack is None or not pack.active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Credit pack not found"
        )
    try:
        url = await razorpay_service.create_payment_link(db, user, pack)
    except razorpay_service.PaymentNotConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payments are not configured yet.",
        )
    return CheckoutResponse(checkout_url=url)


@router.get("/purchases", response_model=list[PurchaseRead])
async def list_purchases(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = await db.scalars(
        select(Purchase)
        .where(Purchase.user_id == user.id)
        .order_by(Purchase.created_at.desc())
    )
    return list(rows)


@router.post("/webhook", include_in_schema=False)
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("x-razorpay-signature", "")
    event_id = request.headers.get("x-razorpay-event-id", "")
    try:
        await razorpay_service.handle_webhook_event(db, payload, sig, event_id)
    except ValueError:
        # Bad signature — reject so the provider doesn't count it as delivered.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature"
        )
    except razorpay_service.PaymentNotConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payments not configured",
        )
    except Exception:
        # Never leak internals to the provider; log and 500 so it retries.
        logger.exception("Razorpay webhook processing failed")
        raise HTTPException(status_code=500, detail="Webhook processing error")
    return {"received": True}


@router.post("/admin/grant", response_model=BalanceRead)
async def admin_grant(
    payload: AdminGrantRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    target = await db.get(User, payload.user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    await credits.admin_adjust(
        db, target.id, payload.amount, admin_id=admin.id, reason=payload.reason
    )
    balance = await db.get(CreditBalance, target.id)
    available = balance.available if balance else 0
    held = balance.held if balance else 0
    return BalanceRead(available=available, held=held, total=available + held)
