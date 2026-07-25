"""Report request/response DTOs."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.report import ReportStatus


class ReportCreate(BaseModel):
    dataset_id: uuid.UUID
    goal: str = Field(min_length=1, description="What the report should cover.")
    title: str | None = Field(default=None, max_length=255)


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    title: str
    goal: str
    status: ReportStatus
    error: str | None
    created_at: datetime


class ReportDetail(ReportRead):
    # List of sections: {title, narrative, charts: [vega_spec, ...]}
    content: list | None
