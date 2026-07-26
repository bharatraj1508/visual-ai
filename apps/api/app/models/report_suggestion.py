"""ReportSuggestion — an AI-proposed report the user can generate for a dataset.

Suggestions are produced once when a dataset is first analyzed and persist so
the panel survives reloads. Each carries the analytical `question` it answers,
the `rationale` (what findings to expect), and the `chart_types` that would
back it up. Its `status` tracks the card's lifecycle:
  suggested  — shown on the analyze panel
  generated  — turned into a report (linked via `report_id`), hidden from cards
  dismissed  — cancelled by the user, hidden from cards
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class SuggestionStatus(str, enum.Enum):
    suggested = "suggested"
    generated = "generated"
    dismissed = "dismissed"


class ReportSuggestion(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "report_suggestions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    chart_types: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[SuggestionStatus] = mapped_column(
        SAEnum(SuggestionStatus, name="suggestionstatus"),
        default=SuggestionStatus.suggested,
        nullable=False,
    )
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reports.id", ondelete="SET NULL"), nullable=True
    )
