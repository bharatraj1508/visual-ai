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


# Fields the installed ChatGoogleGenerativeAI actually accepts. We feature-detect
# so cost controls (output cap, thinking budget) apply where supported without
# breaking on older/newer library versions that name or omit them differently.
_MODEL_FIELDS = set(ChatGoogleGenerativeAI.model_fields)


def build_model(
    *,
    temperature: float = 0,
    max_retries: int | None = None,
    max_output_tokens: int | None = None,
) -> ChatGoogleGenerativeAI:
    if settings.GOOGLE_API_KEY is None:
        raise RuntimeError(
            "GOOGLE_API_KEY is not configured. Set it in the environment to "
            "use the agent."
        )
    kwargs: dict = {
        "model": settings.GEMINI_MODEL,
        "google_api_key": settings.GOOGLE_API_KEY.get_secret_value(),
        # Default temperature=0 keeps agent tool-use deterministic. One-shot
        # ideation calls (report suggestions) override this for variety.
        "temperature": temperature,
        # Retry transient errors (503 overload, 429, 500) with backoff. The
        # library retries the underlying call, transparent to streaming.
        "max_retries": settings.LLM_MAX_RETRIES if max_retries is None else max_retries,
    }
    # Cap output tokens where the library exposes it — bounds cost and verbosity.
    if max_output_tokens is not None and "max_output_tokens" in _MODEL_FIELDS:
        kwargs["max_output_tokens"] = max_output_tokens
    # Keep "thinking" minimal (our reasoning is done in Python). Gemini-3 models
    # reject a budget of 0, so we send a low positive cap from config rather than
    # hardcoding 0; None means "don't send" (use the model default).
    if settings.LLM_THINKING_BUDGET is not None and "thinking_budget" in _MODEL_FIELDS:
        kwargs["thinking_budget"] = settings.LLM_THINKING_BUDGET
    return ChatGoogleGenerativeAI(**kwargs)


def build_agent(ctx: DatasetContext):
    """Return (compiled_agent, chart_collector) for one dataset."""
    collector: list[dict] = []
    tools = build_data_tools(ctx) + [
        build_chart_tool(ctx, collector),
        build_code_tool(ctx),
    ]
    agent = create_react_agent(
        build_model(max_output_tokens=settings.CHAT_MAX_OUTPUT_TOKENS),
        tools,
        prompt=system_prompt(ctx),
    )
    return agent, collector
