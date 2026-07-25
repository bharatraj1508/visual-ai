"""DatasetContext — everything the agent and its tools need about one dataset,
without ever touching the database or the raw rows directly."""
from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass
class DatasetContext:
    dataset_id: uuid.UUID
    parquet_path: str
    filename: str
    row_count: int
    # Column profile dicts: name, dtype, null_count, distinct_count,
    # min_value, max_value, sample_values.
    columns: list[dict]

    def schema_text(self) -> str:
        """Compact, token-cheap schema description for the system prompt.

        This — not the raw data — is what the LLM reasons over.
        """
        lines = [
            f'Dataset "{self.filename}" — {self.row_count} rows, '
            f"{len(self.columns)} columns.",
            "The queryable DuckDB table is named `data`. Columns:",
        ]
        for col in self.columns:
            samples = ", ".join(str(s) for s in col.get("sample_values", [])[:3])
            rng = ""
            if col.get("min_value") is not None:
                rng = f", range [{col['min_value']} .. {col['max_value']}]"
            lines.append(
                f"- {col['name']} ({col['dtype']}): "
                f"{col['distinct_count']} distinct, {col['null_count']} nulls"
                f"{rng}. e.g. {samples}"
            )
        return "\n".join(lines)

    @classmethod
    def from_models(cls, dataset, columns) -> "DatasetContext":
        """Build from a Dataset ORM row and its DatasetColumn rows."""
        return cls(
            dataset_id=dataset.id,
            parquet_path=dataset.parquet_path,
            filename=dataset.filename,
            row_count=dataset.row_count or 0,
            columns=[
                {
                    "name": c.name,
                    "dtype": c.dtype,
                    "null_count": c.null_count,
                    "distinct_count": c.distinct_count,
                    "min_value": c.min_value,
                    "max_value": c.max_value,
                    "sample_values": c.sample_values,
                }
                for c in columns
            ],
        )
