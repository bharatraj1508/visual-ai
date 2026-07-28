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
import os
import re
import tempfile
from collections.abc import Callable
from typing import AsyncIterator

from app.agent.analysis import AnalysisResult, Finding, run_analysis
from app.agent.context import DatasetContext
from app.agent.cost import UsageTracker, usage_from_message
from app.agent.graph import build_model
from app.core.config import settings
from app.core.logging import logger
from app.services import ingestion
from app.services.data_access import load_dataframe, query_tables

_EXEC_TITLE = "Executive Summary"
_RECS_TITLE = "Recommendations"


async def generate_report_events(
    ctx: DatasetContext, goal: str, *, usage: UsageTracker | None = None, variant: int = 0
) -> AsyncIterator[dict]:
    """Yield SSE dicts for a full report run (see module docstring for events).

    ``variant`` > 0 marks a regeneration and nudges the planner toward a fresh
    angle so a re-run reads differently from the original.
    """
    # 0. Multi-table datasets: assemble the tables the goal needs into one analysis
    # view (a single-table context) so the whole battery below is unchanged. Single-
    # table datasets pass straight through. `cleanup` removes any temp assembly file.
    actx, cleanup, assembly_note = await _prepare_analysis_context(ctx, goal, usage)
    try:
        async for ev in _run_report(actx, goal, usage, variant, assembly_note):
            yield ev
    finally:
        if cleanup:
            cleanup()


async def _run_report(
    ctx: DatasetContext,
    goal: str,
    usage: UsageTracker | None,
    variant: int,
    assembly_note: str | None,
) -> AsyncIterator[dict]:
    """The report pipeline over a SINGLE-table analysis context (see caller)."""
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
    # Executive summary — already written during planning; emit as one block. When
    # the analysis was scoped, lead with that statement so the reader always knows
    # which sub-population the whole report describes.
    exec_summary = plan["exec_summary"]
    if analysis.scope_note:
        exec_summary = f"{analysis.scope_note} {exec_summary}"
    if assembly_note:
        exec_summary = f"{assembly_note} {exec_summary}"
    async for ev in _static_section(index, _EXEC_TITLE, exec_summary, []):
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
- "scope": OPTIONAL row filter, used ONLY when the goal is meaningful for a specific \
sub-population and would be distorted by the rest — an object {{"column": <a categorical \
column>, "include": [values to KEEP], "reason": <short phrase naming the group>}}. E.g. a \
"goals conceded" goal → keep only defensive positions; a "enterprise churn" goal → keep only \
enterprise accounts. Use ONLY values that appear under "Category values" below, never invent \
them, and never list every value (that filters nothing). Set to null unless the restriction \
is clearly justified — most goals need no scope.

Use only column names that appear in the schema. Respond with ONLY the JSON object."""

# How many low-cardinality dimensions (and values each) to expose to the spec so it
# can pick a real sub-population — enough to be useful, bounded to stay token-cheap.
_MAX_SCOPE_DIMS = 8
_MAX_SCOPE_DIM_CARD = 20


def _dimension_values_text(ctx: DatasetContext) -> str:
    """List low-cardinality categorical/boolean columns with their FULL value sets.

    The schema only carries ≤3 sample values, too few to choose a scope from — so
    we read the actual distinct values (for columns small enough to enumerate) and
    hand them to the spec model. Best-effort: returns "" if the data can't be read.
    """
    try:
        df = load_dataframe(ctx.parquet_path)
    except Exception:  # noqa: BLE001 — the spec still works without this hint
        return ""
    lines: list[str] = []
    for c in ctx.columns:
        if c.get("dtype") not in ("categorical", "boolean"):
            continue
        name = c["name"]
        if name not in df.columns:
            continue
        vals = df[name].dropna().unique()
        if not 1 <= len(vals) <= _MAX_SCOPE_DIM_CARD:
            continue
        lines.append(f"- {name}: {', '.join(str(v) for v in vals)}")
        if len(lines) >= _MAX_SCOPE_DIMS:
            break
    if not lines:
        return ""
    return "Category values (candidate columns/values for scope):\n" + "\n".join(lines)


_ASSEMBLY_PROMPT = """Report goal: {goal}

This dataset has several tables (schema above). Write ONE DuckDB SQL SELECT that \
assembles just the data needed to answer the goal into a single result set: JOIN \
tables on their shared columns when the goal needs fields from more than one, or \
select from a single table when that is enough. Prefer LEFT JOINs from the most \
central table so rows aren't dropped, return ROW-LEVEL columns (do NOT aggregate or \
GROUP BY — the analysis happens afterwards), and reference tables by the names shown.

