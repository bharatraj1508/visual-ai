"""Report-suggestion endpoints.

The analyze panel calls GET to fetch (and, on first visit, generate) the AI's
report ideas for a dataset. Users can regenerate the set, dismiss individual
cards, or ask their own question — which, once validated against the dataset's
columns, becomes a suggestion card like any other. A suggestion turns into a
report via the reports endpoint, which flips its status to `generated`.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agent.context import DatasetContext
from app.agent.suggestions import (
    CustomSuggestionRejected,
    CustomSuggestionUnavailable,
    craft_custom_suggestion,
    suggest_reports,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.dataset import Dataset, DatasetStatus
from app.models.report_suggestion import ReportSuggestion, SuggestionStatus
from app.models.user import User
from app.schemas.suggestion import CustomSuggestionCreate, SuggestionRead

router = APIRouter()


async def _ready_dataset(dataset_id: uuid.UUID, user: User, db: AsyncSession) -> Dataset:
    dataset = await db.scalar(
        select(Dataset)
        .where(Dataset.id == dataset_id, Dataset.user_id == user.id)
        .options(selectinload(Dataset.columns))
    )
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found"
        )
    if dataset.status != DatasetStatus.ready:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Dataset is not ready"
        )
    return dataset


async def _active_suggestions(
    dataset_id: uuid.UUID, user: User, db: AsyncSession
) -> list[ReportSuggestion]:
    result = await db.scalars(
        select(ReportSuggestion)
        .where(
            ReportSuggestion.dataset_id == dataset_id,
            ReportSuggestion.user_id == user.id,
            ReportSuggestion.status == SuggestionStatus.suggested,
        )
        .order_by(ReportSuggestion.created_at.asc())
    )
    return list(result)


async def _generate_and_store(
    dataset: Dataset, user: User, db: AsyncSession
) -> list[ReportSuggestion]:
    ctx = DatasetContext.from_models(dataset, dataset.columns)
    ideas = await suggest_reports(ctx, use_purpose=user.use_purpose)
    rows = [
        ReportSuggestion(
            user_id=user.id,
            dataset_id=dataset.id,
            title=idea["title"],
            question=idea["question"],
            rationale=idea["rationale"],
            chart_types=idea["chart_types"],
            status=SuggestionStatus.suggested,
        )
        for idea in ideas
    ]
    db.add_all(rows)
    await db.commit()
    for row in rows:
        await db.refresh(row)
    return rows


@router.get(
    "/datasets/{dataset_id}/suggestions", response_model=list[SuggestionRead]
)
async def list_suggestions(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = await _ready_dataset(dataset_id, user, db)
    existing = await _active_suggestions(dataset_id, user, db)
    if existing:
        return existing
    return await _generate_and_store(dataset, user, db)


@router.post(
    "/datasets/{dataset_id}/suggestions/regenerate",
    response_model=list[SuggestionRead],
)
async def regenerate_suggestions(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = await _ready_dataset(dataset_id, user, db)
    for row in await _active_suggestions(dataset_id, user, db):
        row.status = SuggestionStatus.dismissed
    await db.commit()
    return await _generate_and_store(dataset, user, db)


@router.post(
    "/datasets/{dataset_id}/suggestions/custom",
    response_model=SuggestionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_custom_suggestion(
    dataset_id: uuid.UUID,
    payload: CustomSuggestionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Turn the user's own question into a suggestion card.

    422 carries a user-facing reason when the question can't be grounded in the
    dataset's columns; 503 means the model was unavailable and a retry is fine.
    """
    dataset = await _ready_dataset(dataset_id, user, db)
    ctx = DatasetContext.from_models(dataset, dataset.columns)
    try:
        idea = await craft_custom_suggestion(ctx, payload.prompt)
    except CustomSuggestionRejected as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except CustomSuggestionUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="We couldn't process your question right now. Please try again.",
        ) from exc

    row = ReportSuggestion(
        user_id=user.id,
        dataset_id=dataset.id,
        title=idea["title"],
        question=idea["question"],
        rationale=idea["rationale"],
        chart_types=idea["chart_types"],
        status=SuggestionStatus.suggested,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete(
    "/suggestions/{suggestion_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def dismiss_suggestion(
    suggestion_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    suggestion = await db.scalar(
        select(ReportSuggestion).where(
            ReportSuggestion.id == suggestion_id,
            ReportSuggestion.user_id == user.id,
        )
    )
    if suggestion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found"
        )
    suggestion.status = SuggestionStatus.dismissed
    await db.commit()
