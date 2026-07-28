"""Turn a dataset's actual values into a compact "signal digest" for the
suggestion prompt.

The suggestion model otherwise reasons over column *names* and types alone, so
it guesses at relationships and often proposes hollow "compare A vs B" ideas.
This module computes a handful of *real* relationships from the cleaned Parquet —
strong numeric correlations, categorical splits that move a metric, time columns,
and skew — and renders them as a few grounded bullet points. Fed into the prompt,
they anchor suggestions to structure that genuinely exists in the data.

Everything here is best-effort: any failure (whole digest or a single kind)
degrades to fewer/no signals rather than breaking suggestion generation. Only
relationships clearing the configured thresholds are surfaced, so weak or noisy
pairs never reach the prompt.
"""
from __future__ import annotations

import warnings

import pandas as pd
from pandas.api import types as pdt

from app.agent.context import DatasetContext
from app.core.config import settings
from app.core.logging import logger
from app.services import data_access

# A categorical column with more groups than this makes for a noisy split and a
# long, low-signal group-by — skip it for contrast detection.
_MAX_CONTRAST_GROUPS = 30
# Bound the pairwise contrast search so a very wide table can't blow up compute.
_MAX_COLS_PER_AXIS = 8
# For signed metrics (where a max/min ratio is meaningless), a contrast counts
# when the group-mean spread is at least this many standard deviations wide.
_SIGNED_SPREAD_MIN = 1.0


def signal_digest(ctx: DatasetContext) -> str:
    """Return a compact, prompt-ready block of real relationships, or "".

    Computes per table and, for multi-table datasets, groups the findings under
    each table name. Empty string means "nothing notable found" (or the
    computation failed) — the caller then falls back to a schema-only prompt.
    """
    tables = ctx.all_tables()
    multi = len(tables) > 1
    lines: list[str] = []
    for t in tables:
        try:
            df = data_access.load_dataframe(t["parquet_path"])
        except Exception:  # noqa: BLE001 — skip a table we can't read; never break suggestions
            logger.warning("Signal digest: could not load %s", t["parquet_path"], exc_info=True)
            continue
        table_lines = _table_signals(df)
        if not table_lines:
            continue
        if multi:
            lines.append(f"In table `{t['name']}`:")
            lines += [f"  {ln}" for ln in table_lines]
        else:
            lines += table_lines

    if not lines:
        return ""
    header = (
        "Signals detected in the data (ground your ideas in these — they are real "
        "relationships measured in the data, not guesses):"
    )
    return header + "\n" + "\n".join(lines)


def _table_signals(df) -> list[str]:
    """The four signal probes for one table's dataframe."""
    numeric = [c for c in df.columns if pdt.is_numeric_dtype(df[c]) and not pdt.is_bool_dtype(df[c])]
    datetimes = [c for c in df.columns if pdt.is_datetime64_any_dtype(df[c])]
    categoricals = [
        c
        for c in df.columns
        if c not in numeric
        and c not in datetimes
        and 2 <= df[c].nunique(dropna=True) <= _MAX_CONTRAST_GROUPS
    ]
    return (
        _correlations(df, numeric)
        + _contrasts(df, categoricals, numeric)
        + _time_columns(datetimes)
        + _skews(df, numeric)
    )


def _correlations(df: pd.DataFrame, numeric: list[str]) -> list[str]:
    """Strongly correlated numeric pairs — candidates for driver/relationship reports."""
    if len(numeric) < 2:
        return []
    try:
        matrix = df[numeric].corr(method="pearson")
    except Exception:  # noqa: BLE001
        return []
    # Keep the signed r straight off the matrix — no need to recompute per pair.
    pairs: list[tuple[float, str, str]] = []
    for i, a in enumerate(numeric):
        for b in numeric[i + 1 :]:
            r = matrix.at[a, b]
            if pd.notna(r) and abs(r) >= settings.SIGNAL_CORRELATION_MIN:
                pairs.append((r, a, b))
    pairs.sort(key=lambda p: abs(p[0]), reverse=True)
    return [
        f"- `{a}` and `{b}` are {_strength(abs(r))} correlated (r={r:+.2f})"
        for r, a, b in pairs[: settings.SIGNAL_MAX_PER_KIND]
    ]


def _contrasts(
    df: pd.DataFrame, categoricals: list[str], numeric: list[str]
) -> list[str]:
    """Categorical splits where a metric's group-average varies a lot — the raw
    material for "what separates group X from Y" cohort reports."""
    found: list[tuple[float, str]] = []
    for cat in categoricals[:_MAX_COLS_PER_AXIS]:
        for num in numeric[:_MAX_COLS_PER_AXIS]:
            try:
                means = df.groupby(cat, observed=True)[num].mean().dropna()
            except Exception:  # noqa: BLE001
                continue
            if len(means) < 2:
                continue
            lo, hi = means.min(), means.max()
            hi_grp, lo_grp = means.idxmax(), means.idxmin()
            if lo > 0:
                # Positive metric: a max/min ratio is the intuitive, LLM-friendly framing.
                ratio = hi / lo
                if ratio < settings.SIGNAL_CONTRAST_MIN:
                    continue
                score = ratio
                phrase = f"~{ratio:.1f}× higher for '{hi_grp}' than '{lo_grp}'"
            else:
                # Signed metric (profit, margin, growth): a ratio is meaningless, so
                # measure the spread of group means against the column's own std.
                std = df[num].std()
                if not std or pd.isna(std):
                    continue
                spread = (hi - lo) / std
                if spread < _SIGNED_SPREAD_MIN:
                    continue
                score = spread
                phrase = f"much higher for '{hi_grp}' than '{lo_grp}'"
            found.append((score, f"- `{num}` varies sharply across `{cat}` ({phrase})"))
    found.sort(key=lambda x: x[0], reverse=True)
    return [line for _, line in found[: settings.SIGNAL_MAX_PER_KIND]]


def _time_columns(datetimes: list[str]) -> list[str]:
    if not datetimes:
        return []
    cols = ", ".join(f"`{c}`" for c in datetimes[: settings.SIGNAL_MAX_PER_KIND])
    return [f"- time column(s) {cols} support trend-over-time and seasonality analysis"]


def _skews(df: pd.DataFrame, numeric: list[str]) -> list[str]:
    """Heavily-skewed numerics — good candidates for outlier/extreme-value reports."""
    flagged: list[tuple[float, str]] = []
    for col in numeric:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                skew = df[col].skew()
        except Exception:  # noqa: BLE001
            continue
        if pd.notna(skew) and abs(skew) >= settings.SIGNAL_SKEW_MIN:
            flagged.append(
                (abs(skew), f"- `{col}` is heavily skewed — likely outliers or a long tail")
            )
    flagged.sort(key=lambda x: x[0], reverse=True)
    return [line for _, line in flagged[: settings.SIGNAL_MAX_PER_KIND]]


def _strength(abs_r: float) -> str:
    if abs_r >= 0.7:
        return "strongly"
    if abs_r >= 0.5:
        return "moderately"
    return "notably"
