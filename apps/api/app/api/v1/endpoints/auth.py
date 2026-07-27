"""Auth endpoints: register, login, email verification, and current user."""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session, get_db
from app.core.logging import logger
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.auth import (
    MessageResponse,
    ResendVerificationRequest,
    Token,
    UserCreate,
    UserRead,
    VerifyEmailRequest,
)
from app.services.auth import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.services.verification import (
    VerificationError,
    seconds_until_resend_allowed,
    send_verification_email,
    verify_email_token,
)

router = APIRouter()

# Generic ack for resend — deliberately reveals nothing about whether the email
# maps to a real, unverified account.
_RESEND_ACK = (
    "If that email needs verification, we've sent a new link. "
    "Check your inbox."
)


async def _send_verification_bg(user_id: uuid.UUID) -> None:
    """Send a verification email on a fresh session (the request's session is
    gone by the time a background task runs)."""
    async with async_session() as db:
        user = await db.get(User, user_id)
        if user is not None and user.email_verified_at is None:
            await send_verification_email(db, user)


@router.post(
    "/register", response_model=UserRead, status_code=status.HTTP_201_CREATED
)
async def register(
    payload: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        # Enum -> str for storage; None stays None.
        referral_source=(
            payload.referral_source.value if payload.referral_source else None
        ),
        referral_source_other=payload.referral_source_other,
        use_purpose=payload.use_purpose.value if payload.use_purpose else None,
        marketing_opt_in=payload.marketing_opt_in,
        signup_metadata=payload.signup_metadata,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("Registered new user %s", user.email)
    background_tasks.add_task(_send_verification_bg, user.id)
    return user


@router.post("/verify-email", response_model=UserRead)
async def verify_email(
    payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db)
):
    """Redeem a verification token (called from the emailed link)."""
    try:
        user = await verify_email_token(db, payload.token)
    except VerificationError as exc:
        messages = {
            "invalid": "This verification link is invalid.",
            "expired": "This verification link has expired. Request a new one.",
            "used": "This verification link has already been used.",
        }
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=messages.get(exc.reason, "Verification failed."),
        )
    return user


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Resend the verification email. Always returns a generic ack so it can't
    be used to enumerate accounts; silently no-ops when rate-limited or when
    the account is missing/already verified."""
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is not None and user.email_verified_at is None:
        if await seconds_until_resend_allowed(db, user) == 0:
            background_tasks.add_task(_send_verification_bg, user.id)
    return MessageResponse(message=_RESEND_ACK)


@router.post("/login", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # OAuth2PasswordRequestForm carries the email in its `username` field.
    user = await db.scalar(select(User).where(User.email == form.username))
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(str(user.id))
    return Token(access_token=token)


@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user
