"""CSV ingestion: read → cache as Parquet → profile columns.

Profiling is the crux of the whole product: we distill an arbitrarily large
table into a few hundred tokens (schema + stats + a handful of sample values)
that the LLM can reason over, while the actual data stays in Parquet for
deterministic querying by DuckDB/pandas.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd
from pandas.api import types as pdt

# How many distinct sample values to keep per column for the LLM context.
_MAX_SAMPLES = 5
# object columns with distinct/total below this ratio are treated as categorical.
_CATEGORICAL_RATIO = 0.5


def load_csv(path: str | Path) -> pd.DataFrame:
    """Read a CSV robustly. Small-data assumption: fits comfortably in memory."""
    return pd.read_csv(path, encoding_errors="replace")


def write_parquet(df: pd.DataFrame, path: str | Path) -> None:
    df.to_parquet(path, index=False)


def _semantic_dtype(series: pd.Series) -> str:
    """Map a pandas column to a coarse semantic type the LLM understands."""
    if pdt.is_bool_dtype(series):
        return "boolean"
    if pdt.is_integer_dtype(series):
        return "integer"
    if pdt.is_float_dtype(series):
        return "float"
    if pdt.is_datetime64_any_dtype(series):
        return "datetime"

    non_null = series.dropna()
    if non_null.empty:
        return "text"

    # object/string column: sniff for dates, else categorical vs free text.
    if _looks_like_datetime(non_null):
        return "datetime"

    distinct_ratio = non_null.nunique() / len(non_null)
    return "categorical" if distinct_ratio <= _CATEGORICAL_RATIO else "text"


def _looks_like_datetime(non_null: pd.Series) -> bool:
    sample = non_null.astype(str).head(50)
    # Guard against false positives like month names ("Jan"/"Feb"), which
    # pandas happily parses into year-1900 dates. Real dates carry digits.
    if sample.str.contains(r"\d").mean() < 0.9:
        return False
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            parsed = pd.to_datetime(sample, errors="coerce")
        except (ValueError, TypeError):
            return False
    return parsed.notna().mean() >= 0.9


def _min_max(series: pd.Series, dtype: str) -> tuple[str | None, str | None]:
    if dtype not in {"integer", "float", "datetime"}:
        return None, None
    non_null = series.dropna()
    if non_null.empty:
        return None, None
    if dtype == "datetime" and not pdt.is_datetime64_any_dtype(non_null):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            non_null = pd.to_datetime(non_null, errors="coerce").dropna()
        if non_null.empty:
            return None, None
    return str(non_null.min())[:255], str(non_null.max())[:255]


def profile_dataframe(df: pd.DataFrame) -> list[dict]:
    """Return one profile dict per column, aligned to the DatasetColumn model."""
    profiles: list[dict] = []
    for position, name in enumerate(df.columns):
        series = df[name]
        dtype = _semantic_dtype(series)
        min_value, max_value = _min_max(series, dtype)
        samples = [
            str(v)[:255] for v in series.dropna().unique()[:_MAX_SAMPLES]
        ]
        profiles.append(
            {
                "name": str(name),
                "dtype": dtype,
                "position": position,
                "null_count": int(series.isna().sum()),
                "distinct_count": int(series.nunique(dropna=True)),
                "min_value": min_value,
                "max_value": max_value,
                "sample_values": samples,
            }
        )
    return profiles


def ingest_csv(csv_path: str | Path, parquet_out: str | Path) -> tuple[int, int, list[dict]]:
    """Blocking ingestion pipeline. Returns (row_count, col_count, column_profiles).

    Run this via asyncio.to_thread from the async endpoint so pandas doesn't
    block the event loop.
    """
    df = load_csv(csv_path)
    write_parquet(df, parquet_out)
    profiles = profile_dataframe(df)
    return len(df), df.shape[1], profiles
