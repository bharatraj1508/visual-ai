"""Tests for goal-relevant row scoping in the analysis battery and the spec
parser. Real Parquet, real pandas — scoping is the behaviour under test.
"""
import uuid

import pandas as pd
import pytest

from app.agent.analysis import run_analysis
from app.agent.context import DatasetContext
from app.agent.report import _parse_scope


@pytest.fixture
def football(tmp_path):
    """One row per player across four positions; conceding is a defensive metric."""
    positions = (["GK"] * 5) + (["DEF"] * 35) + (["MID"] * 30) + (["FWD"] * 30)
    df = pd.DataFrame(
        {
            "player": [f"P{i}" for i in range(len(positions))],
            "position": positions,
            "goals_conceded": [40 - i % 20 for i in range(len(positions))],
            "expected_conceded": [35 - i % 15 for i in range(len(positions))],
        }
    )
    path = tmp_path / "data.parquet"
    df.to_parquet(path, index=False)
    return str(path)


def _ctx(path: str) -> DatasetContext:
    return DatasetContext(
        dataset_id=uuid.uuid4(),
        parquet_path=path,
        filename="players.csv",
        row_count=100,
        columns=[
            {"name": "player", "dtype": "text", "distinct_count": 100,
             "null_count": 0, "min_value": None, "max_value": None, "sample_values": ["P1"]},
            {"name": "position", "dtype": "categorical", "distinct_count": 4,
             "null_count": 0, "min_value": None, "max_value": None,
             "sample_values": ["GK", "DEF", "MID", "FWD"]},
            {"name": "goals_conceded", "dtype": "integer", "distinct_count": 20,
             "null_count": 0, "min_value": "20", "max_value": "40", "sample_values": ["40"]},
            {"name": "expected_conceded", "dtype": "integer", "distinct_count": 15,
             "null_count": 0, "min_value": "20", "max_value": "35", "sample_values": ["35"]},
        ],
    )


def _spec(**scope) -> dict:
    return {
        "segment_dimensions": ["position"],
        "rank_measures": ["goals_conceded"],
        "scope": scope or None,
    }


def test_valid_scope_restricts_and_notes(football):
    res = run_analysis(
        _ctx(football),
        goal="goals conceded vs expected",
        spec=_spec(column="position", include=["DEF", "GK"], reason="defensive roles"),
    )
    assert res.scope_note is not None
    assert "defensive roles" in res.scope_note
    assert "DEF" in res.scope_note and "GK" in res.scope_note
    # 40 of 100 rows kept (5 GK + 35 DEF) — the overview finding must reflect that.
    assert "40" in res.scope_note
    overview = next(f for f in res.findings if f.kind == "overview")
    assert "40 rows" in overview.text


def test_scope_covering_all_values_is_ignored(football):
    res = run_analysis(
        _ctx(football),
        goal="x",
        spec=_spec(column="position", include=["GK", "DEF", "MID", "FWD"]),
    )
    assert res.scope_note is None  # filters nothing → fail open


def test_scope_with_no_matching_values_is_ignored(football):
    res = run_analysis(
        _ctx(football),
        goal="x",
        spec=_spec(column="position", include=["Sweeper"]),
    )
    assert res.scope_note is None  # 0 rows match → fail open


def test_scope_below_fraction_floor_is_ignored(football):
    # GK alone is 5/100 = 5%, below the 10% floor → fail open to the full dataset.
    res = run_analysis(
        _ctx(football), goal="x", spec=_spec(column="position", include=["GK"])
    )
    assert res.scope_note is None


def test_no_scope_analyzes_everything(football):
    res = run_analysis(_ctx(football), goal="x", spec=_spec())
    assert res.scope_note is None
    overview = next(f for f in res.findings if f.kind == "overview")
    assert "100 rows" in overview.text


# --- _parse_scope validation ------------------------------------------------

def test_parse_scope_rejects_unknown_column():
    assert _parse_scope({"column": "nope", "include": ["x"]}, {"position"}) is None


def test_parse_scope_rejects_empty_include():
    assert _parse_scope({"column": "position", "include": []}, {"position"}) is None


def test_parse_scope_accepts_valid():
    out = _parse_scope(
        {"column": "position", "include": ["DEF", "GK"], "reason": "defense"},
        {"position"},
    )
    assert out == {"column": "position", "include": ["DEF", "GK"], "reason": "defense"}
