"""Chat endpoints: manage sessions and stream an agent turn over SSE.

The message endpoint persists the user turn, streams the agent's tokens / tool
activity / charts as Server-Sent Events, then persists the assistant turn and
its chart artifacts before emitting a final `done` event.
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
from app.agent.streaming import stream_agent_events
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.artifact import Artifact
from app.models.chat_session import ChatSession
from app.models.dataset import Dataset, DatasetStatus
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import ChatRequest, MessageRead, SessionCreate, SessionRead

router = APIRouter()


async def _get_owned_session(
    session_id: uuid.UUID, user: User, db: AsyncSession
) -> ChatSession:
    session = await db.scalar(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user.id
        )
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    return session


@router.post("/sessions", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreate,
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
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Dataset is not ready (status: {dataset.status.value})",
        )
    session = ChatSession(
        user_id=user.id,
        dataset_id=dataset.id,
        title=payload.title or f"Chat about {dataset.filename}",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=list[SessionRead])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.scalars(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.created_at.desc())
    )
    return list(result)


@router.get("/sessions/{session_id}/messages", response_model=list[MessageRead])
async def list_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_owned_session(session_id, user, db)
    result = await db.scalars(
        select(Message)
        .where(Message.session_id == session_id)
        .options(selectinload(Message.artifacts))
        .order_by(Message.created_at)
    )
    return list(result)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = await _get_owned_session(session_id, user, db)
    await db.delete(session)
    await db.commit()


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: uuid.UUID,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = await _get_owned_session(session_id, user, db)
    dataset = await db.scalar(
        select(Dataset)
        .where(Dataset.id == session.dataset_id)
        .options(selectinload(Dataset.columns))
    )
    if dataset is None or dataset.status != DatasetStatus.ready:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dataset for this session is not available",
        )

    ctx = DatasetContext.from_models(dataset, dataset.columns)
    try:
        agent, collector = build_agent(ctx)
    except RuntimeError as exc:
        # e.g. missing GOOGLE_API_KEY
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )

    # Persist the user turn immediately so it survives a dropped connection.
    user_msg = Message(
        session_id=session.id, role="user", content=payload.content
    )
    db.add(user_msg)
    await db.commit()

    history = await db.scalars(
        select(Message)
        .where(Message.session_id == session.id)
        .order_by(Message.created_at)
    )
    lc_messages = [
        (m.role, m.content)
        for m in history
        if m.role in ("user", "assistant") and m.content
    ]

    async def event_generator():
        assistant_parts: list[str] = []
        async for ev in stream_agent_events(agent, lc_messages, collector):
            if ev["event"] == "token":
                assistant_parts.append(ev["data"])
            yield ev

        assistant_msg = Message(
            session_id=session.id,
            role="assistant",
            content="".join(assistant_parts).strip(),
        )
        db.add(assistant_msg)
        await db.flush()
        for chart in collector:
            db.add(
                Artifact(
                    message_id=assistant_msg.id,
                    kind=chart["kind"],
                    title=chart.get("title"),
                    spec=chart["spec"],
                )
            )
        await db.commit()
        yield {
            "event": "done",
            "data": json.dumps({"message_id": str(assistant_msg.id)}),
        }

    return EventSourceResponse(event_generator())
