"""Tests for the code sandbox: correct results, and rejection of escapes.

These spawn the real runner subprocess — the isolation IS the thing under test.
"""
import json

import pandas as pd
import pytest

from app.sandbox.executor import SandboxError, run_python, validate_code


@pytest.fixture
def parquet(tmp_path):
    df = pd.DataFrame(
        {"team": ["A", "A", "B"], "pts": [10, 20, 5], "reb": [1, 2, 3]}
    )
    path = tmp_path / "data.parquet"
    df.to_parquet(path, index=False)
    return str(path)


def test_scalar_result(parquet):
    out = run_python(parquet, "result = int(df['pts'].sum())")
    assert out == {"type": "value", "value": 35}


def test_dataframe_result(parquet):
    out = run_python(
        parquet, "result = df.groupby('team')['pts'].mean().reset_index()"
    )
    assert out["type"] == "dataframe"
    means = {r["team"]: r["pts"] for r in out["rows"]}
    assert means["A"] == 15.0 and means["B"] == 5.0


def test_series_result(parquet):
    out = run_python(parquet, "result = df['pts'] * 2")
    assert out["type"] == "series"


# --- guard rejections (static, no subprocess) --------------------------------

@pytest.mark.parametrize(
    "code",
    [
        "import os",
        "from os import system",
        "result = open('/etc/passwd').read()",
        "result = df.__class__.__init__.__globals__",
        "result = eval('1+1')",
        "result = getattr(df, 'values')",
    ],
)
def test_guard_rejects_escapes(code):
    with pytest.raises(SandboxError):
        validate_code(code)


def test_run_python_rejects_before_executing(parquet):
    with pytest.raises(SandboxError):
        run_python(parquet, "import socket")


def test_timeout_is_enforced(parquet):
    with pytest.raises(SandboxError, match="timed out"):
        run_python(parquet, "result = sum(range(10**12))", timeout_s=2)


def test_user_error_surfaces(parquet):
    with pytest.raises(SandboxError, match="KeyError"):
        run_python(parquet, "result = df['nonexistent_column'].sum()")


def test_cannot_write_files(parquet, tmp_path):
    # open() is blocked by the AST guard, so even attempting a write is rejected.
    with pytest.raises(SandboxError):
        run_python(parquet, f"result = open('{tmp_path}/x', 'w').write('hi')")
