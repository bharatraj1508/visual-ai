"""run_python tool — the escape hatch for analysis SQL can't express.

The LLM writes pandas against the DataFrame `df`; we execute it in the sandbox
(app/sandbox) and return the serialized `result`.
"""
from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.agent.context import DatasetContext
from app.sandbox.executor import SandboxError, run_python


class RunPythonArgs(BaseModel):
    code: str = Field(
        description=(
            "Python code operating on the pandas DataFrame `df` (with `pd` and "
            "`np` in scope). Assign the final answer to a variable named "
            "`result` (a DataFrame, Series, or scalar). No imports, no file or "
            "network access. Example: result = df.groupby('team')['pts'].mean()"
        )
    )


def build_code_tool(ctx: DatasetContext) -> StructuredTool:
    def run_python_tool(code: str) -> str:
        try:
            return json.dumps({"result": run_python(ctx.parquet_path, code)},
                              default=str)
        except SandboxError as exc:
            return json.dumps({"error": str(exc)})

    return StructuredTool.from_function(
        func=run_python_tool,
        name="run_python",
        description=(
            "Run pandas code on the dataset for analysis SQL can't express "
            "(rolling windows, custom transforms, stats). The DataFrame is "
            "`df`; assign the answer to `result`. Prefer query_data for simple "
            "filtering/aggregation."
        ),
        args_schema=RunPythonArgs,
    )
