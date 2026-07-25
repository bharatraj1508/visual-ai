"""Deterministic query engine over a dataset's Parquet file.

Two layers of safety for the untrusted SQL the LLM writes in `run_sql`:
  1. The Parquet is loaded into an in-memory DuckDB table named `data`, then
     external access is disabled and the config is locked — so the query cannot
     read or write any file (no read_csv('/etc/passwd'), no COPY ... TO).
  2. A statement guard rejects anything that isn't a single SELECT/WITH.

Small-data assumption: the whole table fits in memory comfortably.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import duckdb
import pandas as pd

# Cap rows returned to the LLM so a `SELECT *` can't blow up the context window.
DEFAULT_MAX_ROWS = 1000

_STARTS_OK = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
_FORBIDDEN = re.compile(
    r"\b(attach|detach|install|load|copy|export|import|pragma|set|call|"
    r"create|insert|update|delete|drop|alter|reset)\b",
    re.IGNORECASE,
)


class QueryError(ValueError):
    """Raised when a query is rejected or fails to execute."""


def load_dataframe(parquet_path: str | Path) -> pd.DataFrame:
    return pd.read_parquet(parquet_path)


def _to_records(df: pd.DataFrame) -> list[dict]:
    """JSON-safe records: NaN -> null, numpy/datetime -> native/ISO."""
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _readonly_connection(parquet_path: str | Path) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(database=":memory:")
    con.execute(
        "CREATE TABLE data AS SELECT * FROM read_parquet(?)",
        [str(parquet_path)],
    )
    # Lock down: no filesystem/network, and no re-enabling it mid-query.
    con.execute("SET enable_external_access=false")
    con.execute("SET lock_configuration=true")
    return con


def _validate_select(sql: str) -> str:
    stripped = sql.strip().rstrip(";").strip()
    if not stripped:
        raise QueryError("Empty query")
    if ";" in stripped:
        raise QueryError("Only a single statement is allowed")
    if not _STARTS_OK.match(stripped):
        raise QueryError("Only SELECT / WITH queries are allowed")
    if _FORBIDDEN.search(stripped):
        raise QueryError("Query contains a forbidden keyword")
    return stripped


def run_sql(
    parquet_path: str | Path, sql: str, max_rows: int = DEFAULT_MAX_ROWS
) -> dict:
    """Run a read-only SELECT against the `data` table.

    Returns {columns, rows, row_count, truncated}. `truncated` is True when the
    result was clipped to `max_rows`.
    """
    safe_sql = _validate_select(sql)
    con = _readonly_connection(parquet_path)
    try:
        wrapped = f"SELECT * FROM ({safe_sql}) AS _sub LIMIT {max_rows + 1}"
        try:
            df = con.execute(wrapped).df()
        except duckdb.Error as exc:
            raise QueryError(str(exc)) from exc
    finally:
        con.close()

    truncated = len(df) > max_rows
    if truncated:
        df = df.head(max_rows)
    return {
        "columns": list(df.columns),
        "rows": _to_records(df),
        "row_count": len(df),
        "truncated": truncated,
    }


def describe(parquet_path: str | Path, columns: list[str] | None = None) -> dict:
    """Summary statistics per column (count/mean/std/min/quartiles/unique/etc.)."""
    df = load_dataframe(parquet_path)
    if columns:
        missing = [c for c in columns if c not in df.columns]
        if missing:
            raise QueryError(f"Unknown column(s): {missing}")
        df = df[columns]
    summary = df.describe(include="all").transpose()
    summary.insert(0, "column", summary.index)
    return {"stats": _to_records(summary)}


def value_counts(
    parquet_path: str | Path, column: str, limit: int = 20
) -> dict:
    """Frequency of each distinct value in a column (nulls included)."""
    df = load_dataframe(parquet_path)
    if column not in df.columns:
        raise QueryError(f"Unknown column: {column}")
    counts = (
        df[column]
        .value_counts(dropna=False)
        .head(limit)
        .rename_axis("value")
        .reset_index(name="count")
    )
    return {"column": column, "counts": _to_records(counts)}


def correlate(
    parquet_path: str | Path,
    columns: list[str] | None = None,
    method: str = "pearson",
) -> dict:
    """Correlation matrix among numeric columns."""
    df = load_dataframe(parquet_path)
    numeric = df.select_dtypes(include="number")
    if columns:
        missing = [c for c in columns if c not in numeric.columns]
        if missing:
            raise QueryError(
                f"Column(s) not numeric or not found: {missing}"
            )
        numeric = numeric[columns]
    if numeric.shape[1] < 2:
        raise QueryError("Need at least two numeric columns to correlate")
    matrix = numeric.corr(method=method).round(4)
    return {
        "method": method,
        "columns": list(matrix.columns),
        "matrix": json.loads(matrix.to_json()),
    }
