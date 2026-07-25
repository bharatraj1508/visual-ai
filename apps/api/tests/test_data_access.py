"""Tests for the DuckDB/pandas data-access engine and the agent data tools.

These exercise real Parquet files and the real DuckDB engine (no mocks) — the
engine IS the thing under test, so faking it would test nothing.
"""
import json

import pandas as pd
import pytest

from app.agent.context import DatasetContext
from app.agent.tools.data import build_data_tools
from app.services import data_access
from app.services.data_access import QueryError


@pytest.fixture
def parquet(tmp_path):
    """A small attendance-like dataset written to Parquet."""
    df = pd.DataFrame(
        {
            "student": ["Aisha", "Ben", "Aisha", "Ben", "Carlos"],
            "month": ["Jan", "Jan", "Feb", "Feb", "Feb"],
            "present": [18, 12, 20, 15, 10],
            "total": [20, 20, 20, 20, 20],
            "pct": [90.0, 60.0, 100.0, 75.0, 50.0],
        }
    )
    path = tmp_path / "data.parquet"
    df.to_parquet(path, index=False)
    return str(path)


# --- run_sql -----------------------------------------------------------------

def test_run_sql_aggregates(parquet):
    result = data_access.run_sql(
        parquet,
        "SELECT student, AVG(pct) AS avg_pct FROM data "
        "GROUP BY student ORDER BY avg_pct DESC",
    )
    assert result["columns"] == ["student", "avg_pct"]
    assert result["rows"][0]["student"] == "Aisha"
    assert result["rows"][0]["avg_pct"] == pytest.approx(95.0)
    assert result["truncated"] is False


def test_run_sql_row_cap_and_truncation(parquet):
    result = data_access.run_sql(parquet, "SELECT * FROM data", max_rows=2)
    assert result["row_count"] == 2
    assert result["truncated"] is True


def test_run_sql_with_cte(parquet):
    result = data_access.run_sql(
        parquet,
        "WITH t AS (SELECT student, SUM(present) AS p FROM data GROUP BY student) "
        "SELECT * FROM t ORDER BY p DESC",
    )
    assert result["rows"][0]["p"] == 38  # Aisha 18+20


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE data",
        "CREATE TABLE x AS SELECT 1",
        "COPY (SELECT 1) TO '/tmp/x.csv'",
        "INSTALL httpfs",
        "SELECT 1; DROP TABLE data",
        "PRAGMA database_list",
    ],
)
def test_run_sql_rejects_non_select(parquet, sql):
    with pytest.raises(QueryError):
        data_access.run_sql(parquet, sql)


def test_run_sql_cannot_read_external_files(parquet, tmp_path):
    secret = tmp_path / "secret.csv"
    secret.write_text("a,b\n1,2\n")
    # Even though it starts with SELECT, external file access is disabled.
    with pytest.raises(QueryError):
        data_access.run_sql(parquet, f"SELECT * FROM read_csv('{secret}')")


# --- describe / value_counts / correlate ------------------------------------

def test_describe_all_columns(parquet):
    result = data_access.describe(parquet)
    cols = {row["column"] for row in result["stats"]}
    assert {"student", "present", "pct"} <= cols


def test_value_counts(parquet):
    result = data_access.value_counts(parquet, "student")
    counts = {r["value"]: r["count"] for r in result["counts"]}
    assert counts["Aisha"] == 2 and counts["Carlos"] == 1


def test_value_counts_unknown_column(parquet):
    with pytest.raises(QueryError):
        data_access.value_counts(parquet, "nope")


def test_correlate(parquet):
    result = data_access.correlate(parquet, columns=["present", "pct"])
    assert result["matrix"]["present"]["pct"] == pytest.approx(
        result["matrix"]["pct"]["present"]
    )


def test_correlate_needs_two_numeric(parquet):
    with pytest.raises(QueryError):
        data_access.correlate(parquet, columns=["present"])


# --- tool wrappers -----------------------------------------------------------

def _ctx(parquet):
    return DatasetContext(
        dataset_id=None,
        parquet_path=parquet,
        filename="attendance.csv",
        row_count=5,
        columns=[{"name": "pct", "dtype": "float", "distinct_count": 5,
                  "null_count": 0, "min_value": "50.0", "max_value": "100.0",
                  "sample_values": ["90.0"]}],
    )


def test_tools_return_json_strings(parquet):
    tools = {t.name: t for t in build_data_tools(_ctx(parquet))}
    assert set(tools) == {"query_data", "describe_data", "value_counts", "correlate"}
    out = tools["query_data"].invoke({"sql": "SELECT COUNT(*) AS n FROM data"})
    assert json.loads(out)["rows"][0]["n"] == 5


def test_tool_returns_error_json_not_raise(parquet):
    tools = {t.name: t for t in build_data_tools(_ctx(parquet))}
    out = tools["query_data"].invoke({"sql": "DROP TABLE data"})
    assert "error" in json.loads(out)


def test_schema_text_is_compact(parquet):
    text = _ctx(parquet).schema_text()
    assert "table is named `data`" in text
    assert "pct (float)" in text
