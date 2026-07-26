"""Report generation — deterministic analysis first, LLM as writer only.

The old design ran a full ReAct agent loop *per section*: every statistic was a
model round-trip that re-sent the system prompt, six tool schemas, and the
growing tool-result history. That re-sent context 15–30× per report and was the
dominant cost.

The new design inverts it:
  1. Python computes an exhaustive analysis battery — every notable statistic —
     as exact ``Finding`` objects plus ready-to-render charts (``analysis.py``).
     Zero tokens.
  2. ONE structured "plan" call selects and orders findings into sections and
     writes the executive summary + recommendations (it sees everything at once).
  3. ONE streamed narrative call per analytical section turns that section's
     assigned findings into prose. No tools, no loop, no re-sent history.

The LLM never calculates and never authors SQL, so report numbers are
Python-exact and charts are always valid. The SSE event contract is unchanged,
so the endpoint and frontend are untouched:
  report_start, section_start, token, chart, section_end, error.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import AsyncIterator

from app.agent.analysis import AnalysisResult, Finding, run_analysis
from app.agent.context import DatasetContext
from app.agent.cost import UsageTracker, usage_from_message
from app.agent.graph import build_model
from app.core.config import settings
from app.core.logging import logger

_EXEC_TITLE = "Executive Summary"
_RECS_TITLE = "Recommendations"


async def generate_report_events(
    ctx: DatasetContext, goal: str, *, usage: UsageTracker | None = None, variant: int = 0
) -> AsyncIterator[dict]:
    """Yield SSE dicts for a full report run (see module docstring for events).

    ``variant`` > 0 marks a regeneration and nudges the planner toward a fresh
    angle so a re-run reads differently from the original.
    """
    # 1a. Cheap semantic spec: one small LLM call decides the readable entity
    # name, the id to collapse duplicate rows on, valid groupings, etc. — the
    # understanding pandas can't infer (name vs id, per-match vs per-tournament).
    spec = await _infer_spec(ctx, goal, usage)

    # 1b. Deterministic battery — pandas is blocking, so offload it.
    analysis = await asyncio.to_thread(run_analysis, ctx, goal, spec)

    # 2. Plan call: pick/order findings into sections + write summary & recs.
    plan = await _plan(ctx, goal, analysis, usage, variant)

    # A section with no findings assigned has nothing to narrate — drop it so the
    # announced titles match what we actually stream.
    plan_sections = [s for s in plan["sections"] if s["finding_ids"]]

    titles = [_EXEC_TITLE] + [s["title"] for s in plan_sections] + [_RECS_TITLE]
    yield {"event": "report_start", "data": json.dumps({"sections": titles})}

    index = 0
    # Executive summary — already written during planning; emit as one block.
    async for ev in _static_section(index, _EXEC_TITLE, plan["exec_summary"], []):
        yield ev
    index += 1

    # Analytical sections — one streamed narrative call each.
    for section in plan_sections:
        section_findings = analysis.findings_by_id(section["finding_ids"])
        charts = [analysis.charts[c] for c in section["chart_ids"] if c in analysis.charts]
        charts = charts[: settings.REPORT_MAX_CHARTS_PER_SECTION]  # keep sections from piling up charts
        yield {"event": "section_start",
               "data": json.dumps({"index": index, "title": section["title"]})}
        async for ev in _write_section(goal, section["title"], section_findings, usage):
            yield ev
        for chart in charts:
            yield {"event": "chart", "data": json.dumps(chart, default=str)}
        yield {"event": "section_end", "data": json.dumps({"index": index})}
        index += 1

    # Recommendations — written during planning; emit as a bulleted block.
    recs = "\n".join(f"- {r}" for r in plan["recommendations"]) or "- No specific actions identified."
    async for ev in _static_section(index, _RECS_TITLE, recs, []):
        yield ev


# --------------------------------------------------------------------------- #
# Planning
# --------------------------------------------------------------------------- #
_PLAN_PROMPT = """Report goal: {goal}

Below are pre-computed findings about the dataset. Every number is exact — you \
MUST NOT invent, alter, or recompute any value; only select and organize.

Findings:
{digest}

Available charts:
{charts}

Assemble a rich, insightful report as a JSON object with exactly these keys:
- "exec_summary": 3-4 sentences synthesizing the most important, goal-relevant findings.
- "sections": 4 to 6 objects, each {{"title": ..., "finding_ids": [ids], "chart_ids": [ids]}}:
    * TITLE must be specific and insight-oriented, phrased as a finding or a question \
(e.g. "What separates the top performers?") — never a generic label like "Overview" or "Analysis".
    * Group 2-4 RELATED findings per section into a coherent theme; order sections most \
to least important for the goal.
    * Distribute charts so every section has 1-2 — do NOT pile many charts into one section, \
and favour a VARIETY of chart types across the report rather than repeating one.
    * Use each finding id at most once across all sections.