Respond with ONLY a JSON object: {{"sql": "SELECT ..."}}."""


async def _prepare_analysis_context(
    ctx: DatasetContext, goal: str, usage: UsageTracker | None
) -> tuple[DatasetContext, Callable[[], None] | None, str | None]:
    """For a multi-table dataset, combine the relevant tables into one analysis
    frame and return a single-table context over it (plus a cleanup fn for the temp
    file and a note to open the report with). Single-table datasets pass through
    unchanged. Any failure falls back to the largest single table."""
    if not ctx.is_multi():
        return ctx, None, None

    tables = [(t["name"], t["parquet_path"]) for t in ctx.all_tables()]
    sql = await _infer_assembly(ctx, goal, usage)
    if sql:
        try:
            def _assemble():
                df = query_tables(tables, sql)
                df = df.loc[:, ~df.columns.duplicated()]  # joins can repeat names
                fd, tmp = tempfile.mkstemp(suffix=".parquet")
                os.close(fd)
                try:
                    ingestion.write_parquet(df, tmp)
                    return df, tmp, ingestion.profile_dataframe(df)
                except Exception:  # noqa: BLE001 — don't leak the temp file on failure
                    _safe_remove(tmp)
                    raise

            df, tmp, profiles = await asyncio.to_thread(_assemble)
            if len(df) and profiles:
                actx = DatasetContext(
                    dataset_id=ctx.dataset_id, parquet_path=tmp, filename=ctx.filename,
                    row_count=len(df), columns=profiles,
                )
                names = ", ".join(t["name"] for t in ctx.all_tables())
                note = (
                    f"This report combines the dataset's tables ({names}) into a "
                    "single analysis view."
                )
                return actx, lambda: _safe_remove(tmp), note
            _safe_remove(tmp)
        except Exception:  # noqa: BLE001 — fall back to a single table below
            logger.warning("Report assembly failed; using the largest table.", exc_info=True)

    largest = max(ctx.all_tables(), key=lambda t: t.get("row_count") or 0)
    actx = DatasetContext(
        dataset_id=ctx.dataset_id, parquet_path=largest["parquet_path"],
        filename=largest["filename"], row_count=largest["row_count"],
        columns=largest["columns"],
    )
    note = (
        f"This report analyzes the '{largest['name']}' table "
        f"(one of {len(ctx.all_tables())} in the dataset)."
    )
    return actx, None, note


async def _infer_assembly(
    ctx: DatasetContext, goal: str, usage: UsageTracker | None
) -> str | None:
    """One LLM call → a DuckDB SELECT that assembles the multi-table view. Returns
    None on any failure so the caller falls back to a single table."""
    try:
        resp = await build_model(
            max_output_tokens=settings.REPORT_PLAN_MAX_OUTPUT_TOKENS
        ).ainvoke(
            [("system", ctx.schema_text()), ("user", _ASSEMBLY_PROMPT.format(goal=goal))]
        )
    except Exception:  # noqa: BLE001
        logger.warning("Assembly SQL inference failed.", exc_info=True)
        return None
    if usage is not None:
        usage.add(*usage_from_message(resp))
    obj = _parse_object(_extract_text(resp.content))
    sql = obj.get("sql") if obj else None
    return sql.strip() if isinstance(sql, str) and sql.strip() else None


def _safe_remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


async def _infer_spec(
    ctx: DatasetContext, goal: str, usage: UsageTracker | None
) -> dict:
    """One cheap call for the semantic understanding pandas can't infer. Returns
    {} on any failure so the battery falls back to heuristics."""
    user = _SPEC_PROMPT.format(goal=goal)
    dims = _dimension_values_text(ctx)
    if dims:
        user += "\n\n" + dims
    try:
        resp = await build_model(
            max_output_tokens=settings.REPORT_PLAN_MAX_OUTPUT_TOKENS
        ).ainvoke([("system", ctx.schema_text()), ("user", user)])
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
        "scope": _parse_scope(raw.get("scope"), names),
    }


def _parse_scope(raw, names: set[str]) -> dict | None:
    """Validate the optional scope filter: a real column plus a non-empty list of
    values to keep. Value existence is re-checked against the data in the battery,
    so here we only sanity-check the shape."""
    if not isinstance(raw, dict) or raw.get("column") not in names:
        return None
    include = [
        str(v) for v in raw.get("include", []) if isinstance(v, (str, int, float, bool))
    ]
    if not include:
        return None
    return {
        "column": raw["column"],
        "include": include,
        "reason": str(raw.get("reason", "")).strip(),
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
    if analysis.scope_note:
        # The battery already restricted to a sub-population; tell the planner so it
        # frames the report around that group rather than the whole dataset.
        user = f"NOTE: {analysis.scope_note}\n\n" + user
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
