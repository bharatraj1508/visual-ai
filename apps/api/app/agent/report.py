"""Multi-section report generation.

Flow: a planner proposes section titles, then the analyst agent (reused from
M4) writes each section — running queries and producing charts — while events
stream to the client. Both the planner and the agent factory are injected so
the orchestration is testable without a live LLM.
"""
from __future__ import annotations

import json
import re
from typing import AsyncIterator, Awaitable, Callable

from app.agent.context import DatasetContext
from app.agent.graph import build_agent, build_model
from app.agent.streaming import stream_agent_events

Planner = Callable[[DatasetContext, str], Awaitable[list[str]]]
AgentFactory = Callable[[DatasetContext], tuple]

_FALLBACK_SECTIONS = [
    "Overview & Data Quality",
    "Key Distributions",
    "Notable Relationships",
    "Summary & Takeaways",
]


async def default_planner(ctx: DatasetContext, goal: str) -> list[str]:
    """Ask the LLM for 3–6 section titles; fall back to a generic outline."""
    prompt = (
        f"{ctx.schema_text()}\n\n"
        f"The user wants this report: {goal!r}.\n"
        "Propose 3 to 6 concise section titles that together form a thorough "
        "analytical report on THIS dataset. Respond with ONLY a JSON array of "
        'strings, e.g. ["Overview", "Trends"].'
    )
    resp = await build_model().ainvoke(prompt)
    content = resp.content if isinstance(resp.content, str) else str(resp.content)
    match = re.search(r"\[.*\]", content, re.DOTALL)
    if match:
        try:
            titles = [str(t).strip() for t in json.loads(match.group(0)) if str(t).strip()]
            if titles:
                return titles[:6]
        except json.JSONDecodeError:
            pass
    return _FALLBACK_SECTIONS


async def generate_report_events(
    ctx: DatasetContext,
    goal: str,
    *,
    planner: Planner,
    agent_factory: AgentFactory,
) -> AsyncIterator[dict]:
    """Yield SSE dicts for a full report run.

    Events: report_start, section_start, token, tool_start, tool_end, chart,
    section_end, error. The endpoint layers report_done after persisting.
    """
    titles = await planner(ctx, goal)
    yield {"event": "report_start", "data": json.dumps({"sections": titles})}

    for index, title in enumerate(titles):
        yield {
            "event": "section_start",
            "data": json.dumps({"index": index, "title": title}),
        }
        agent, collector = agent_factory(ctx)
        section_prompt = (
            f"Write the report section titled '{title}' for the goal: {goal}. "
            "Analyze the data with tools, include a chart if it helps, and keep "
            "the narrative concise. Do not restate raw table rows."
        )
        async for ev in stream_agent_events(agent, [("user", section_prompt)], collector):
            yield ev
        yield {"event": "section_end", "data": json.dumps({"index": index})}
