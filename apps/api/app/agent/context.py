"""DatasetContext — everything the agent and its tools need about one dataset,
without ever touching the database or the raw rows directly.

A dataset is one or MORE tables (each an uploaded CSV, or a group of same-shaped
CSVs stacked together). Single-table datasets keep the original, compact schema
text verbatim; multi-table datasets additionally list each table by name and the
columns they share, so the LLM can query and join across them.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class DatasetContext:
    dataset_id: uuid.UUID
    parquet_path: str
    filename: str
    row_count: int
    # Column profile dicts for the PRIMARY table: name, dtype, null_count,
    # distinct_count, min_value, max_value, sample_values.
    columns: list[dict]
    # For multi-table datasets: one entry per table
    # ({name, filename, parquet_path, row_count, columns}). None => single table.
    tables: list[dict] | None = None

    def all_tables(self) -> list[dict]:
        """Every table as a uniform dict, synthesizing the single-table case as one
        table named `data` (the DuckDB table single-table datasets always used)."""
        if self.tables:
            return self.tables
        return [{
            "name": "data",
            "filename": self.filename,
            "parquet_path": self.parquet_path,
            "row_count": self.row_count,
            "columns": self.columns,
        }]

    def is_multi(self) -> bool:
        return bool(self.tables) and len(self.tables) > 1

    def schema_text(self) -> str:
        """Compact, token-cheap schema for the prompt — this, not the raw data, is
        what the LLM reasons over."""
        tables = self.all_tables()
        if len(tables) == 1:
            # Preserve the original single-table wording verbatim.
            lines = [
                f'Dataset "{self.filename}" — {tables[0]["row_count"]} rows, '
                f"{len(tables[0]['columns'])} columns.",
                "The queryable DuckDB table is named `data`. Columns:",
            ]
            lines += _column_lines(tables[0]["columns"])
            return "\n".join(lines)

        lines = [
            f'Dataset "{self.filename}" — {len(tables)} related tables. Each is a '
            "separate DuckDB table (named below); query them individually or JOIN "
            "them on shared columns."
        ]
        for t in tables:
            lines.append("")
            lines.append(
                f'Table `{t["name"]}` (from "{t["filename"]}") — {t["row_count"]} '
                f"rows, {len(t['columns'])} columns:"
            )
            lines += _column_lines(t["columns"])
        rels = _relationships(tables)
        if rels:
            lines.append("")
            lines.append("Shared columns (candidate join keys):")
            lines += rels
        return "\n".join(lines)

    @classmethod
    def from_models(cls, dataset, columns) -> "DatasetContext":
        """Build from a Dataset ORM row and its (primary-table) DatasetColumn rows."""
        primary = [
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
        ]
        tables = None
        raw = getattr(dataset, "tables", None)
        if raw:
            tables = [
                {
                    "name": t["name"],
                    "filename": t.get("filename", t["name"]),
                    "parquet_path": t["parquet_path"],
                    "row_count": t.get("row_count") or 0,
                    "columns": t.get("columns", []),
                }
                for t in raw
            ]
        return cls(
            dataset_id=dataset.id,
            parquet_path=dataset.parquet_path,
            filename=dataset.filename,
            row_count=dataset.row_count or 0,
            columns=primary,
            tables=tables,
        )


def _column_lines(columns: list[dict]) -> list[str]:
    lines = []
    for col in columns:
        samples = ", ".join(str(s) for s in col.get("sample_values", [])[:3])
        rng = ""
        if col.get("min_value") is not None:
            rng = f", range [{col['min_value']} .. {col['max_value']}]"
        lines.append(
            f"- {col['name']} ({col['dtype']}): "
            f"{col['distinct_count']} distinct, {col['null_count']} nulls"
            f"{rng}. e.g. {samples}"
        )
    return lines


def _relationships(tables: list[dict]) -> list[str]:
    """Columns that appear in more than one table — the natural join keys."""
    where: dict[str, list[str]] = defaultdict(list)
    for t in tables:
        for c in t["columns"]:
            where[c["name"]].append(t["name"])
    return [
        f"- `{col}` in {', '.join(f'`{n}`' for n in names)}"
        for col, names in where.items()
        if len(names) >= 2
    ]
