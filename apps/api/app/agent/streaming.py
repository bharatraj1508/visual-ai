"""Translate a LangGraph agent run into Server-Sent Events.

Event types emitted (SSE `event:` field):
  token       — a chunk of the assistant's streaming text
  tool_start  — a tool began (name + input)
  tool_end    — a tool finished (name)
  chart       — a newly created chart artifact (id, title, Vega-Lite spec)
  error       — the run raised
The endpoint layers `done` on top once persistence completes.
"""
from __future__ import annotations

import json
from typing import AsyncIterator

from app.core.logging import logger


def _chunk_text(chunk) -> str:
    """Gemini message chunks carry either a str or a list of content parts."""
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return ""


async def stream_agent_events(
    agent, messages: list, collector: list[dict]
) -> AsyncIterator[dict]:
    """Yield SSE dicts ({"event", "data"}) for one agent run.

    New entries in `collector` (charts) are flushed as `chart` events right
    after the tool that produced them completes.
    """
    flushed = 0
    try:
        async for event in agent.astream_events(
            {"messages": messages}, version="v2"
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                text = _chunk_text(event["data"]["chunk"])
                if text:
                    yield {"event": "token", "data": text}
            elif kind == "on_tool_start":
                yield {
                    "event": "tool_start",
                    "data": json.dumps(
                        {"name": event.get("name"),
                         "input": event["data"].get("input")},
                        default=str,
                    ),
                }
            elif kind == "on_tool_end":
                yield {
                    "event": "tool_end",
                    "data": json.dumps({"name": event.get("name")}),
                }
                while flushed < len(collector):
                    yield {
                        "event": "chart",
                        "data": json.dumps(collector[flushed], default=str),
                    }
                    flushed += 1
    except Exception as exc:  # noqa: BLE001 — surface any agent failure to the client
        logger.exception("Agent run failed")
        yield {"event": "error", "data": json.dumps({"detail": str(exc)})}
