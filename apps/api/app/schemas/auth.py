"""Auth request/response DTOs."""
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class ReferralSource(str, Enum):
    """Where the user heard about Visual AI. Stored as a plain string, so new
    channels can be added here without a DB migration."""

    facebook = "facebook"
    instagram = "instagram"
    linkedin = "linkedin"
    twitter = "twitter"
    youtube = "youtube"
    google_search = "google_search"
    friend = "friend"
    blog = "blog"
    other = "other"


class UsePurpose(str, Enum):
    """What the user intends to use Visual AI for (segmentation)."""

    professional = "professional"
    educational = "educational"
    research = "research"
    personal = "personal"
    business = "business"
    other = "other"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    referral_source: Optional[ReferralSource] = None
    referral_source_other: Optional[str] = Field(default=None, max_length=200)
    use_purpose: Optional[UsePurpose] = None
    marketing_opt_in: bool = False
    # Client-supplied signup context (e.g. UTM params). Free-form on purpose.
    signup_metadata: Optional[dict[str, Any]] = None

    @model_validator(mode="after")
    def _require_other_text(self) -> "UserCreate":
        # If they picked "Other", keep the free-text they typed; otherwise drop
        # any stray value so it can't contradict the selected source.
        if self.referral_source != ReferralSource.other:
            self.referral_source_other = None
        return self


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    email_verified: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=16, max_length=256)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    """Generic ack for actions that shouldn't leak account existence."""

    message: str
