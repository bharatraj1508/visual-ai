"""Sandbox child process. Reads a JSON job from stdin, executes user code
against the dataset's DataFrame under resource limits, prints a JSON result.

Run as: python -m app.sandbox.runner   (stdin = job JSON)

This process is deliberately started with a minimal environment (no DB URL, no
API keys) and tight rlimits. It is NOT a hardened security boundary against a
motivated attacker — see app/sandbox/executor.py for the threat model.
"""
import json
import sys

import numpy as np
import pandas as pd

# Safe subset of builtins exposed to user code. Notably absent: open, eval,
# exec, compile, __import__, getattr, globals — the escape hatches.
_ALLOWED_BUILTINS = [
    "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter",
    "float", "int", "isinstance", "len", "list", "map", "max", "min", "pow",
    "print", "range", "reversed", "round", "set", "sorted", "str", "sum",
    "tuple", "type", "zip",
]


def _safe_builtins() -> dict:
    import builtins

    return {name: getattr(builtins, name) for name in _ALLOWED_BUILTINS}


def _apply_limits(cpu_seconds: int, mem_bytes: int) -> None:
    """Best-effort resource limits. Some are not enforced on macOS; we set them
    anyway so they bite on Linux (Docker/prod)."""
    try:
        import resource
    except ImportError:  # non-Unix
        return
    for res, value in (
        (resource.RLIMIT_CPU, cpu_seconds),
        (resource.RLIMIT_FSIZE, 0),  # no file writes
        (resource.RLIMIT_AS, mem_bytes),  # address space
    ):
        try:
            resource.setrlimit(res, (value, value))
        except (ValueError, OSError):
            pass


def _serialize(result) -> dict:
    if result is None:
        return {"type": "none", "value": None}
    if isinstance(result, pd.DataFrame):
        head = result.head(1000)
        return {
            "type": "dataframe",
            "columns": [str(c) for c in result.columns],
            "rows": json.loads(head.to_json(orient="records", date_format="iso")),
            "row_count": int(len(head)),
            "truncated": bool(len(result) > 1000),
        }
    if isinstance(result, pd.Series):
        head = result.head(1000)
        return {
            "type": "series",
            "value": json.loads(head.to_json(date_format="iso")),
            "truncated": bool(len(result) > 1000),
        }
    try:
        json.dumps(result)
        return {"type": "value", "value": result}
    except (TypeError, ValueError):
        return {"type": "value", "value": str(result)}


def main() -> None:
    job = json.load(sys.stdin)
    df = pd.read_parquet(job["parquet_path"])

    # Limits go on right before running untrusted code (our own setup is exempt).
    _apply_limits(job.get("cpu_seconds", 8), job.get("mem_bytes", 1024 ** 3))

    namespace = {
        "__builtins__": _safe_builtins(),
        "pd": pd,
        "np": np,
        "df": df,
        "result": None,
    }
    try:
        exec(compile(job["code"], "<user_code>", "exec"), namespace)
        payload = {"ok": True, "result": _serialize(namespace.get("result"))}
    except Exception as exc:  # noqa: BLE001 — report any user-code failure
        payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    sys.stdout.write(json.dumps(payload))


if __name__ == "__main__":
    main()
