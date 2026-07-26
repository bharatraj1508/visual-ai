"""Report endpoints.

Creation and generation are split so the client can navigate to a dedicated
report page and watch it build:
  POST /reports              — create the row (status `running`) and return it
  GET  /reports/{id}/stream  — SSE: run the agent, stream sections, persist
Generation streams like chat (no job queue): sections stream in and the
assembled content is persisted as `completed` before the final `report_done`.
"""
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.agent.context import DatasetContext
from app.agent.cost import UsageTracker
from app.agent.report import generate_report_events
from app.agent.streaming import friendly_error_detail
from app.core.database import get_db
from app.core.logging import logger
from app.core.security import get_current_user
from app.models.dataset import Dataset, DatasetStatus
from app.models.report import Report, ReportStatus
from app.models.report_suggestion import ReportSuggestion, SuggestionStatus
from app.models.user import User
from app.schemas.report import (
    ReportCreate,
    ReportDetail,
    ReportRead,
    ReportUpdate,
)

router = APIRouter()


async def _get_owned_report(
    report_id: uuid.UUID, user: User, db: AsyncSession
) -> Report:
    report = await db.scalar(
        select(Report).where(Report.id == report_id, Report.user_id == user.id)
    )
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Report not found"
        )
    return report


def _goal_from_suggestion(s: ReportSuggestion) -> str:
    chart_hint = (
        f" Where they help, use varied charts such as: {', '.join(s.chart_types)}."
        if s.chart_types
        else ""
    )
    return f"{s.question} {s.rationale}{chart_hint}".strip()


