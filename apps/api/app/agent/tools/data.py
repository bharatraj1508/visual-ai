"""Safe data tools exposed to the LangGraph ReAct agent.

Each tool closes over a DatasetContext (which Parquet file to query) and returns
a JSON string — the form the agent consumes as tool output. The heavy lifting
lives in services.data_access; these are thin, LLM-facing wrappers.
"""
from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.agent.context import DatasetContext
from app.services import data_access
from app.services.data_access import QueryError


def _dump(result: dict) -> str:
    return json.dumps(result, default=str)


def _error(exc: Exception) -> str:
    return json.dumps({"error": str(exc)})


class QueryDataArgs(BaseModel):
    sql: str = Field(
        description=(
            "A single read-only DuckDB SQL SELECT query against the table "
            "named `data`. No semicolons, no DDL. Example: "
            "SELECT student_name, AVG(attendance_pct) AS avg_pct "
            "FROM data GROUP BY student_name ORDER BY avg_pct DESC"
        )
    )


class DescribeArgs(BaseModel):
    columns: list[str] | None = Field(
        default=None,
        description="Optional subset of columns; omit for all columns.",
    )


class ValueCountsArgs(BaseModel):
    column: str = Field(description="Column to count distinct values of.")
    limit: int = Field(default=20, description="Max distinct values to return.")


class CorrelateArgs(BaseModel):
    columns: list[str] | None = Field(
        default=None,
        description="Optional subset of numeric columns; omit for all numeric.",
    )
    method: str = Field(
        default="pearson",
        description="Correlation method: pearson, spearman, or kendall.",
    )


def build_data_tools(ctx: DatasetContext) -> list[StructuredTool]:
    path = ctx.parquet_path

    def query_data(sql: str) -> str:
        try:
            return _dump(data_access.run_sql(path, sql))
        except QueryError as exc:
            return _error(exc)

    def describe_data(columns: list[str] | None = None) -> str:
        try:
            return _dump(data_access.describe(path, columns))
        except QueryError as exc:
            return _error(exc)

    def value_counts(column: str, limit: int = 20) -> str:
        try:
            return _dump(data_access.value_counts(path, column, limit))
        except QueryError as exc:
            return _error(exc)

    def correlate(columns: list[str] | None = None, method: str = "pearson") -> str:
        try:
            return _dump(data_access.correlate(path, columns, method))
        except QueryError as exc:
            return _error(exc)

    return [
        StructuredTool.from_function(
            func=query_data,
            name="query_data",
            description=(
                "Run a read-only SQL SELECT over the dataset (DuckDB, table "
                "`data`). Use this for filtering, grouping, aggregating, and "
                "sorting. Returns up to 1000 rows as JSON."
            ),
            args_schema=QueryDataArgs,
        ),
        StructuredTool.from_function(
            func=describe_data,
            name="describe_data",
            description=(
                "Get summary statistics (count, mean, std, min/max, quartiles, "
                "unique) for the dataset's columns."
            ),
            args_schema=DescribeArgs,
        ),
        StructuredTool.from_function(
            func=value_counts,
            name="value_counts",
            description=(
                "Get the frequency of each distinct value in one column."
            ),
            args_schema=ValueCountsArgs,
        ),
        StructuredTool.from_function(
            func=correlate,
            name="correlate",
            description=(
                "Compute the correlation matrix among numeric columns."
            ),
            args_schema=CorrelateArgs,
        ),
    ]
