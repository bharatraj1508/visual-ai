"""Deterministic, report-appropriate data cleaning.

This is NOT ML preprocessing — there is intentionally no one-hot encoding (it
would explode categoricals into dozens of 0/1 columns and destroy the group-by /
chart / narrative that reports are built on) and no imputation or row-dropping
(a report should *describe* missingness, not invent or delete data). We only make
strictly-improving, explainable fixes:

  - trim column-name whitespace
  - normalize placeholder nulls ("N/A", "-", "") to real blanks
  - trim / collapse whitespace in text cells
  - coerce text that is really numbers ("$1,234", "45%") or dates to real types
  - merge case-variant category labels ("Male"/"male")
  - drop all-null and constant columns (no signal)
  - drop exact-duplicate rows

``clean_dataframe`` returns the cleaned frame plus a human-readable summary of
what changed; ``audit`` runs it as a dry-run to preview the same changes.
"""
from __future__ import annotations

import re

import pandas as pd
from pandas.api import types as pdt

from app.services.ingestion import _looks_like_datetime

# Case-insensitive placeholder tokens that really mean "missing".
_NULL_TOKENS = {
    "", "na", "n/a", "n\\a", "null", "none", "nan", "#n/a", "-", "--", "?",
    ".", "unknown", "n.a.", "missing",
}
_CURRENCY = "$€£₹¥"


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Apply the safe fixes. Returns (cleaned_df, changes)."""
    df = df.copy()
    changes: list[dict] = []

    # 1. Trim column-name whitespace.
    renames = {c: c.strip() for c in df.columns if isinstance(c, str) and c != c.strip()}
    if renames:
        df = df.rename(columns=renames)
        changes.append(_chg("trim_headers", "Cleaned column names",
                            f"Trimmed stray whitespace from {len(renames)} column name(s)."))

    # 2. Text cells: collapse whitespace, then map placeholder tokens to null.
    null_fixed = 0
    for c in _object_cols(df):
        s = df[c].map(_norm_text)
        mask = s.map(lambda v: isinstance(v, str) and v.lower() in _NULL_TOKENS)
        null_fixed += int(mask.sum())
        df[c] = s.mask(mask, other=pd.NA)
    if null_fixed:
        changes.append(_chg("null_tokens", "Standardized missing values",
                            f"Converted {null_fixed} placeholder value(s) like 'N/A', '-' or "
                            "blanks into proper empty cells."))

    # 3. Coerce text columns that are really numbers or dates.
    num_cols, dt_cols = [], []
    for c in _object_cols(df):
        non_null = df[c].dropna()
        if len(non_null) < 3:
            continue
        as_num = non_null.map(_to_number)
        if as_num.notna().mean() >= 0.9 and not _looks_like_datetime(non_null):
            df[c] = df[c].map(_to_number)
            num_cols.append(c)
        elif _looks_like_datetime(non_null):
            parsed = pd.to_datetime(df[c], errors="coerce")
            if parsed.notna().mean() >= 0.9:
                df[c] = parsed
                dt_cols.append(c)
    if num_cols:
        changes.append(_chg("coerce_numeric", "Fixed numeric columns stored as text",
                            f"Converted {len(num_cols)} column(s) to numbers: {_names(num_cols)}."))
    if dt_cols:
        changes.append(_chg("coerce_datetime", "Fixed date columns stored as text",
                            f"Parsed {len(dt_cols)} column(s) as dates: {_names(dt_cols)}."))

    # 4. Merge category labels that differ only by case ("FWD"/"fwd").
    merged = []
    for c in _object_cols(df):
        s = df[c].dropna().astype(str)
        if s.empty or s.nunique() > 60:
            continue
        if s.nunique() > s.str.lower().nunique():
            mapping = _canonical_case_map(df[c])
            df[c] = df[c].map(lambda v: mapping.get(v, v) if isinstance(v, str) else v)
            merged.append(c)
    if merged:
        changes.append(_chg("merge_case", "Merged duplicate categories",
                            f"Unified case-variant labels (e.g. 'Male'/'male') in "
                            f"{len(merged)} column(s): {_names(merged)}."))

    # 5. Drop all-null columns.
    empty = [c for c in df.columns if df[c].isna().all()]
    if empty:
        df = df.drop(columns=empty)
        changes.append(_chg("drop_empty_cols", "Removed empty columns",
                            f"Dropped {len(empty)} column(s) with no data: {_names(empty)}."))

    # 6. Drop constant columns (a single repeated value carries no signal).
    const = [c for c in df.columns if df[c].nunique(dropna=True) <= 1 and not df[c].isna().all()]
    if const:
        df = df.drop(columns=const)
        changes.append(_chg("drop_constant_cols", "Removed constant columns",
                            f"Dropped {len(const)} column(s) with one repeated value: {_names(const)}."))

    # 7. Drop exact-duplicate rows.
    before = len(df)
    df = df.drop_duplicates(ignore_index=True)
    if before - len(df):
        changes.append(_chg("drop_dup_rows", "Removed duplicate rows",
                            f"Dropped {before - len(df)} exact-duplicate row(s)."))

    return df, changes


def audit(parquet_path: str) -> list[dict]:
    """Dry-run: what cleaning WOULD do to this dataset (drives the recommendation
    card). Returns [] when the data is already clean."""
    df = pd.read_parquet(parquet_path)
    _, changes = clean_dataframe(df)
    return changes


def apply_cleaning(parquet_path: str) -> tuple[int, int, list[dict], list[dict]]:
    """Clean the Parquet in place and re-profile it.

    Reads the cached Parquet, applies the safe fixes, overwrites the cache (the
    original CSV is preserved elsewhere as backup), and re-profiles the cleaned
    frame. Returns ``(row_count, col_count, column_profiles, changes)`` so the
    caller can update the dataset row and its column profile in one shot. Shared
    by upload (auto-clean) and the manual /preprocess endpoint so both take the
    exact same path. Idempotent: re-running on already-clean data yields no
    changes.
    """
    # Imported here rather than at module top to keep the dependency one-way
    # (ingestion never imports preprocessing) and avoid a circular import.
    from app.services import ingestion

    df = pd.read_parquet(parquet_path)
    cleaned, changes = clean_dataframe(df)
    # Profile BEFORE overwriting the cache: if profiling somehow fails, the caller
    # still sees the original Parquet + original profile (consistent), rather than
    # a cleaned Parquet on disk paired with a stale profile in the database.
    profiles = ingestion.profile_dataframe(cleaned)
    ingestion.write_parquet(cleaned, parquet_path)
    return len(cleaned), cleaned.shape[1], profiles, changes


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _object_cols(df: pd.DataFrame) -> list[str]:
    """Text-like columns — object OR pandas StringDtype. (A plain `dtype == object`
    check misses StringDtype, which newer pandas uses for string columns.)"""
    return [
        c for c in df.columns
        if not (
            pdt.is_numeric_dtype(df[c])
            or pdt.is_datetime64_any_dtype(df[c])
            or pdt.is_bool_dtype(df[c])
        )
    ]


def _norm_text(v):
    return re.sub(r"\s+", " ", v).strip() if isinstance(v, str) else v


def _to_number(v):
    """Parse a currency/percent/thousands-formatted string to a float, else NA.
    Strict: float() rejects '12abc', so no false positives."""
    if isinstance(v, bool):
        return pd.NA
    if isinstance(v, (int, float)):
        return float(v)
    if not isinstance(v, str):
        return pd.NA
    t = v.strip().lstrip(_CURRENCY).strip().rstrip("%").replace(",", "")
    try:
        return float(t)
    except ValueError:
        return pd.NA


def _canonical_case_map(series: pd.Series) -> dict:
    """Map each value to the most frequent casing among its case-variants."""
    counts = series.dropna().astype(str).value_counts()
    best: dict[str, tuple[int, str]] = {}
    for val, cnt in counts.items():
        key = val.lower()
        if key not in best or cnt > best[key][0]:
            best[key] = (cnt, val)
    return {val: best[val.lower()][1] for val in counts.index}


def _names(cols, limit: int = 4) -> str:
    cols = list(cols)
    if len(cols) <= limit:
        return ", ".join(map(str, cols))
    return ", ".join(map(str, cols[:limit])) + f", +{len(cols) - limit} more"


def _chg(code: str, title: str, detail: str) -> dict:
    return {"code": code, "title": title, "detail": detail}
