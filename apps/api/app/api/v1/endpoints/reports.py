"""Report endpoints. Generation streams over SSE (like chat, no job queue):
the report row is created as `running`, sections stream in, and the assembled
content is persisted as `completed` before the final `report_done` event.
"""
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.agent.context import DatasetContext
from app.agent.graph import build_agent
from app.agent.report import default_planner, generate_report_events
from app.core.database import get_db
from app.core.logging import logger
from app.core.security import get_current_user
from app.models.dataset import Dataset, DatasetStatus
from app.models.report import Report, ReportStatus
from app.models.user import User
from app.schemas.report import ReportCreate, ReportDetail, ReportRead

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


@router.post("")
async def create_report(
    payload: ReportCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = await db.scalar(
        select(Dataset)
        .where(Dataset.id == payload.dataset_id, Dataset.user_id == user.id)
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

    ctx = DatasetContext.from_models(dataset, dataset.columns)
    report = Report(
        user_id=user.id,
        dataset_id=dataset.id,
        title=payload.title or f"Report: {dataset.filename}",
        goal=payload.goal,
        status=ReportStatus.running,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    async def event_generator():
        sections: list[dict] = []
        current: dict | None = None
        try:
            async for ev in generate_report_events(
                ctx, payload.goal,
                planner=default_planner, agent_factory=build_agent,
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
            await db.commit()
            yield {"event": "report_done",
                   "data": json.dumps({"report_id": str(report.id)})}
        except Exception as exc:  # noqa: BLE001 — record failure, tell the client
            logger.exception("Report generation failed for %s", report.id)
            report.status = ReportStatus.failed
            report.error = str(exc)[:2048]
            report.content = sections or None
            await db.commit()
            yield {"event": "error", "data": json.dumps({"detail": str(exc)})}

    return EventSourceResponse(event_generator())


@router.get("", response_model=list[ReportRead])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.scalars(
        select(Report)
        .where(Report.user_id == user.id)
        .order_by(Report.created_at.desc())
    )
    return list(result)


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _get_owned_report(report_id, user, db)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = await _get_owned_report(report_id, user, db)
    await db.delete(report)
    await db.commit()
