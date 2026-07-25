"""Artifact — a rendered output attached to an assistant message (a chart spec,
a table, a stat block). Charts are stored as Vega-Lite JSON in `spec`."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.message import Message


class Artifact(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "artifacts"

    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # chart | table | stat | text
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    spec: Mapped[dict] = mapped_column(JSONB, nullable=False)

    message: Mapped["Message"] = relationship(back_populates="artifacts")
