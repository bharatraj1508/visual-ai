"""Per-column profile of a dataset. This is the compact, LLM-facing summary of
the data (schema + stats + samples) — the agent reads this, never the raw rows."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.dataset import Dataset


class DatasetColumn(UUIDMixin, Base):
    __tablename__ = "dataset_columns"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    # Semantic type: integer | float | boolean | datetime | categorical | text
    dtype: Mapped[str] = mapped_column(String(32), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    null_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    distinct_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    min_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    max_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sample_values: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )

    dataset: Mapped["Dataset"] = relationship(back_populates="columns")
