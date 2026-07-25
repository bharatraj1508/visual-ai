"""Dataset request/response DTOs."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.dataset import DatasetStatus


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


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    status: DatasetStatus
    row_count: int | None
    col_count: int | None
    error: str | None
    created_at: datetime


class DatasetProfile(DatasetRead):
    """Full profile: dataset metadata plus the per-column summary."""

    columns: list[DatasetColumnRead]
