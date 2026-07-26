"""Tests for neutral chart-spec compilation and the create_chart tool (no LLM)."""
import json

import pandas as pd
import pytest

from app.agent.context import DatasetContext
from app.agent.tools.chart import build_chart_tool
from app.agent.tools.chart_spec import build_chart_spec
from app.services.data_access import QueryError


def test_bar_spec():
    rows = [{"student": "A", "avg": 90.0}, {"student": "B", "avg": 60.0}]
    spec = build_chart_spec("bar", rows, x="student", y="avg", title="Averages")
    assert spec["render"] == "cartesian"
    assert spec["xKey"] == "student"
    assert spec["xType"] == "category"
    assert spec["series"] == [
        {"key": "avg", "name": "avg", "chartType": "bar", "yAxis": "left",
         "stackId": None}
    ]
    assert spec["title"] == "Averages"
    assert spec["data"] == rows


def test_histogram_bins_and_counts():
    rows = [{"score": v} for v in range(0, 100, 5)]
    spec = build_chart_spec("histogram", rows, x="score")
    assert spec["type"] == "histogram"
    assert spec["xKey"] == "bin"
    assert spec["series"][0]["key"] == "count"
    # Every point is a {bin, count} pair and counts sum to the input size.
    assert sum(row["count"] for row in spec["data"]) == len(rows)


def test_histogram_rejects_non_numeric():
    with pytest.raises(QueryError):
        build_chart_spec("histogram", [{"grade": "A"}, {"grade": "B"}], x="grade")


def test_pie_spec():
    rows = [{"grade": "A", "n": 3}, {"grade": "B", "n": 5}]
    spec = build_chart_spec("pie", rows, x="grade", y="n")
    assert spec["render"] == "pie"
    assert spec["xKey"] == "grade"
    assert spec["series"][0]["key"] == "n"
    assert spec["data"] == rows


def test_scatter_carries_series_field():
    rows = [{"x": 1.0, "y": 2.0, "grp": "a"}, {"x": 3.0, "y": 4.0, "grp": "b"}]
    spec = build_chart_spec("scatter", rows, x="x", y="y", series="grp")
    assert spec["render"] == "scatter"
    assert spec["seriesField"] == "grp"
    assert spec["yKey"] == "y"


def test_grouped_bar_pivots_series_wide():
    rows = [
        {"region": "N", "year": "2023", "sales": 10},
        {"region": "N", "year": "2024", "sales": 20},
        {"region": "S", "year": "2023", "sales": 5},
        {"region": "S", "year": "2024", "sales": 8},
    ]
    spec = build_chart_spec("grouped_bar", rows, x="region", y="sales", series="year")
    keys = {s["key"] for s in spec["series"]}
    assert keys == {"2023", "2024"}
    assert all(s["stackId"] is None for s in spec["series"])
    north = next(r for r in spec["data"] if r["region"] == "N")
    assert north["2023"] == 10 and north["2024"] == 20


def test_stacked_bar_sets_stack_id():
    rows = [
        {"region": "N", "year": "2023", "sales": 10},
        {"region": "N", "year": "2024", "sales": 20},
    ]
    spec = build_chart_spec("stacked_bar", rows, x="region", y="sales", series="year")
    assert all(s["stackId"] == "stack" for s in spec["series"])


def test_dual_axis_splits_axes_and_marks():
    rows = [{"month": "Jan", "revenue": 100.0, "margin": 0.2}]
    spec = build_chart_spec("dual_axis", rows, x="month", y="revenue", y2="margin")
    by_key = {s["key"]: s for s in spec["series"]}
    assert by_key["revenue"]["chartType"] == "bar"
    assert by_key["revenue"]["yAxis"] == "left"
    assert by_key["margin"]["chartType"] == "line"
    assert by_key["margin"]["yAxis"] == "right"


def test_temporal_x_type_inference():
    rows = [{"d": "2024-01-01", "v": 1.0}, {"d": "2024-02-01", "v": 2.0}]
    spec = build_chart_spec("line", rows, x="d", y="v")
    assert spec["xType"] == "time"


def test_aggregate_synonym_normalized():
    rows = [{"a": "x", "b": 1.0}, {"a": "x", "b": 3.0}]
    spec = build_chart_spec("bar", rows, x="a", y="b", aggregate="avg")
    assert spec["data"] == [{"a": "x", "b": 2.0}]


def test_line_requires_y():
    with pytest.raises(QueryError):
        build_chart_spec("line", [{"a": "x"}], x="a")


def test_invalid_aggregate_rejected():
    with pytest.raises(QueryError):
        build_chart_spec("bar", [{"a": "x", "b": 1}], x="a", y="b", aggregate="bogus")


def test_unknown_chart_type_rejected():
    with pytest.raises(QueryError):
        build_chart_spec("bogus", [{"a": "x", "b": 1}], x="a", y="b")


# --- create_chart tool -------------------------------------------------------

@pytest.fixture
def parquet(tmp_path):
    df = pd.DataFrame({"student": ["A", "B", "A"], "pct": [90.0, 60.0, 80.0]})
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
    assert "data" not in out
    # Full spec captured out-of-band for the client.
    assert len(collector) == 1
    assert collector[0]["spec"]["render"] == "cartesian"
    assert collector[0]["spec"]["data"]  # data embedded here


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
