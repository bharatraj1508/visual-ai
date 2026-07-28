"""Tests for the deterministic cleaning service and the shared apply_cleaning
helper that upload and the /preprocess endpoint both use.

Real Parquet round-trips (no mocks): cleaning IS the thing under test.
"""
import pandas as pd
import pytest

from app.services import preprocessing


@pytest.fixture
def dirty_parquet(tmp_path):
    """A deliberately messy dataset covering several cleaning passes at once."""
    df = pd.DataFrame(
        {
            " amount ": ["$1,000", "$2,000", "$3,000", "$3,000"],  # header ws + currency
            "gender": ["Male", "male", "Female", "Female"],        # case-variant labels
            "blank": [None, None, None, None],                     # all-null column
        }
    )
    path = tmp_path / "data.parquet"
    df.to_parquet(path, index=False)
    return str(path)


def test_apply_cleaning_fixes_and_reprofiles(dirty_parquet):
    row_count, col_count, profiles, changes = preprocessing.apply_cleaning(dirty_parquet)

    codes = {c["code"] for c in changes}
    assert {"trim_headers", "coerce_numeric", "merge_case", "drop_empty_cols"} <= codes
    assert "drop_dup_rows" in codes  # rows 3 & 4 collapse once the empty col is gone

    # The empty column is gone; the header is trimmed; the dup row is dropped.
    names = {p["name"] for p in profiles}
    assert "amount" in names and " amount " not in names
    assert "blank" not in names
    assert row_count == 3 and col_count == 2

    # amount is now a real number, not text.
    amount = next(p for p in profiles if p["name"] == "amount")
    assert amount["dtype"] in {"integer", "float"}

    # The cache on disk reflects the cleaned frame.
    cleaned = pd.read_parquet(dirty_parquet)
    assert list(cleaned.columns) == ["amount", "gender"]
    assert pd.api.types.is_numeric_dtype(cleaned["amount"])


def test_apply_cleaning_is_idempotent(dirty_parquet):
    preprocessing.apply_cleaning(dirty_parquet)
    _, _, _, changes = preprocessing.apply_cleaning(dirty_parquet)
    assert changes == []  # already clean — nothing left to do


def test_clean_dataframe_normalizes_null_tokens():
    # `id` keeps the rows distinct so dedup doesn't collapse the two blanked rows.
    df = pd.DataFrame(
        {"note": ["N/A", "-", "real", "real value"], "id": [1, 2, 3, 4]}
    )
    cleaned, changes = preprocessing.clean_dataframe(df)
    assert {c["code"] for c in changes} >= {"null_tokens"}
    assert cleaned["note"].isna().sum() == 2
