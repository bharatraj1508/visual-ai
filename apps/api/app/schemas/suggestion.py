"""Report-suggestion request/response DTOs."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.report_suggestion import SuggestionStatus


class SuggestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    title: str
    question: str
    rationale: str
    chart_types: list[str]
    status: SuggestionStatus
    report_id: uuid.UUID | None
    created_at: datetime
