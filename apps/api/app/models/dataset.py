"""Dataset model — one uploaded CSV, stored as the original file plus a
Parquet cache. The column profile (see M2) is what feeds the LLM's context."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.dataset_column import DatasetColumn
    from app.models.user import User


class DatasetStatus(str, enum.Enum):
    uploading = "uploading"
    profiling = "profiling"
    ready = "ready"
    failed = "failed"


class Dataset(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "datasets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    parquet_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    col_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Ingestion summary: how many CSV files went in (ZIPs expanded) and the
    # total size of the resulting Parquet tables. NULL on pre-existing rows.
    source_file_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[DatasetStatus] = mapped_column(
        SAEnum(DatasetStatus, name="datasetstatus"),
        default=DatasetStatus.uploading,
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # Data-cleaning state. At ingest we store the AUDIT (what cleaning would do);
    # after the user runs "Pre-process now" we flip the flag and replace the
    # summary with what was actually applied.
    preprocessed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )
    preprocessing_summary: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Multi-table datasets: one entry per table (name, filename, parquet_path,
    # row_count, col_count, columns). NULL means a single-table dataset — the
    # legacy shape, described by parquet_path + the DatasetColumn rows.
    tables: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Soft delete: archived datasets are hidden by default but can be restored.
    archived: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )

    owner: Mapped["User"] = relationship(back_populates="datasets")
    columns: Mapped[list["DatasetColumn"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="DatasetColumn.position",
    )
