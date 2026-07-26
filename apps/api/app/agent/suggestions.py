"""Analyze a dataset and propose reports worth generating.

One LLM call turns the dataset's column profile into a handful of concrete
report ideas — each a title, the analytical question it answers, the findings
to expect, and the chart types that would back it up. The prompt is grounded
only in the schema (never raw rows), and a schema-derived fallback keeps the
panel useful even when the model is unavailable or returns junk.
"""
from __future__ import annotations

import json
import re

from app.agent.context import DatasetContext
from app.agent.graph import build_model
from app.agent.tools.chart_spec import CHART_TYPES
from app.core.logging import logger

_ALLOWED_CHARTS = set(CHART_TYPES)

# Chart vocabulary the frontend can render — kept in sync with chart_spec.py.
_CHART_VOCAB = (
    "bar, grouped_bar, stacked_bar, line, multi_line, area, stacked_area, "
    "scatter, pie, donut, histogram, dual_axis, radar"
)

SUGGESTION_COUNT = 5

# A worked example shows the model the DEPTH we want — a report is a
# multi-column investigation with a thesis, not a single chart.
_EXAMPLE = (
    '{"title": "What separates high-churn customers from loyal ones?", '
    '"question": "Comparing churned vs. retained customers, which combination '
    'of tenure, monthly_charges, and contract_type best predicts churn?", '
    '"rationale": "Segment the base into churned vs. retained cohorts, then '
    'compare distributions and rates across contract type and charge bands to '
    'isolate the highest-risk profile. Expect month-to-month, high-charge, '
    'short-tenure customers to dominate churn.", '
    '"chart_types": ["grouped_bar", "stacked_bar", "scatter"]}'
)

_PROMPT = """{schema}

You are a senior data analyst scoping an engagement. You have just been handed \
the dataset above. Propose the {count} highest-value reports to build from it.

Think like an analyst, not a chart generator. Each report must be a genuine \
INVESTIGATION with a thesis — it should combine, segment, or relate MULTIPLE \
columns and lead to an actionable insight. Draw on the column names, types, \
sample values and cardinalities to ground every idea in THIS dataset's actual \
subject matter.

Strongly prefer reports that:
- segment the population into cohorts and compare them (e.g. high vs. low on an \
outcome, or across a key category);
- identify the drivers or correlates of an important outcome variable;
- profile a notable group (at-risk, top performers, outliers) across several signals;
- examine how a metric shifts across one dimension while accounting for another;
- surface anomalies, imbalances, or surprising distributions.

Hard rules:
- Do NOT propose trivial one-variable or two-variable lookups. Titles like \
"age vs hours", "distribution of X", "overview", or "X by Y" are single charts, \
NOT reports — never use them.
- Each report must reference at least TWO real columns from the schema by name.
- The 5 reports must be genuinely distinct angles, not rephrasings of each other.

Return each report as an object:
- "title": a specific, insight-oriented name, ideally phrased as the finding or \
question (e.g. the example below)
- "question": the precise analytical question, naming the columns involved and \
the comparison/segmentation being made
- "rationale": 1-2 sentences covering BOTH the analytical approach (segmentation, \
correlation, cohort comparison, driver analysis...) and the insight you expect
- "chart_types": 2-4 types from [{charts}] that would best evidence the analysis

Example of the expected depth:
{example}

Respond with ONLY a JSON array of exactly {count} such objects — no prose."""


async def suggest_reports(ctx: DatasetContext, count: int = SUGGESTION_COUNT) -> list[dict]:
    """Return `count` report ideas as dicts: title, question, rationale, chart_types."""
    prompt = _PROMPT.format(
        schema=ctx.schema_text(),
        count=count,
        charts=_CHART_VOCAB,
        example=_EXAMPLE,
    )
    try:
        # A little temperature for varied angles; the default retry count keeps
        # a transient blip from silently dropping us to the shallow fallback.
        resp = await build_model(temperature=0.7).ainvoke(prompt)
    except Exception:  # noqa: BLE001 — fall back rather than fail the panel
        logger.warning(
            "Suggestion generation failed for dataset %s; using fallback ideas.",
            ctx.dataset_id,
            exc_info=True,
        )
        return _fallback(ctx, count)

    parsed = _parse(_extract_text(resp.content))
    if not parsed:
        logger.warning(
            "Suggestion output for dataset %s was unparseable; using fallback.",
            ctx.dataset_id,
        )
        return _fallback(ctx, count)
    return parsed[:count]


