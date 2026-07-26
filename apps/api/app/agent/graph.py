"""Builds the LangGraph ReAct agent: Gemini + the dataset's tools.

build_agent returns (agent, chart_collector). The collector is a run-scoped
list that create_chart appends specs to; the caller persists/streams it.
"""
from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from app.agent.context import DatasetContext
from app.agent.prompts import system_prompt
from app.agent.tools.chart import build_chart_tool
from app.agent.tools.code import build_code_tool
from app.agent.tools.data import build_data_tools
from app.core.config import settings


def build_model(
    *, temperature: float = 0, max_retries: int | None = None
) -> ChatGoogleGenerativeAI:
    if settings.GOOGLE_API_KEY is None:
        raise RuntimeError(
            "GOOGLE_API_KEY is not configured. Set it in the environment to "
            "use the agent."
        )
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GOOGLE_API_KEY.get_secret_value(),
        # Default temperature=0 keeps agent tool-use deterministic. One-shot
        # ideation calls (report suggestions) override this for variety.
        temperature=temperature,
        # Retry transient errors (503 overload, 429, 500) with backoff. The
        # library retries the underlying call, transparent to streaming.
        max_retries=settings.LLM_MAX_RETRIES if max_retries is None else max_retries,
    )


def build_agent(ctx: DatasetContext):
    """Return (compiled_agent, chart_collector) for one dataset."""
    collector: list[dict] = []
    tools = build_data_tools(ctx) + [
        build_chart_tool(ctx, collector),
        build_code_tool(ctx),
    ]
    agent = create_react_agent(
        build_model(), tools, prompt=system_prompt(ctx)
    )
    return agent, collector