- "recommendations": 3-5 concrete, action-oriented bullets grounded in the findings.

Focus ruthlessly on the goal: build the report around the findings that answer it, and \
OMIT findings about unrelated columns even though they are listed. Lead with the finding(s) \
that most directly address the goal.

Respond with ONLY the JSON object, no prose."""


_SPEC_PROMPT = """Report goal: {goal}

Configure an automated analysis of the table above. First reason about its GRAIN — is \
there one row per entity, or several (e.g. one row per player PER MATCH)? — then decide \
what each column means. Respond with ONLY a JSON object:
- "entity_column": the human-READABLE column naming the entity the goal profiles (a \
person/player/customer/product NAME), or null. Prefer a name over an id code.
- "dedupe_column": the column that uniquely identifies that entity (an id), or null.
- "entity_grain": true if the goal ranks/profiles those entities AND the table has \
multiple rows per entity (so we collapse to one row per entity first); else false.
- "rank_measures": up to 4 numeric columns that best express how good/important an \
entity is for THIS goal, most relevant first.
- "segment_dimensions": up to 4 categorical columns that are meaningful, STABLE \
groupings for the goal (attributes of the entity such as position/team/nationality); \
exclude per-event columns like match stage, result, or date.
- "avoid_columns": columns misleading to aggregate or chart — ids, codes, jersey/shirt \
numbers, timestamps, and denormalized per-entity totals that must not be summed across rows.

Use only column names that appear in the schema. Respond with ONLY the JSON object."""


async def _infer_spec(
    ctx: DatasetContext, goal: str, usage: UsageTracker | None
) -> dict:
    """One cheap call for the semantic understanding pandas can't infer. Returns
    {} on any failure so the battery falls back to heuristics."""
    try:
        resp = await build_model(
            max_output_tokens=settings.REPORT_PLAN_MAX_OUTPUT_TOKENS
        ).ainvoke(
            [("system", ctx.schema_text()), ("user", _SPEC_PROMPT.format(goal=goal))]
        )
    except Exception:  # noqa: BLE001 — heuristics are a fine fallback
        logger.warning("Analysis spec inference failed; using heuristics.", exc_info=True)
        return {}
    if usage is not None:
        usage.add(*usage_from_message(resp))
    raw = _parse_object(_extract_text(resp.content))
    if not raw:
        return {}
    names = {c["name"] for c in ctx.columns}

    def cols(key: str) -> list[str]:
        v = raw.get(key)
        return [x for x in v if isinstance(x, str) and x in names] if isinstance(v, list) else []

    ec = raw.get("entity_column")
    dc = raw.get("dedupe_column")
    return {
        "entity_column": ec if ec in names else None,
        "dedupe_column": dc if dc in names else None,
        "entity_grain": bool(raw.get("entity_grain")),
        "rank_measures": cols("rank_measures"),
        "segment_dimensions": cols("segment_dimensions"),
        "avoid_columns": cols("avoid_columns"),
    }


def _parse_object(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


async def _plan(
    ctx: DatasetContext,
    goal: str,
    analysis: AnalysisResult,
    usage: UsageTracker | None,
    variant: int = 0,
) -> dict:
    """One structured call. Falls back to a deterministic plan on any failure."""
    if not analysis.findings:
        return _fallback_plan(analysis)
    user = _PLAN_PROMPT.format(
        goal=goal, digest=analysis.digest_text(), charts=analysis.chart_index_text()
    )
    if variant:
        # A regeneration: ask for a different structure/emphasis so it reads fresh.
        user += (
            "\n\nThis is an alternate take (regeneration): organize the report "
            "differently and emphasize different angles than a conventional structure, "
            "while staying accurate to the findings."
        )
    try:
        # schema_text goes in the SYSTEM slot: it's identical for every call on
        # this dataset, so it forms a stable prefix that implicit context caching
        # can reuse across the plan call and future reports.
        resp = await build_model(
            max_output_tokens=settings.REPORT_PLAN_MAX_OUTPUT_TOKENS
        ).ainvoke([("system", ctx.schema_text()), ("user", user)])
    except Exception:  # noqa: BLE001 — degrade to a deterministic outline
        # Log rather than swallow: a *persistent* failure here (bad model config,
        # invalid argument) would otherwise silently ship a degraded report.
        logger.warning("Report plan call failed; using deterministic outline.", exc_info=True)
        return _fallback_plan(analysis)
    if usage is not None:
        usage.add(*usage_from_message(resp))
    parsed = _parse_plan(_extract_text(resp.content), analysis)
    return parsed or _fallback_plan(analysis)


def _parse_plan(text: str, analysis: AnalysisResult) -> dict | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    valid_f = {f.id for f in analysis.findings}
    valid_c = set(analysis.charts)
    used: set[str] = set()
    sections = []
    for s in raw.get("sections", []):
        if not isinstance(s, dict):
            continue
        title = str(s.get("title", "")).strip()
        if not title:
            continue
        fids = [i for i in s.get("finding_ids", []) if i in valid_f and i not in used]
        used.update(fids)
        cids = [i for i in s.get("chart_ids", []) if i in valid_c]
        sections.append({"title": title[:120], "finding_ids": fids, "chart_ids": cids})
    if not sections:
        return None
    exec_summary = str(raw.get("exec_summary", "")).strip()
    recs = [str(r).strip() for r in raw.get("recommendations", []) if str(r).strip()]
    return {
        "exec_summary": exec_summary or _default_summary(analysis),
        "sections": sections[:6],
        "recommendations": recs[:5] or _default_recs(analysis),
    }


def _fallback_plan(analysis: AnalysisResult) -> dict:
    """Deterministic outline: group findings by kind. Used when the LLM plan call
    fails or returns junk, so a report never dies at the planning step."""
    groups = [
        ("Top Performers", ("entity",)),
        ("Performance vs Expectation", ("performance",)),
        ("Key Relationships & Drivers", ("correlation",)),
        ("Segment Comparisons", ("segment",)),
        ("Cohort Profiles & Cross-Tabs", ("cohort", "crosstab")),
        ("Composition & Distributions", ("category", "distribution")),
        ("Trends Over Time", ("trend",)),
        ("Data Overview & Quality", ("overview", "quality")),
    ]
    sections = []
    for title, kinds in groups:
        fs = [f for f in analysis.findings if f.kind in kinds]
        if not fs:
            continue
        sections.append({
            "title": title,
            "finding_ids": [f.id for f in fs],
            "chart_ids": [f.chart_id for f in fs if f.chart_id],
        })
    if not sections:  # nothing computed at all
        sections = [{"title": "Overview", "finding_ids": [f.id for f in analysis.findings],
                     "chart_ids": []}]
    return {
        "exec_summary": _default_summary(analysis),
        "sections": sections[:4],
        "recommendations": _default_recs(analysis),
    }


def _default_summary(analysis: AnalysisResult) -> str:
    return " ".join(f.text for f in analysis.findings[:2]) or "Analysis of the dataset."


def _default_recs(analysis: AnalysisResult) -> list[str]:
    recs = []
    if any(f.kind == "quality" and "missing" in f.text for f in analysis.findings):
        recs.append("Address the missing-value gaps before relying on affected columns.")
    if any(f.kind == "correlation" for f in analysis.findings):
        recs.append("Investigate the strongest correlations for causal drivers.")
    return recs or ["Review the highlighted findings with domain stakeholders."]


# --------------------------------------------------------------------------- #
# Section narrative
# --------------------------------------------------------------------------- #
_SECTION_PROMPT = """You are writing one section of an analytical data report. Overall goal: {goal}
Section title: "{title}"

