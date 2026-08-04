"""CSV ingestion: read → cache as Parquet → profile columns.

Profiling is the crux of the whole product: we distill an arbitrarily large
table into a few hundred tokens (schema + stats + a handful of sample values)
that the LLM can reason over, while the actual data stays in Parquet for
deterministic querying by DuckDB/pandas.
"""
from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
from pandas.api import types as pdt

from app.core.config import settings
from app.core.logging import logger

# How many distinct sample values to keep per column for the LLM context.
_MAX_SAMPLES = 5
# object columns with distinct/total below this ratio are treated as categorical.
_CATEGORICAL_RATIO = 0.5
# Files whose columns overlap at least this much (Jaccard) are treated as the SAME
# table split into parts and stacked; less overlap → they stay separate tables.
_STACK_OVERLAP = 0.6


class TooManyTablesError(Exception):
    """The files form more distinct tables than the LLM pipeline can reason
    over. The message is user-facing."""


# A live-progress sink: progress(key, state, label, detail). `key` groups
# updates to one UI line ("clean" advances through tables); `state` is "active"
# or "done". Ingestion runs in a worker thread, so implementations must be
# thread-safe (the SSE endpoint hands off via loop.call_soon_threadsafe).
Progress = Callable[[str, str, str, Optional[str]], None]


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


def _table_name(filename: str, taken: set[str]) -> str:
    """A safe, unique SQL identifier derived from a filename ('Sales Q1.csv' →
    'sales_q1'), so each table can be referenced by name in DuckDB. Folder parts
    (ZIP members keep their relative path) are folded in — '2024/players.csv' →
    't_2024_players' — so same-named files from different folders stay apart."""
    path = Path(filename)
    base = " ".join((*path.parts[:-1], path.stem))
    stem = re.sub(r"[^a-z0-9]+", "_", base.lower()).strip("_")[:63] or "table"
    if stem[0].isdigit():
        stem = f"t_{stem}"
    name, i = stem, 2
    while name in taken:
        name, i = f"{stem}_{i}", i + 1
    taken.add(name)
    return name


def _cluster_by_schema(
    items: list[tuple[str, pd.DataFrame]],
) -> list[list[tuple[str, pd.DataFrame]]]:
    """Group files that are the SAME table split into parts (columns overlap ≥
    _STACK_OVERLAP). Each group becomes one stacked table; distinct groups stay
    separate tables. Never merges unrelated files."""
    clusters: list[dict] = []
    for name, df in items:
        cols = set(df.columns)
        for cl in clusters:
            union = cols | cl["cols"]
            if union and len(cols & cl["cols"]) / len(union) >= _STACK_OVERLAP:
                cl["items"].append((name, df))
                cl["cols"] |= cols
                break
        else:
            clusters.append({"cols": set(cols), "items": [(name, df)]})
    return [cl["items"] for cl in clusters]


def build_tables(items: list[tuple[str, pd.DataFrame]]) -> list[dict]:
    """Turn uploaded CSVs into one or more dataset TABLES — never rejecting.

    Files sharing a schema are stacked into one table (a dataset split into
    parts); differently-shaped files each become their own table, to be queried
    together downstream. Returns ``[{name, filename, df}]``.
    """
    taken: set[str] = set()
    tables: list[dict] = []
    for group in _cluster_by_schema(items):
        dfs = [df for _, df in group]
        df = dfs[0] if len(dfs) == 1 else pd.concat(dfs, ignore_index=True)
        first = group[0][0]
        filename = first if len(group) == 1 else f"{first} +{len(group) - 1} more"
        tables.append({"name": _table_name(first, taken), "filename": filename, "df": df})
    return tables


def ingest_tables(
    named_paths: list[tuple[str, str | Path]],
    dataset_dir: str | Path,
    progress: Progress | None = None,
) -> tuple[list[dict], list[dict], bool]:
    """Blocking pipeline for one or more CSVs that form a dataset.

    Clusters the files into tables (see ``build_tables``), writes each as its own
    Parquet, applies the safe cleaning pass, and profiles the cleaned result.
    Returns ``(tables_info, changes, preprocessed)`` where each table_info is
    ``{name, filename, parquet_path, row_count, col_count, columns}``. A single
    table is written to ``data.parquet`` — the legacy layout — so single-CSV
    datasets are byte-for-byte unchanged. Run via asyncio.to_thread.

    ``progress`` (optional) receives live step updates for the upload UI.
    """
    # Lazy import keeps the module dependency one-way (preprocessing imports
    # ingestion at module load, not the reverse).
    from app.services import preprocessing

    def emit(key: str, state: str, label: str, detail: str | None = None) -> None:
        if progress is not None:
            progress(key, state, label, detail)

    n = len(named_paths)
    emit("read", "active", "Reading your files")
    items = [(name, load_csv(path)) for name, path in named_paths]
    emit("read", "done", "Reading your files",
         f"{n} file{'s' if n != 1 else ''} read")

    emit("combine", "active", "Detecting & combining tables")
    tables = build_tables(items)
    # Every table's schema is pasted into the LLM prompts, so the DISTINCT-table
    # count after clustering — not the raw file count — must stay bounded.
    if len(tables) > settings.MAX_DATASET_TABLES:
        raise TooManyTablesError(
            f"These files form {len(tables)} distinct tables; the limit is "
            f"{settings.MAX_DATASET_TABLES}. Files with matching columns are "
            "combined automatically — this upload has too many different schemas."
        )
    single = len(tables) == 1
    tcount = len(tables)
    emit(
        "combine", "done", "Detecting & combining tables",
        "single table"
        if single
        else f"{n} files grouped into {tcount} tables",
    )
    dataset_dir = Path(dataset_dir)
    out: list[dict] = []
    changes: list[dict] = []
    preprocessed = True
    emit("clean", "active", "Cleaning & profiling your data")
    for i, t in enumerate(tables):
        if not single:
            emit(
                "clean", "active", "Cleaning & profiling your data",
                f"table {i + 1}/{tcount}: {t['name']}",
            )
        path = dataset_dir / ("data.parquet" if single else f"table__{i}__{t['name']}.parquet")
        write_parquet(t["df"], path)
        try:
            rows, cols, profiles, chg = preprocessing.apply_cleaning(str(path))
            changes.extend(chg)
        except Exception:  # noqa: BLE001 — cleaning is best-effort; keep the raw table
            logger.warning("Cleaning failed for table %s; keeping raw.", t["name"], exc_info=True)
            rows, cols, profiles = len(t["df"]), t["df"].shape[1], profile_dataframe(t["df"])
            preprocessed = False
        out.append({
            "name": t["name"],
            "filename": t["filename"],
            "parquet_path": str(path),
            "row_count": rows,
            "col_count": cols,
            "columns": profiles,
        })
    total_rows = sum(t["row_count"] for t in out)
    fixes = len(changes)
    emit(
        "clean", "done", "Cleaning & profiling your data",
        f"{total_rows:,} rows"
        + (f" · {fixes} fix{'es' if fixes != 1 else ''} found" if fixes else " · looks clean"),
    )
    if not single:
        logger.info("Ingested %d tables for dataset dir %s", len(out), dataset_dir)
    return out, changes, preprocessed
