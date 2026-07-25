"""create_chart tool — the agent describes WHAT to plot (a SQL query + encoding);
we run the query deterministically and compile a validated Vega-Lite spec.

Crucially, the data never round-trips through the LLM: the tool returns only a
small confirmation to the model and stashes the full spec (with embedded rows)
in a run-scoped collector that the endpoint persists and streams to the client.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Literal, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.agent.context import DatasetContext
from app.services import data_access
from app.services.data_access import QueryError

ChartType = Literal["bar", "line", "area", "scatter", "pie", "histogram"]

# Rows embedded in a chart spec; higher than the text row-cap since charts plot
# points rather than feeding them back to the LLM.
_CHART_MAX_ROWS = 5000

_VEGA_SCHEMA = "https://vega.github.io/schema/vega-lite/v5.json"
_MARK_BY_TYPE = {"bar": "bar", "line": "line", "area": "area", "scatter": "point"}
_AGG_SYNONYMS = {"avg": "mean", "average": "mean"}
_VALID_AGG = {"sum", "mean", "count", "min", "max", "median"}


def _infer_type(rows: list[dict], field: str) -> str:
    values = [r[field] for r in rows if r.get(field) is not None]
    if not values:
        return "nominal"
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        return "quantitative"
    if _mostly_temporal(values):
        return "temporal"
    return "nominal"


def _mostly_temporal(values: list) -> bool:
    parsed = 0
    for v in values[:50]:
        if isinstance(v, (datetime, date)):
            parsed += 1
            continue
        try:
            datetime.fromisoformat(str(v))
            parsed += 1
        except ValueError:
            pass
    return parsed / min(len(values), 50) >= 0.9


def _normalize_agg(aggregate: Optional[str]) -> Optional[str]:
    if not aggregate:
        return None
    agg = _AGG_SYNONYMS.get(aggregate.lower(), aggregate.lower())
    if agg not in _VALID_AGG:
        raise QueryError(
            f"Unsupported aggregate '{aggregate}'. Use one of {sorted(_VALID_AGG)}."
        )
    return agg


def build_vega_spec(
    chart_type: str,
    rows: list[dict],
    x: str,
    y: Optional[str] = None,
    series: Optional[str] = None,
    aggregate: Optional[str] = None,
    title: Optional[str] = None,
) -> dict:
    """Compile typed params into a valid Vega-Lite v5 spec with embedded data."""
    agg = _normalize_agg(aggregate)
    spec: dict = {"$schema": _VEGA_SCHEMA, "data": {"values": rows}}
    if title:
        spec["title"] = title

    if chart_type == "histogram":
        spec["mark"] = "bar"
        x_type = _infer_type(rows, x)
        spec["encoding"] = {
            "x": {"field": x, "bin": True,
                  "type": x_type if x_type == "quantitative" else "quantitative"},
            "y": {"aggregate": "count", "type": "quantitative"},
        }
    elif chart_type == "pie":
        if not y:
            raise QueryError("Pie charts require a `y` field for the slice size.")
        theta = {"field": y, "type": "quantitative"}
        if agg:
            theta["aggregate"] = agg
        spec["mark"] = "arc"
        spec["encoding"] = {
            "theta": theta,
            "color": {"field": x, "type": _infer_type(rows, x)},
        }
    else:
        if not y:
            raise QueryError(f"{chart_type} charts require a `y` field.")
        y_enc: dict = {"field": y, "type": _infer_type(rows, y)}
        if agg:
            y_enc["aggregate"] = agg
        encoding = {
            "x": {"field": x, "type": _infer_type(rows, x)},
            "y": y_enc,
        }
        if series:
            encoding["color"] = {"field": series, "type": _infer_type(rows, series)}
        spec["mark"] = _MARK_BY_TYPE[chart_type]
        spec["encoding"] = encoding

    return spec


class CreateChartArgs(BaseModel):
    chart_type: ChartType = Field(description="The kind of chart to render.")
    sql: str = Field(
        description=(
            "A read-only SELECT over table `data` producing exactly the rows to "
            "plot. Aggregate here rather than plotting raw rows when possible."
        )
    )
    x: str = Field(description="Column (from the query result) for the x axis / category / pie color.")
    y: Optional[str] = Field(
        default=None,
        description="Column for the y axis / pie slice size. Omit only for histograms.",
    )
    series: Optional[str] = Field(
        default=None, description="Optional column to split into colored series."
    )
    aggregate: Optional[str] = Field(
        default=None,
        description="Optional aggregate on y: sum, mean, count, min, max, median.",
    )
    title: Optional[str] = Field(default=None, description="Chart title.")


def build_chart_tool(ctx: DatasetContext, collector: list[dict]) -> StructuredTool:
    def create_chart(
        chart_type: str,
        sql: str,
        x: str,
        y: Optional[str] = None,
        series: Optional[str] = None,
        aggregate: Optional[str] = None,
        title: Optional[str] = None,
    ) -> str:
        try:
            result = data_access.run_sql(ctx.parquet_path, sql, max_rows=_CHART_MAX_ROWS)
        except QueryError as exc:
            return json.dumps({"error": str(exc)})

        rows, cols = result["rows"], result["columns"]
        if not rows:
            return json.dumps({"error": "The query returned no rows to plot."})
        for field in (x, y, series):
            if field and field not in cols:
                return json.dumps(
                    {"error": f"'{field}' is not a column in the query result: {cols}"}
                )
        try:
            spec = build_vega_spec(chart_type, rows, x, y, series, aggregate, title)
        except QueryError as exc:
            return json.dumps({"error": str(exc)})

        chart_id = f"chart_{len(collector) + 1}"
        collector.append(
            {"id": chart_id, "kind": "chart", "title": title, "spec": spec}
        )
        # Compact confirmation for the LLM — NOT the full spec.
        return json.dumps(
            {
                "status": "created",
                "chart_id": chart_id,
                "chart_type": chart_type,
                "points": len(rows),
                "columns": cols,
            }
        )

    return StructuredTool.from_function(
        func=create_chart,
        name="create_chart",
        description=(
            "Create a chart from a SQL query over table `data`. Returns a "
            "confirmation; the rendered chart is delivered to the user "
            "automatically. Supports bar, line, area, scatter, pie, histogram."
        ),
        args_schema=CreateChartArgs,
    )