@router.post("", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ReportCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = await db.scalar(
        select(Dataset).where(
            Dataset.id == payload.dataset_id, Dataset.user_id == user.id
        )
    )
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found"
        )
    if dataset.status != DatasetStatus.ready:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Dataset is not ready"
        )

    goal = payload.goal
    title = payload.title
    suggestion: ReportSuggestion | None = None
    if payload.suggestion_id is not None:
        suggestion = await db.scalar(
            select(ReportSuggestion).where(
                ReportSuggestion.id == payload.suggestion_id,
                ReportSuggestion.user_id == user.id,
                ReportSuggestion.dataset_id == dataset.id,
            )
        )
        if suggestion is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Suggestion not found",
            )
        goal = goal or _goal_from_suggestion(suggestion)
        title = title or suggestion.title

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide a goal or a suggestion_id.",
        )

    report = Report(
        user_id=user.id,
        dataset_id=dataset.id,
        title=title or f"Report: {dataset.filename}",
        goal=goal,
        status=ReportStatus.running,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Generating a report removes its suggestion card immediately.
    if suggestion is not None:
        suggestion.status = SuggestionStatus.generated
        suggestion.report_id = report.id
        await db.commit()

    return report


@router.post(
    "/{report_id}/regenerate",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
)
async def regenerate_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a NEW report version for the same problem statement (goal + dataset)
    without touching the existing one. The client streams it with `fresh=true` so
    the result cache is bypassed and a genuinely new run is produced."""
    source = await _get_owned_report(report_id, user, db)
    dataset = await db.scalar(
        select(Dataset).where(
            Dataset.id == source.dataset_id, Dataset.user_id == user.id
        )
    )
    if dataset is None or dataset.status != DatasetStatus.ready:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Dataset is not available"
        )
    new = Report(
        user_id=user.id,
        dataset_id=source.dataset_id,
        title=source.title,
        goal=source.goal,
        status=ReportStatus.running,
    )
    db.add(new)
    await db.commit()
    await db.refresh(new)
    return new


@router.get("/{report_id}/versions", response_model=list[ReportDetail])
async def report_versions(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """All report versions for this one's problem statement (same dataset + goal),
    oldest first — the original at the top, regenerations appended below."""
    report = await _get_owned_report(report_id, user, db)
    result = await db.scalars(
        select(Report)
        .where(
            Report.user_id == user.id,
            Report.dataset_id == report.dataset_id,
            Report.goal == report.goal,
            Report.archived.is_(False),
        )
        .order_by(Report.created_at.asc())
    )
    return list(result)


@router.post("/{report_id}/archive", response_model=ReportRead)
async def archive_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Soft-delete a single report version; restorable from the archived view."""
    report = await _get_owned_report(report_id, user, db)
    report.archived = True
    await db.commit()
    await db.refresh(report)
    return report


@router.post("/{report_id}/unarchive", response_model=ReportRead)
async def unarchive_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = await _get_owned_report(report_id, user, db)
    report.archived = False
    await db.commit()
    await db.refresh(report)
    return report


@router.get("/{report_id}/stream")
async def stream_report(
    report_id: uuid.UUID,
    fresh: bool = Query(
        False, description="Skip the result cache and force a new generation."
    ),
    variant: int = Query(0, description="Regeneration index; nudges a fresh angle."),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = await _get_owned_report(report_id, user, db)

    # Already finished (e.g. a page reload after completion) — nothing to run.
    if report.status == ReportStatus.completed:
        async def replay():
            yield {"event": "report_done",
                   "data": json.dumps({"report_id": str(report.id)})}
        return EventSourceResponse(replay())

    dataset = await db.scalar(
        select(Dataset)
        .where(Dataset.id == report.dataset_id, Dataset.user_id == user.id)
        .options(selectinload(Dataset.columns))
    )
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found"
        )

    # Result cache: an identical goal on the same dataset produces an identical
    # report. Reuse a prior completed run's content instead of paying to
    # regenerate it — the biggest single saving on repeats. Skipped for explicit
    # regenerations (`fresh`), which must produce a new version.
    cached = None if fresh else await db.scalar(
        select(Report)
        .where(
            Report.user_id == user.id,
            Report.dataset_id == report.dataset_id,
            Report.goal == report.goal,
            Report.status == ReportStatus.completed,
            Report.content.isnot(None),
            Report.id != report.id,
        )
        .order_by(Report.created_at.desc())
    )
    if cached is not None:
        report.content = cached.content
        report.status = ReportStatus.completed
        report.input_tokens = 0
        report.output_tokens = 0
        report.cost_usd = 0.0  # reused — no new inference spend
        report.error = None
        await db.commit()

        async def replay_cached():
            yield {"event": "report_done",
                   "data": json.dumps({"report_id": str(report.id), "cost_usd": 0.0,
                                       "input_tokens": 0, "output_tokens": 0,
                                       "cached": True})}
        return EventSourceResponse(replay_cached())

    # A failed report can be retried simply by re-opening the stream.
    if report.status == ReportStatus.failed:
        report.status = ReportStatus.running
        report.error = None
        await db.commit()

    ctx = DatasetContext.from_models(dataset, dataset.columns)

    async def event_generator():
        sections: list[dict] = []
        current: dict | None = None
        usage = UsageTracker()
        try:
            async for ev in generate_report_events(
                ctx, report.goal, usage=usage, variant=variant,
            ):
                etype = ev["event"]
                if etype == "section_start":
                    current = {
                        "title": json.loads(ev["data"])["title"],
                        "narrative": "",
                        "charts": [],
                    }
                    sections.append(current)
                elif etype == "token" and current is not None:
                    current["narrative"] += ev["data"]
                elif etype == "chart" and current is not None:
                    current["charts"].append(json.loads(ev["data"]).get("spec"))
                elif etype == "section_end":
                    current = None
                yield ev

            report.content = sections
            report.status = ReportStatus.completed
            report.input_tokens = usage.input_tokens
            report.output_tokens = usage.output_tokens
            report.cost_usd = usage.cost_usd
            await db.commit()
            yield {"event": "report_done",
                   "data": json.dumps({
                       "report_id": str(report.id),
                       "cost_usd": usage.cost_usd,
                       "input_tokens": usage.input_tokens,
                       "output_tokens": usage.output_tokens,
                   })}
        except Exception as exc:  # noqa: BLE001 — record failure, tell the client
            logger.exception("Report generation failed for %s", report.id)
            detail = friendly_error_detail(exc)
            report.status = ReportStatus.failed
            report.error = detail[:2048]
            report.content = sections or None
            await db.commit()
            yield {"event": "error", "data": json.dumps({"detail": detail})}

    return EventSourceResponse(event_generator())


def _content_stats(content) -> tuple[int, int, list[str]]:
    """(section_count, chart_count, distinct_chart_types) from a report's content."""
    if not isinstance(content, list):
        return 0, 0, []
    types: list[str] = []
    for section in content:
        for chart in (section or {}).get("charts") or []:
            t = chart.get("type") if isinstance(chart, dict) else None
            if t:
                types.append(t)
    # distinct, first-seen order preserved
    distinct = list(dict.fromkeys(types))
    return len(content), len(types), distinct


@router.get("", response_model=list[ReportRead])
async def list_reports(
    dataset_id: uuid.UUID | None = None,
    archived: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Report).where(
        Report.user_id == user.id, Report.archived == archived
    )
    if dataset_id is not None:
        query = query.where(Report.dataset_id == dataset_id)
    result = await db.scalars(query.order_by(Report.created_at.desc()))
    # Enrich each row with lightweight content stats for the dashboard.
    out = []
    for report in result:
        sections, charts, types = _content_stats(report.content)
        out.append(
            ReportRead.model_validate(report).model_copy(
                update={
                    "section_count": sections,
                    "chart_count": charts,
                    "chart_types": types,
                }
            )
        )
    return out


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _get_owned_report(report_id, user, db)


@router.patch("/{report_id}", response_model=ReportRead)
async def rename_report(
    report_id: uuid.UUID,
    payload: ReportUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = await _get_owned_report(report_id, user, db)
    report.title = payload.title.strip()
    await db.commit()
    await db.refresh(report)
    return report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = await _get_owned_report(report_id, user, db)
    await db.delete(report)
    await db.commit()
