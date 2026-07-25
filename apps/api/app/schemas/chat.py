"""Chat request/response DTOs."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    dataset_id: uuid.UUID
    title: str | None = Field(default=None, max_length=255)


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    title: str
    created_at: datetime


class ArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    title: str | None
    spec: dict


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    artifacts: list[ArtifactRead] = []


class ChatRequest(BaseModel):
    content: str = Field(min_length=1)
