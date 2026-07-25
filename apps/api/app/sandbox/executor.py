"""Runs LLM-generated pandas code in an isolated subprocess.

Defense in depth (MVP threat model = prevent accidents, resource abuse, and
trivial exfiltration by semi-trusted LLM output — NOT a motivated attacker):
  1. AST guard: no imports, no dunder attribute access, no dangerous builtins.
  2. Separate process with a minimal env (no DB URL / API keys reachable).
  3. rlimits: CPU seconds, address space, and RLIMIT_FSIZE=0 (no file writes).
  4. Wall-clock timeout that hard-kills the process.
  5. No imports allowed => no socket/urllib => no network.

For true multi-tenant isolation, run the subprocess inside a container/gVisor.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

from app.core.logging import logger

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_TIMEOUT_S = 10
DEFAULT_CPU_S = 8
DEFAULT_MEM_BYTES = 1024 ** 3  # 1 GiB

# Builtins that enable sandbox escapes or I/O.
_FORBIDDEN_NAMES = frozenset(
    {
        "eval", "exec", "compile", "open", "__import__", "globals", "locals",
        "vars", "getattr", "setattr", "delattr", "input", "breakpoint",
        "memoryview", "exit", "quit", "help",
    }
)


class SandboxError(ValueError):
    """Raised when code is rejected by the guard or fails/aborts in the sandbox."""


def validate_code(code: str) -> None:
    """Reject code that imports, touches dunders, or names dangerous builtins."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise SandboxError(f"Syntax error: {exc}") from exc

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise SandboxError("Imports are not allowed in sandboxed code.")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise SandboxError("Dunder attribute access is not allowed.")
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
            raise SandboxError(f"Use of '{node.id}' is not allowed.")


def run_python(
    parquet_path: str | Path,
    code: str,
    *,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    cpu_s: int = DEFAULT_CPU_S,
    mem_bytes: int = DEFAULT_MEM_BYTES,
) -> dict:
    """Execute `code` against the dataset. Returns the serialized `result`.

    The code runs with `df` (the DataFrame), `pd`, and `np` in scope and must
    assign its answer to a variable named `result`.
    """
    validate_code(code)

    job = json.dumps(
        {
            "code": code,
            "parquet_path": str(parquet_path),
            "cpu_seconds": cpu_s,
            "mem_bytes": mem_bytes,
        }
    )
    # Minimal env: withhold secrets (DATABASE_URL, GOOGLE_API_KEY, cloud creds).
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(_PROJECT_ROOT)}

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "app.sandbox.runner"],
            input=job,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=str(_PROJECT_ROOT),
            env=env,
        )
    except subprocess.TimeoutExpired:
        raise SandboxError(f"Execution timed out after {timeout_s}s.")

    if proc.returncode != 0:
        # Non-zero without JSON => killed by an rlimit (mem/cpu) or hard crash.
        detail = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else ""
        logger.warning("Sandbox process exited %s: %s", proc.returncode, detail)
        raise SandboxError(
            f"Execution aborted (likely resource limit). {detail}"[:500]
        )

    try:
        out = json.loads(proc.stdout.strip())
    except json.JSONDecodeError:
        raise SandboxError(f"Invalid sandbox output: {proc.stdout[:300]}")

    if not out.get("ok"):
        raise SandboxError(out.get("error", "Unknown sandbox error"))
    return out["result"]
