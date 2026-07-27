"""Razorpay integration: create Payment Links and process webhook events.

Uses Payment Links (a hosted checkout page URL) so the flow matches the rest of
the app: create link server-side -> redirect the user -> credits are granted
ONLY by the signature-verified webhook, deduped by Razorpay's event id, so a
lost/duplicated/forged redirect can't mint or double-mint credits.

UPI, cards, netbanking, and wallets are enabled per-account in the Razorpay
dashboard (UPI is on by default) — no code toggles needed here.
"""
from __future__ import annotations

import asyncio
import json
import uuid

import razorpay
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.credit_ledger import CreditBucket, CreditLedger, LedgerEntryType
from app.models.credit_pack import CreditPack
from app.models.purchase import Purchase, PurchaseStatus
from app.models.user import User
from app.models.webhook_event import WebhookEvent
from app.services import credits


class PaymentNotConfiguredError(RuntimeError):
    pass


def _client() -> razorpay.Client:
    if settings.RAZORPAY_KEY_ID is None or settings.RAZORPAY_KEY_SECRET is None:
        raise PaymentNotConfiguredError(
            "RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET not set — purchases disabled."
        )
    return razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET.get_secret_value(),
        )
    )


async def create_payment_link(
    db: AsyncSession, user: User, pack: CreditPack
) -> str:
    """Create a pending purchase + a Razorpay Payment Link; return its URL."""
    client = _client()

    purchase = Purchase(
        user_id=user.id,
        pack_id=pack.id,
        credits_granted=pack.total_credits,
        price_minor=pack.price_minor,
        currency=pack.currency,
        status=PurchaseStatus.pending,
    )
    db.add(purchase)
    await db.commit()
    await db.refresh(purchase)

    def _create() -> dict:
        return client.payment_link.create(
            {
                "amount": pack.price_minor,  # in paise
                "currency": pack.currency.upper(),
                "accept_partial": False,
                "description": f"{pack.name} — {pack.total_credits} credits",
                "customer": {"email": user.email},
                # We redirect straight to the link, so no need to also email it.
                "notify": {"email": False, "sms": False},
                "reminder_enable": False,
                "notes": {
                    "purchase_id": str(purchase.id),
                    "user_id": str(user.id),
                    "credits": str(pack.total_credits),
                },
                "callback_url": settings.PAYMENT_SUCCESS_URL,
                "callback_method": "get",
                "reference_id": str(purchase.id),
            }
        )

    link = await asyncio.to_thread(_create)
    purchase.provider_ref = link["id"]
    await db.commit()
    return link["short_url"]


async def _complete_purchase(
    db: AsyncSession, purchase_id: str, payment_id: str | None
) -> None:
    """Mark the purchase completed and grant its credits (idempotent)."""
    purchase = await db.get(Purchase, uuid.UUID(purchase_id))
    if purchase is None:
        logger.warning("Purchase %s not found for paid webhook", purchase_id)
        return
    if purchase.status != PurchaseStatus.completed:
        purchase.status = PurchaseStatus.completed
        if payment_id:
            purchase.provider_payment_id = payment_id
        await db.commit()

    await credits.grant_credits(
        db,
        purchase.user_id,
        purchase.credits_granted,
        entry_type=LedgerEntryType.purchase,
        bucket=CreditBucket.purchased,
        actor="razorpay",
        reason="Credit pack purchase",
        idempotency_key=f"purchase:{purchase.id}",
        related_purchase_id=purchase.id,
    )


async def _reverse_refund(db: AsyncSession, payment_id: str | None) -> None:
    """On a refund, mark the purchase refunded and claw back credits (clamped
    to available — never forced negative)."""
    if not payment_id:
        return
    purchase = await db.scalar(
        select(Purchase).where(Purchase.provider_payment_id == payment_id)
    )
    if purchase is None or purchase.status == PurchaseStatus.refunded:
        return
    purchase.status = PurchaseStatus.refunded
    await db.commit()

    balance = await credits.get_or_create_balance(db, purchase.user_id)
    take = min(purchase.credits_granted, balance.available)
    if take > 0:
        balance.available -= take
        await db.flush()
        db.add(
            CreditLedger(
                user_id=purchase.user_id,
                entry_type=LedgerEntryType.refund_reversal,
                amount=-take,
                bucket=CreditBucket.purchased,
                balance_after=balance.available,
                related_purchase_id=purchase.id,
                actor="razorpay",
                reason="Razorpay refund",
            )
        )
        await db.commit()


async def handle_webhook_event(
    db: AsyncSession, payload: bytes, signature: str, event_id: str
) -> None:
    """Verify, dedupe, and process a Razorpay webhook. Raises ValueError on a
    bad signature so the endpoint can return 400."""
    if settings.RAZORPAY_WEBHOOK_SECRET is None:
        raise PaymentNotConfiguredError("RAZORPAY_WEBHOOK_SECRET is not set.")
    secret = settings.RAZORPAY_WEBHOOK_SECRET.get_secret_value()

    try:
        _client().utility.verify_webhook_signature(
            payload.decode("utf-8"), signature, secret
        )
    except Exception as exc:  # razorpay raises SignatureVerificationError
        raise ValueError("Invalid Razorpay webhook signature") from exc

    # Dedupe on Razorpay's unique event id (X-Razorpay-Event-Id header). If the
    # header is missing, fall back to a content hash so we still record it.
    key = event_id or f"anon:{hash(payload)}"
    if await db.get(WebhookEvent, key) is not None:
        return
    data = json.loads(payload)
    event = data.get("event", "")
    db.add(WebhookEvent(event_id=key, type=event))
    await db.commit()

    entities = data.get("payload", {})

    def entity(name: str) -> dict:
        return entities.get(name, {}).get("entity", {})

    # Razorpay fires several "paid" events for one Payment Link depending on the
    # webhook subscription (payment.captured, order.paid, payment_link.paid). We
    # handle all three — notes.purchase_id propagates to the link, order, AND
    # payment entities — and rely on idempotency (status check + grant key) so
    # duplicate events are safe no-ops.
    payment = entity("payment")
    if event in ("payment_link.paid", "order.paid", "payment.captured"):
        link, order = entity("payment_link"), entity("order")
        purchase_id = (
            (link.get("notes") or {}).get("purchase_id")
            or link.get("reference_id")
            or (order.get("notes") or {}).get("purchase_id")
            or order.get("receipt")
            or (payment.get("notes") or {}).get("purchase_id")
        )
        if purchase_id:
            await _complete_purchase(db, purchase_id, payment.get("id"))
    elif event in ("refund.created", "refund.processed"):
        await _reverse_refund(db, entity("refund").get("payment_id"))
    # Other events are acked (recorded) without action.
