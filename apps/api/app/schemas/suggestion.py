"""Report-suggestion request/response DTOs."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent.suggestions import CUSTOM_PROMPT_MAX_CHARS, sanitize_user_prompt
from app.models.report_suggestion import SuggestionStatus

CUSTOM_PROMPT_MIN_CHARS = 10


class CustomSuggestionCreate(BaseModel):
    """A user's free-text question about their dataset, to be turned into a
    problem-statement card. Sanitized at the edge so nothing downstream ever
    sees control characters or fence-tag injection."""

    prompt: str = Field(min_length=1, max_length=CUSTOM_PROMPT_MAX_CHARS)

    @field_validator("prompt")
    @classmethod
    def _sanitize(cls, value: str) -> str:
        value = sanitize_user_prompt(value)
        if len(value) < CUSTOM_PROMPT_MIN_CHARS:
            raise ValueError(
                "Describe what you want to learn from the data in a bit more detail."
            )
        return value


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
