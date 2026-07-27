"""Compile a chart request into a neutral, Recharts-friendly spec.

The frontend renders with Recharts, which wants *wide* data (one column per
series) plus a small description of how to draw it. This module owns that
transform so the agent only has to say WHAT to plot — the SQL result, the x
field, the measure(s), and a chart type — never HOW.

The output shape (see `ChartSpec`) is deliberately renderer-agnostic:
  {
    type, render, title, data, xKey, xType,
    series: [{key, name, chartType, yAxis, stackId}],
    seriesField, yKey, xLabel, yLabel
  }
`render` tells the client which Recharts container to reach for; `series`
tells it what to draw inside it.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Optional

import pandas as pd

from app.services.data_access import QueryError

# Semantic chart types the agent may request.
CHART_TYPES = (
    "bar",
    "grouped_bar",
    "stacked_bar",
    "line",
    "multi_line",
    "area",
    "stacked_area",
    "scatter",
    "pie",
    "donut",
    "histogram",
    "dual_axis",
    "radar",
)

# type -> (render container, per-series mark, stacked?)
_RENDER = {
    "bar": ("cartesian", "bar", False),
    "grouped_bar": ("cartesian", "bar", False),
    "stacked_bar": ("cartesian", "bar", True),
    "line": ("cartesian", "line", False),
    "multi_line": ("cartesian", "line", False),
    "area": ("cartesian", "area", False),
    "stacked_area": ("cartesian", "area", True),
    "histogram": ("cartesian", "bar", False),
    "dual_axis": ("cartesian", "bar", False),
    "scatter": ("scatter", "scatter", False),
    "pie": ("pie", "pie", False),
    "donut": ("pie", "pie", False),
    "radar": ("radar", "radar", False),
}

_AGG_SYNONYMS = {"avg": "mean", "average": "mean"}
_VALID_AGG = {"sum", "mean", "count", "min", "max", "median"}
_HIST_BINS = 12


def _normalize_agg(aggregate: Optional[str]) -> Optional[str]:
    if not aggregate:
        return None
    agg = _AGG_SYNONYMS.get(aggregate.lower(), aggregate.lower())
    if agg not in _VALID_AGG:
        raise QueryError(
            f"Unsupported aggregate '{aggregate}'. Use one of {sorted(_VALID_AGG)}."
        )
    return agg


def _records(df: pd.DataFrame) -> list[dict]:
    """JSON-safe records: NaN -> null, numpy/datetime -> native/ISO."""
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _x_type(series: pd.Series) -> str:
    non_null = series.dropna()
    if non_null.empty:
        return "category"
    if pd.api.types.is_numeric_dtype(non_null):
        return "number"
    if pd.api.types.is_datetime64_any_dtype(non_null):
        return "time"
    sample = non_null.head(30)
    parsed = 0
    for v in sample:
        if isinstance(v, (datetime, date)):
            parsed += 1
            continue
        try:
            datetime.fromisoformat(str(v))
            parsed += 1
        except ValueError:
            pass
    return "time" if parsed / len(sample) >= 0.9 else "category"


def _mark_for(chart_type: str) -> str:
    return _RENDER[chart_type][1]


def _histogram(df: pd.DataFrame, x: str, title, x_label) -> dict:
    col = pd.to_numeric(df[x], errors="coerce").dropna()
    if col.empty:
        raise QueryError(
            f"Histogram needs a numeric column, but '{x}' has no numeric values. "
            "For categories, use a bar chart with an aggregate of count instead."
        )
    bins = min(_HIST_BINS, max(1, col.nunique()))
    cut = pd.cut(col, bins=bins)
    counts = cut.value_counts().sort_index()
    data = [
        {"bin": f"{iv.left:.4g}–{iv.right:.4g}", "count": int(n)}
        for iv, n in counts.items()
    ]
    return {
        "type": "histogram",
        "render": "cartesian",
        "title": title,
        "data": data,
        "xKey": "bin",
        "xType": "category",
        "series": [
            {"key": "count", "name": "Count", "chartType": "bar",
             "yAxis": "left", "stackId": None}
        ],
        "seriesField": None,
        "yKey": None,
        "xLabel": x_label or x,
        "yLabel": "Count",
    }


def _pivot_series(
    df: pd.DataFrame, x: str, y: str, series_field: str
) -> tuple[pd.DataFrame, list[str]]:
    """Long (x, series, y) -> wide (one column per distinct series value)."""
    wide = (
        df.pivot_table(index=x, columns=series_field, values=y, aggfunc="first")
        .reset_index()
    )
    wide.columns = [str(c) for c in wide.columns]
    keys = [c for c in wide.columns if c != x]
    return wide, keys


def build_chart_spec(
    chart_type: str,
    rows: list[dict],
    x: str,
    y: Optional[str] = None,
    y2: Optional[str] = None,
    series: Optional[str] = None,
    aggregate: Optional[str] = None,
    title: Optional[str] = None,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    name_key: Optional[str] = None,
) -> dict:
    """Compile query rows + an encoding into a neutral ChartSpec.

    Raises QueryError on an invalid request (missing measure, non-numeric
    histogram, etc.) so the tool can hand a clear message back to the agent.
    """
    if chart_type not in _RENDER:
        raise QueryError(
            f"Unknown chart_type '{chart_type}'. Choose one of {list(CHART_TYPES)}."
        )
    df = pd.DataFrame(rows)
    if df.empty:
        raise QueryError("The query returned no rows to plot.")
    agg = _normalize_agg(aggregate)

    if chart_type == "histogram":
        return _histogram(df, x, title, x_label)

    if not y:
        raise QueryError(f"{chart_type} charts require a `y` field.")

    render, mark, stacked = _RENDER[chart_type]
    stack_id = "stack" if stacked else None

    # Optional aggregation (the agent is nudged to do this in SQL, but we
    # support it here so a stray raw-rows query still renders sensibly).
    if agg and chart_type not in ("scatter",):
        group_cols = [x] + ([series] if series else [])
        measure_cols = [c for c in (y, y2) if c]
        df = (
            df.groupby(group_cols, dropna=False)[measure_cols]
            .agg(agg)
            .reset_index()
        )

    if render == "scatter":
        # `labelKey` names the per-point identity column (e.g. the player name)
        # so the tooltip can say WHICH row a dot is, not just its x/y.
        label_key = name_key if name_key and name_key in df.columns else None
        return {
            "type": chart_type,
            "render": "scatter",
            "title": title,
            "data": _records(df),
            "xKey": x,
            "xType": _x_type(df[x]),
            "series": [],
            "seriesField": series,
            "yKey": y,
            "xLabel": x_label or x,
            "yLabel": y_label or y,
            "labelKey": label_key,
        }

    if render == "pie":
        slice_df = df[[x, y]].copy()
        return {
            "type": chart_type,
            "render": "pie",
            "title": title,
            "data": _records(slice_df),
            "xKey": x,
            "xType": "category",
            "series": [
                {"key": y, "name": y_label or y, "chartType": "pie",
                 "yAxis": "left", "stackId": None}
            ],
            "seriesField": None,
            "yKey": y,
            "xLabel": x_label or x,
            "yLabel": y_label or y,
        }

    # cartesian (bar / line / area families, dual_axis) and radar -----------
    if series:
        wide, keys = _pivot_series(df, x, y, series)
        series_specs = [
            {"key": k, "name": k, "chartType": mark, "yAxis": "left",
             "stackId": stack_id}
            for k in keys
        ]
        data_df = wide
    elif y2:
        cols = [x, y, y2]
        data_df = df[cols].copy()
        if chart_type == "dual_axis":
            series_specs = [
                {"key": y, "name": y_label or y, "chartType": "bar",
                 "yAxis": "left", "stackId": None},
                {"key": y2, "name": y2, "chartType": "line",
                 "yAxis": "right", "stackId": None},
            ]
        else:
            series_specs = [
                {"key": m, "name": m, "chartType": mark, "yAxis": "left",
                 "stackId": stack_id}
                for m in (y, y2)
            ]
    else:
        data_df = df[[x, y]].copy()
        series_specs = [
            {"key": y, "name": y_label or y, "chartType": mark,
             "yAxis": "left", "stackId": stack_id}
        ]

    return {
        "type": chart_type,
        "render": "radar" if chart_type == "radar" else "cartesian",
        "title": title,
        "data": _records(data_df),
        "xKey": x,
        "xType": _x_type(data_df[x]),
        "series": series_specs,
        "seriesField": None,
        "yKey": None,
        "xLabel": x_label or x,
        "yLabel": y_label or y,
    }