Base the section ONLY on these pre-computed findings (every number is exact — never \
invent, change, or add numbers):
{findings}

Write a substantial, insightful paragraph (roughly 120-180 words) that interprets these \
findings for the goal: state what the pattern is, cite the concrete numbers, explain WHY \
it matters, and what it implies or what to do about it. Be specific and analytical, and \
connect the findings to each other where relevant. Do not use headings or bullet lists, \
do not restate raw tables, and do not describe chart axes (charts are shown automatically)."""


async def _write_section(
    goal: str, title: str, findings: list[Finding], usage: UsageTracker | None
) -> AsyncIterator[dict]:
    """Stream one section's narrative from its findings (no tools, single call)."""
    if not findings:
        return
    findings_text = "\n".join(f"- {f.text}" for f in findings)
    prompt = _SECTION_PROMPT.format(goal=goal, title=title, findings=findings_text)
    model = build_model(max_output_tokens=settings.REPORT_SECTION_MAX_OUTPUT_TOKENS)
    gathered = None
    async for chunk in model.astream(prompt):
        gathered = chunk if gathered is None else gathered + chunk
        text = _extract_text(getattr(chunk, "content", ""))
        if text:
            yield {"event": "token", "data": text}
    if usage is not None and gathered is not None:
        usage.add(*usage_from_message(gathered))


async def _static_section(
    index: int, title: str, body: str, charts: list[dict]
) -> AsyncIterator[dict]:
    """Emit a section whose text is already known (summary / recommendations)."""
    yield {"event": "section_start", "data": json.dumps({"index": index, "title": title})}
    if body:
        yield {"event": "token", "data": body}
    for chart in charts:
        yield {"event": "chart", "data": json.dumps(chart, default=str)}
    yield {"event": "section_end", "data": json.dumps({"index": index})}


def _extract_text(content) -> str:
    """Gemini content is either a str or a list of content-part dicts."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            (p.get("text", "") or "") if isinstance(p, dict) else str(p) for p in content
        )
    return str(content) if content else ""
