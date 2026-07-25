"""Declarative base and shared column mixins for all ORM models.

Keeping Base here (rather than in core/database.py) avoids circular imports:
models import from here, and Alembic/database import the models.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Root declarative base. All models inherit from this so Alembic can
    discover them via Base.metadata."""


class UUIDMixin:
    """Adds a UUID primary key generated application-side."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """Adds created_at / updated_at timestamps maintained by the DB + ORM."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
