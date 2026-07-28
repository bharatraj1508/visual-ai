"""Tests for the LLM-free parts of suggestion generation: prompt assembly,
response parsing, and the schema-derived fallback.
"""
from app.agent.context import DatasetContext
from app.agent.suggestions import _build_prompt, _fallback, _parse


def _ctx(tmp_path) -> DatasetContext:
    return DatasetContext(
        dataset_id=None,
        parquet_path=str(tmp_path / "x.parquet"),  # never read; fallback is schema-only
        filename="sales.csv",
        row_count=100,
        columns=[
            {"name": "region", "dtype": "categorical", "distinct_count": 4,
             "null_count": 0, "min_value": None, "max_value": None,
             "sample_values": ["West"]},
            {"name": "revenue", "dtype": "float", "distinct_count": 90,
             "null_count": 0, "min_value": "1.0", "max_value": "9.0",
             "sample_values": ["4.0"]},
            {"name": "cost", "dtype": "float", "distinct_count": 80,
             "null_count": 0, "min_value": "1.0", "max_value": "8.0",
             "sample_values": ["3.0"]},
        ],
    )


def test_build_prompt_includes_signals_and_purpose():
    prompt = _build_prompt(
        schema="SCHEMA_HERE",
        signals="Signals detected:\n- `a` and `b` are strongly correlated",
        use_purpose="professional",
        count=5,
    )
    assert "SCHEMA_HERE" in prompt
    assert "strongly correlated" in prompt
    assert "professional" in prompt and "goal" in prompt


def test_build_prompt_omits_absent_signals_and_purpose_cleanly():
    prompt = _build_prompt("SCHEMA", signals="", use_purpose=None, count=5)
    assert "SCHEMA" in prompt
    # No dangling artefacts when both optional pieces are absent.
    assert "None" not in prompt
    assert "describes their goal" not in prompt
    assert "Signals detected" not in prompt


def test_parse_filters_bad_charts_and_incomplete_items():
    raw = (
        '[{"title": "T1", "question": "Q1", "rationale": "R1", '
        '"chart_types": ["bar", "heatmap", "scatter"]},'
        '{"title": "", "question": "no title so dropped"},'
        '{"title": "T2", "question": "Q2"}]'
    )
    out = _parse(raw)
    assert len(out) == 2  # the empty-title item is dropped
    assert out[0]["chart_types"] == ["bar", "scatter"]  # "heatmap" filtered out
    assert out[1]["chart_types"] == ["bar", "line"]  # default when none survive


def test_fallback_returns_requested_count(tmp_path):
    ideas = _fallback(_ctx(tmp_path), count=5)
    assert len(ideas) == 5
    assert all(i["title"] and i["question"] and i["chart_types"] for i in ideas)
