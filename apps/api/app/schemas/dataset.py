"""Dataset request/response DTOs."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.dataset import DatasetStatus


class DatasetUpdate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)


class DatasetColumnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    dtype: str
    position: int
    null_count: int
    distinct_count: int
    min_value: str | None
    max_value: str | None
    sample_values: list


class PreprocessChange(BaseModel):
    code: str
    title: str
    detail: str


class DatasetTableSummary(BaseModel):
    """One table within a (possibly multi-CSV) dataset, without its columns."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    filename: str
    row_count: int | None = None
    col_count: int | None = None


class DatasetTableProfile(DatasetTableSummary):
    columns: list[DatasetColumnRead] = []


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    status: DatasetStatus
    row_count: int | None
    col_count: int | None
    error: str | None
    created_at: datetime
    archived: bool = False
    preprocessed: bool = False
    # At ingest: what cleaning WOULD do (drives the recommendation card).
    # After preprocessing: what was applied.
    preprocessing_summary: list[PreprocessChange] | None = None
    # Per-table summary when the dataset spans multiple CSVs; None for single-table.
    tables: list[DatasetTableSummary] | None = None


class DatasetProfile(DatasetRead):
    """Full profile: dataset metadata plus the per-column summary."""

    columns: list[DatasetColumnRead]
    # Full per-table profiles (with columns) for multi-table datasets.
    tables: list[DatasetTableProfile] | None = None
