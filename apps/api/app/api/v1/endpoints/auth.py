"""Auth endpoints: register, login (OAuth2 password flow), and current user."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.auth import Token, UserCreate, UserRead
from app.services.auth import (
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter()


@router.post(
    "/register", response_model=UserRead, status_code=status.HTTP_201_CREATED
)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("Registered new user %s", user.email)
    return user


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
