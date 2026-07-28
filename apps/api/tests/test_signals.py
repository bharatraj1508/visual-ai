"""Tests for the signal digest that grounds report suggestions in real
relationships. Real Parquet, real pandas — the computation is the subject.
"""
import pandas as pd
import pytest

from app.agent.context import DatasetContext
from app.agent.signals import signal_digest


def _ctx(parquet_path: str) -> DatasetContext:
    return DatasetContext(
        dataset_id=None,
        parquet_path=parquet_path,
        filename="t.csv",
        row_count=0,
        columns=[],  # signal_digest reads the Parquet directly, not the profile
    )


def _write(tmp_path, df) -> str:
    path = tmp_path / "data.parquet"
    df.to_parquet(path, index=False)
    return str(path)


def test_digest_surfaces_correlation_and_contrast(tmp_path):
    df = pd.DataFrame(
        {
            "region": ["A", "A", "A", "B", "B", "B"],
            "sales": [100, 110, 90, 10, 12, 8],  # ~10x higher in A than B
            "x": [1, 2, 3, 4, 5, 6],
            "y": [2, 4, 6, 8, 10, 12],  # perfectly correlated with x
        }
    )
    digest = signal_digest(_ctx(_write(tmp_path, df)))

    assert digest  # non-empty
    assert "correlated" in digest and "`x`" in digest and "`y`" in digest
    assert "varies sharply across `region`" in digest and "`sales`" in digest


def test_digest_detects_contrast_on_signed_metric(tmp_path):
    # profit goes negative, so the max/min ratio path can't fire — the spread
    # fallback must still surface the dramatic split across region.
    df = pd.DataFrame(
        {
            "region": ["A", "A", "A", "B", "B", "B"],
            "profit": [-50, -40, -60, 500, 520, 480],
        }
    )
    digest = signal_digest(_ctx(_write(tmp_path, df)))
    assert "varies sharply across `region`" in digest and "`profit`" in digest
    assert "much higher for 'B' than 'A'" in digest


def test_digest_flags_time_column(tmp_path):
    df = pd.DataFrame(
        {
            "day": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "value": [1, 2, 3],
        }
    )
    digest = signal_digest(_ctx(_write(tmp_path, df)))
    assert "time column(s)" in digest and "`day`" in digest


def test_digest_empty_when_no_signal(tmp_path):
    # A single, unremarkable numeric column: no pairs, no groups, no skew.
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5]})
    assert signal_digest(_ctx(_write(tmp_path, df))) == ""


def test_digest_never_raises_on_bad_path(tmp_path):
    assert signal_digest(_ctx(str(tmp_path / "does-not-exist.parquet"))) == ""
