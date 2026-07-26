"""Report request/response DTOs."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.report import ReportStatus


class ReportCreate(BaseModel):
    dataset_id: uuid.UUID
    # Either provide a free-text goal, or a suggestion_id to build the report
    # from an AI suggestion (its question/rationale become the goal).
    goal: str | None = Field(default=None, description="What the report should cover.")
    title: str | None = Field(default=None, max_length=255)
    suggestion_id: uuid.UUID | None = None


class ReportUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    title: str
    goal: str
    status: ReportStatus
    error: str | None
    created_at: datetime
    # Token usage + priced cost. Null for reports made before cost tracking.
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class ReportDetail(ReportRead):
    # List of sections: {title, narrative, charts: [vega_spec, ...]}
    content: list | None
