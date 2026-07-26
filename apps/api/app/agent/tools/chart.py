"""create_chart tool — the agent describes WHAT to plot (a SQL query + encoding);
we run the query deterministically and compile a neutral chart spec that the
frontend renders with Recharts.

Crucially, the data never round-trips through the LLM: the tool returns only a
small confirmation to the model and stashes the full spec (with embedded rows)
in a run-scoped collector that the endpoint persists and streams to the client.
"""
from __future__ import annotations

import json
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.agent.context import DatasetContext
from app.agent.tools.chart_spec import build_chart_spec
from app.services import data_access
from app.services.data_access import QueryError

# Rows embedded in a chart spec; higher than the text row-cap since charts plot
# points rather than feeding them back to the LLM.
_CHART_MAX_ROWS = 5000


class CreateChartArgs(BaseModel):
    chart_type: str = Field(
        description=(
            "Chart to render. One of: bar, grouped_bar, stacked_bar, line, "
            "multi_line, area, stacked_area, scatter, pie, donut, histogram, "
            "dual_axis, radar. Pick the type that best reveals the finding."
        )
    )
    sql: str = Field(
        description=(
            "A read-only SELECT over table `data` producing exactly the rows to "
            "plot. Aggregate here rather than plotting raw rows when possible."
        )
    )
    x: str = Field(
        description="Column for the x axis / category / pie slice label / histogram value."
    )
    y: Optional[str] = Field(
        default=None,
        description="Primary measure column. Omit only for histograms.",
    )
    y2: Optional[str] = Field(
        default=None,
        description=(
            "Optional second measure. For dual_axis it is drawn as a line on a "
            "right-hand axis; for grouped/stacked charts it is a second series."
        ),
    )
    series: Optional[str] = Field(
        default=None,
        description=(
            "Optional column to split into multiple colored series (e.g. year, "
            "category). The rows are pivoted wide automatically."
        ),
    )
    aggregate: Optional[str] = Field(
        default=None,
        description="Optional aggregate on the measure(s): sum, mean, count, min, max, median.",
    )
    title: Optional[str] = Field(default=None, description="Chart title.")
    x_label: Optional[str] = Field(default=None, description="Optional x-axis label.")
    y_label: Optional[str] = Field(default=None, description="Optional y-axis label.")


def build_chart_tool(ctx: DatasetContext, collector: list[dict]) -> StructuredTool:
    def create_chart(
        chart_type: str,
        sql: str,
        x: str,
        y: Optional[str] = None,
        y2: Optional[str] = None,
        series: Optional[str] = None,
        aggregate: Optional[str] = None,
        title: Optional[str] = None,
        x_label: Optional[str] = None,
        y_label: Optional[str] = None,
    ) -> str:
        try:
            result = data_access.run_sql(ctx.parquet_path, sql, max_rows=_CHART_MAX_ROWS)
        except QueryError as exc:
            return json.dumps({"error": str(exc)})

        rows, cols = result["rows"], result["columns"]
        if not rows:
            return json.dumps({"error": "The query returned no rows to plot."})
        for field in (x, y, y2, series):
            if field and field not in cols:
                return json.dumps(
                    {"error": f"'{field}' is not a column in the query result: {cols}"}
                )
        try:
            spec = build_chart_spec(
                chart_type, rows, x, y, y2, series, aggregate, title, x_label, y_label
            )
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
                "points": len(spec["data"]),
                "series": [s["key"] for s in spec["series"]] or [spec.get("yKey")],
            }
        )

    return StructuredTool.from_function(
        func=create_chart,
        name="create_chart",
        description=(
            "Create a chart from a SQL query over table `data`. Returns a "
            "confirmation; the rendered chart is delivered to the user "
            "automatically. Chart types: bar, grouped_bar, stacked_bar, line, "
            "multi_line, area, stacked_area, scatter, pie, donut, histogram, "
            "dual_axis, radar. Prefer the type that best backs up the finding, "
            "and vary chart types across a report."
        ),
        args_schema=CreateChartArgs,
    )