def _extract_text(content) -> str:
    """Gemini responses carry either a str or a list of content-part dicts.

    Stringifying the list directly yields Python repr (single quotes), which is
    not valid JSON — so we must join the parts' text instead.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            (part.get("text", "") or "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content)


def _parse(content: str) -> list[dict]:
    match = re.search(r"\[.*\]", content, re.DOTALL)
    if not match:
        return []
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        question = str(item.get("question", "")).strip()
        if not title or not question:
            continue
        # Keep only chart types we can actually render — the model sometimes
        # invents ones like "heatmap".
        chart_types = [
            c
            for c in (str(x).strip().lower() for x in item.get("chart_types", []))
            if c in _ALLOWED_CHARTS
        ]
        out.append(
            {
                "title": title[:255],
                "question": question,
                "rationale": str(item.get("rationale", "")).strip()
                or "Explore this question across the dataset.",
                "chart_types": chart_types[:4] or ["bar", "line"],
            }
        )
    return out


def _fallback(ctx: DatasetContext, count: int) -> list[dict]:
    """Schema-derived ideas when the LLM can't be reached.

    Still framed as multi-column investigations rather than single charts, so a
    degraded panel doesn't look trivial.
    """
    numeric = [c["name"] for c in ctx.columns if _is_numeric(c)]
    categorical = [c["name"] for c in ctx.columns if not _is_numeric(c)]
    ideas: list[dict] = []

    if numeric and categorical:
        n, c = numeric[0], categorical[0]
        ideas.append(
            {
                "title": f"Which {c} segments drive {n}?",
                "question": f"How does {n} differ across {c} cohorts, and which "
                f"segments sit at the extremes?",
                "rationale": f"Segment records by {c} and compare {n} distributions "
                "and averages to isolate the strongest and weakest groups.",
                "chart_types": ["grouped_bar", "stacked_bar", "histogram"],
            }
        )
    if len(numeric) >= 3:
        ideas.append(
            {
                "title": f"What drives {numeric[0]}?",
                "question": f"Which of {', '.join(numeric[1:4])} correlate most "
                f"strongly with {numeric[0]}?",
                "rationale": "Assess pairwise correlations against the outcome to "
                "rank likely drivers and spot non-linear relationships.",
                "chart_types": ["scatter", "bar", "dual_axis"],
            }
        )
    if numeric:
        ideas.append(
            {
                "title": f"Profiling the extremes of {numeric[0]}",
                "question": f"How do records in the top and bottom deciles of "
                f"{numeric[0]} differ across the other fields?",
                "rationale": "Compare high vs. low cohorts across every dimension to "
                "build a profile of what characterizes each extreme.",
                "chart_types": ["grouped_bar", "radar", "scatter"],
            }
        )
    if len(categorical) >= 2:
        ideas.append(
            {
                "title": f"Interaction of {categorical[0]} and {categorical[1]}",
                "question": f"How does the composition of {categorical[1]} shift "
                f"across {categorical[0]}?",
                "rationale": f"Cross-tabulate {categorical[0]} against {categorical[1]} "
                "to reveal imbalances and co-occurrence patterns.",
                "chart_types": ["stacked_bar", "grouped_bar", "donut"],
            }
        )
    if len(numeric) >= 2 and categorical:
        ideas.append(
            {
                "title": f"{numeric[0]} vs {numeric[1]}, split by {categorical[0]}",
                "question": f"Does the relationship between {numeric[0]} and "
                f"{numeric[1]} hold across {categorical[0]} groups?",
                "rationale": "Overlay the relationship by segment to check whether a "
                "trend is universal or driven by particular groups.",
                "chart_types": ["scatter", "multi_line"],
            }
        )

    ideas.append(
        {
            "title": "Data quality & coverage audit",
            "question": "Where are the gaps, imbalances and outliers that could "
            "bias any downstream analysis?",
            "rationale": "Map missingness, cardinality and range across every column "
            "to establish what the dataset can and cannot support.",
            "chart_types": ["bar", "histogram"],
        }
    )

    # De-dup by title while preserving order, then top up if still short.
    seen: set[str] = set()
    deduped = [i for i in ideas if not (i["title"] in seen or seen.add(i["title"]))]
    while len(deduped) < count:
        deduped.append(
            {
                "title": "Key patterns & takeaways",
                "question": "What are the most consequential relationships in this data?",
                "rationale": "Synthesize the strongest signals across columns into a "
                "narrative of what matters most.",
                "chart_types": ["bar", "line"],
            }
        )
    return deduped[:count]


def _is_numeric(col: dict) -> bool:
    dtype = str(col.get("dtype", "")).lower()
    return any(t in dtype for t in ("int", "float", "double", "number", "decimal"))
