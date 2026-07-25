"""Tests for Vega-Lite spec compilation and the create_chart tool (no LLM)."""
import json

import pandas as pd
import pytest

from app.agent.context import DatasetContext
from app.agent.tools.chart import build_chart_tool, build_vega_spec
from app.services.data_access import QueryError


def test_bar_spec():
    rows = [{"student": "A", "avg": 90.0}, {"student": "B", "avg": 60.0}]
    spec = build_vega_spec("bar", rows, x="student", y="avg", title="Averages")
    assert spec["mark"] == "bar"
    assert spec["encoding"]["x"] == {"field": "student", "type": "nominal"}
    assert spec["encoding"]["y"]["type"] == "quantitative"
    assert spec["title"] == "Averages"
    assert spec["data"]["values"] == rows


def test_histogram_spec_bins_and_counts():
    rows = [{"score": v} for v in (10, 20, 30, 40)]
    spec = build_vega_spec("histogram", rows, x="score")
    assert spec["mark"] == "bar"
    assert spec["encoding"]["x"]["bin"] is True
    assert spec["encoding"]["y"]["aggregate"] == "count"


def test_pie_spec():
    rows = [{"grade": "A", "n": 3}, {"grade": "B", "n": 5}]
    spec = build_vega_spec("pie", rows, x="grade", y="n", aggregate="sum")
    assert spec["mark"] == "arc"
    assert spec["encoding"]["theta"] == {
        "field": "n", "type": "quantitative", "aggregate": "sum"
    }
    assert spec["encoding"]["color"]["field"] == "grade"


def test_scatter_with_series_gets_color():
    rows = [{"x": 1.0, "y": 2.0, "grp": "a"}]
    spec = build_vega_spec("scatter", rows, x="x", y="y", series="grp")
    assert spec["mark"] == "point"
    assert spec["encoding"]["color"]["field"] == "grp"


def test_temporal_type_inference():
    rows = [{"d": "2024-01-01", "v": 1.0}, {"d": "2024-02-01", "v": 2.0}]
    spec = build_vega_spec("line", rows, x="d", y="v")
    assert spec["encoding"]["x"]["type"] == "temporal"


def test_aggregate_synonym_normalized():
    rows = [{"a": "x", "b": 1.0}]
    spec = build_vega_spec("bar", rows, x="a", y="b", aggregate="avg")
    assert spec["encoding"]["y"]["aggregate"] == "mean"


def test_pie_requires_y():
    with pytest.raises(QueryError):
        build_vega_spec("pie", [{"a": "x"}], x="a")


def test_invalid_aggregate_rejected():
    with pytest.raises(QueryError):
        build_vega_spec("bar", [{"a": "x", "b": 1}], x="a", y="b", aggregate="bogus")


# --- create_chart tool -------------------------------------------------------

@pytest.fixture
def parquet(tmp_path):
    df = pd.DataFrame(
        {"student": ["A", "B", "A"], "pct": [90.0, 60.0, 80.0]}
    )
    path = tmp_path / "data.parquet"
    df.to_parquet(path, index=False)
    return str(path)


def _ctx(parquet):
    return DatasetContext(
        dataset_id=None, parquet_path=parquet, filename="f.csv",
        row_count=3, columns=[],
    )


def test_create_chart_collects_spec_and_returns_compact(parquet):
    collector = []
    tool = build_chart_tool(_ctx(parquet), collector)
    out = json.loads(
        tool.invoke(
            {
                "chart_type": "bar",
                "sql": "SELECT student, AVG(pct) AS avg_pct FROM data GROUP BY student",
                "x": "student",
                "y": "avg_pct",
                "title": "Avg pct",
            }
        )
    )
    # Compact confirmation to the LLM — no data rows leaked back.
    assert out["status"] == "created"
    assert out["chart_id"] == "chart_1"
    assert "rows" not in out
    # Full spec captured out-of-band for the client.
    assert len(collector) == 1
    assert collector[0]["spec"]["mark"] == "bar"
    assert collector[0]["spec"]["data"]["values"]  # data embedded here


def test_create_chart_unknown_column_errors(parquet):
    collector = []
    tool = build_chart_tool(_ctx(parquet), collector)
    out = json.loads(
        tool.invoke(
            {"chart_type": "bar", "sql": "SELECT student FROM data",
             "x": "student", "y": "nonexistent"}
        )
    )
    assert "error" in out
    assert collector == []
