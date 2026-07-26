"""Token-usage accounting and pricing for a report run.

A ``UsageTracker`` is threaded through generation and accumulates input/output
tokens from every LLM call (the planner plus each section's agent loop). The
totals are priced with the active model's per-token rates from settings.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


@dataclass
class UsageTracker:
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens += max(0, input_tokens)
        self.output_tokens += max(0, output_tokens)

    @property
    def cost_usd(self) -> float:
        return round(
            self.input_tokens / 1_000_000 * settings.GEMINI_INPUT_PRICE_PER_1M
            + self.output_tokens / 1_000_000 * settings.GEMINI_OUTPUT_PRICE_PER_1M,
            6,
        )


def usage_from_message(message) -> tuple[int, int]:
    """Extract (input_tokens, output_tokens) from a LangChain AIMessage.

    Gemini reports these in ``usage_metadata``; missing/partial data counts as
    zero so cost accounting degrades gracefully rather than crashing a run.
    """
    meta = getattr(message, "usage_metadata", None)
    if isinstance(meta, dict):
        return (
            int(meta.get("input_tokens") or 0),
            int(meta.get("output_tokens") or 0),
        )
    return 0, 0
