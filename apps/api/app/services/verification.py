"""Email-verification lifecycle: issue tokens, send the email, redeem tokens.

Kept framework-agnostic — raises `VerificationError` rather than HTTP errors so
the endpoint layer owns the HTTP translation.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.email_verification_token import EmailVerificationToken
from app.models.user import User
from app.services.email import EmailMessage, get_email_sender


class VerificationError(Exception):
    """Raised when a token can't be redeemed. `reason` is a stable code the
    API maps to a message: 'invalid' | 'expired' | 'used'."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_verification_url(raw_token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/auth/verify?token={raw_token}"


def _build_message(user: User, url: str) -> EmailMessage:
    ttl_hours = settings.EMAIL_VERIFICATION_TOKEN_TTL_HOURS
    subject = "Verify your email for Visual AI"
    text = (
        f"Welcome to Visual AI!\n\n"
        f"Confirm your email to activate your account and unlock your free "
        f"credits:\n\n{url}\n\n"
        f"This link expires in {ttl_hours} hours. "
        f"If you didn't create an account, you can ignore this email."
    )
    html = (
        f'<div style="font-family:system-ui,sans-serif;max-width:480px;margin:auto">'
        f"<h2>Welcome to Visual AI</h2>"
        f"<p>Confirm your email to activate your account and unlock your "
        f"free credits.</p>"
        f'<p><a href="{url}" style="display:inline-block;padding:12px 20px;'
        f"background:#111;color:#fff;text-decoration:none;border-radius:8px\">"
        f"Verify email</a></p>"
        f'<p style="color:#666;font-size:13px">This link expires in '
        f"{ttl_hours} hours. If you didn't create an account, ignore this "
        f"email.</p></div>"
    )
    return EmailMessage(to=user.email, subject=subject, html=html, text=text)


async def issue_verification_token(db: AsyncSession, user: User) -> str:
    """Invalidate any outstanding tokens for the user and mint a fresh one.
    Returns the RAW token (only ever held here + in the email)."""
    # One live token per user: retire prior unused ones so an old link can't
    # be used after a resend.
    await db.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.used_at.is_(None),
        )
        .values(used_at=_now())
    )

    raw = secrets.token_urlsafe(32)
    token = EmailVerificationToken(
        user_id=user.id,
        token_hash=_hash_token(raw),
        expires_at=_now()
        + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_TTL_HOURS),
    )
    db.add(token)
    await db.flush()
    return raw


async def send_verification_email(db: AsyncSession, user: User) -> None:
    """Issue a token and email the verification link. Commits the token so it
    survives even if the caller runs this as a fire-and-forget task."""
    raw = await issue_verification_token(db, user)
    await db.commit()
    url = build_verification_url(raw)
    try:
        await get_email_sender().send(_build_message(user, url))
    except Exception:
        # Don't crash the request path on a transient provider error — the user
        # can hit "resend". Log with context for observability.
        logger.exception("Failed to send verification email to %s", user.email)


async def seconds_until_resend_allowed(db: AsyncSession, user: User) -> int:
    """0 if a resend is allowed now, else seconds the caller must wait."""
    last = await db.scalar(
        select(EmailVerificationToken.created_at)
        .where(EmailVerificationToken.user_id == user.id)
        .order_by(EmailVerificationToken.created_at.desc())
        .limit(1)
    )
    if last is None:
        return 0
    cooldown = settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS
    elapsed = (_now() - last).total_seconds()
    return max(0, int(cooldown - elapsed))


async def verify_email_token(db: AsyncSession, raw_token: str) -> User:
    """Redeem a token. Raises VerificationError on invalid/expired/used."""
    token = await db.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == _hash_token(raw_token)
        )
    )
    if token is None:
        raise VerificationError("invalid")
    if token.used_at is not None:
        raise VerificationError("used")
    if token.expires_at <= _now():
        raise VerificationError("expired")

    token.used_at = _now()
    user = await db.get(User, token.user_id)
    if user is None:  # user deleted after token issue — treat as invalid
        raise VerificationError("invalid")

    # Idempotent: re-verifying an already-verified account is a no-op success.
    first_verification = user.email_verified_at is None
    if first_verification:
        user.email_verified_at = _now()
    await db.commit()
    await db.refresh(user)

    if first_verification:
        # Grant the welcome credits now that the email is confirmed. Idempotent
        # on the user id, so a double-submit can't double-grant.
        from app.services.credits import grant_signup_bonus

        await grant_signup_bonus(db, user.id)

    logger.info("Verified email for user %s", user.email)
    return user
