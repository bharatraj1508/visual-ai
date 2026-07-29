"""Multi-table datasets: clustering into tables, cross-table querying, the
multi-table schema text, and single-table backward compatibility.

Real DataFrames / Parquet / DuckDB — no mocks.
"""
import uuid

import pandas as pd
import pytest

from app.agent.context import DatasetContext
from app.agent.signals import signal_digest
from app.services import data_access, ingestion


# --- build_tables: never reject, cluster by schema ---------------------------

def _named(**frames):
    return [(name, df) for name, df in frames.items()]


def test_same_schema_files_become_one_stacked_table():
    a = pd.DataFrame({"region": ["W"], "rev": [1]})
    b = pd.DataFrame({"region": ["E"], "rev": [2]})
    tables = ingestion.build_tables(_named(**{"jan.csv": a, "feb.csv": b}))
    assert len(tables) == 1
    assert len(tables[0]["df"]) == 2  # stacked


def test_different_schemas_become_separate_tables():
    orders = pd.DataFrame({"order_id": [1, 2], "cust_id": [10, 11]})
    customers = pd.DataFrame({"cust_id": [10, 11], "region": ["W", "E"]})
    tables = ingestion.build_tables(
        _named(**{"orders.csv": orders, "customers.csv": customers})
    )
    assert len(tables) == 2
    names = {t["name"] for t in tables}
    assert names == {"orders", "customers"}


def test_unrelated_files_are_not_rejected():
    a = pd.DataFrame({"a": [1], "b": [2]})
    b = pd.DataFrame({"c": [3], "d": [4]})
    tables = ingestion.build_tables(_named(**{"a.csv": a, "b.csv": b}))
    assert len(tables) == 2  # kept as two tables, never raised


def test_folder_paths_from_zip_members_distinguish_table_names():
    # Same filename in different folders (as extracted from a ZIP) — different
    # schemas, so they stay separate tables named after their folders.
    players = pd.DataFrame({"player": ["A"], "goals": [3]})
    teams = pd.DataFrame({"team": ["X"], "points": [50]})
    tables = ingestion.build_tables(
        _named(**{"2024/stats.csv": players, "teams/stats.csv": teams})
    )
    assert {t["name"] for t in tables} == {"t_2024_stats", "teams_stats"}


def test_ingest_rejects_too_many_distinct_tables(tmp_path, monkeypatch):
    # The cap is env-tunable (settings.MAX_DATASET_TABLES) and applies to the
    # CLUSTERED table count, so many same-schema files never trip it.
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_DATASET_TABLES", 2)
    paths = []
    for i in range(3):  # three distinct schemas → three tables > cap of 2
        p = tmp_path / f"t{i}.csv"
        p.write_text(f"col_{i}\n1\n")
        paths.append((f"t{i}.csv", str(p)))
    with pytest.raises(ingestion.TooManyTablesError, match="limit is 2"):
        ingestion.ingest_tables(paths, str(tmp_path))

    # Same schema across many files clusters into ONE table — no rejection.
    same = []
    for i in range(5):
        p = tmp_path / f"part{i}.csv"
        p.write_text("region,rev\nW,1\n")
        same.append((f"part{i}.csv", str(p)))
    tables_info, _, _ = ingestion.ingest_tables(same, str(tmp_path))
    assert len(tables_info) == 1


def test_table_names_are_sql_safe_and_unique():
    a = pd.DataFrame({"x": [1]})
    b = pd.DataFrame({"y": [2]})  # different schema → separate table, same stem clash
    tables = ingestion.build_tables([("2024 Data!.csv", a), ("2024 Data!.csv", b)])
    names = [t["name"] for t in tables]
    assert names[0] != names[1]  # de-duplicated
    assert all(n.replace("_", "").isalnum() and not n[0].isdigit() for n in names)


# --- ingest_tables: disk + cleaning ------------------------------------------

def test_ingest_tables_writes_per_table_parquet(tmp_path):
    orders = tmp_path / "orders.csv"
    customers = tmp_path / "customers.csv"
    pd.DataFrame({"order_id": [1, 2], "cust_id": [10, 11]}).to_csv(orders, index=False)
    pd.DataFrame({"cust_id": [10, 11], "region": ["W", "E"]}).to_csv(customers, index=False)

    info, _changes, _pre = ingestion.ingest_tables(
        [("orders.csv", orders), ("customers.csv", customers)], tmp_path
    )
    assert len(info) == 2
    for t in info:
        assert t["parquet_path"].endswith(".parquet")
        assert pd.read_parquet(t["parquet_path"]) is not None
        assert t["columns"]  # profiled


def test_ingest_tables_single_uses_legacy_data_parquet(tmp_path):
    pd.DataFrame({"x": [1, 2, 3]}).to_csv(tmp_path / "one.csv", index=False)
    info, _c, _p = ingestion.ingest_tables([("one.csv", tmp_path / "one.csv")], tmp_path)
    assert len(info) == 1
    assert info[0]["parquet_path"].endswith("data.parquet")  # unchanged layout


# --- query_tables: cross-table SQL -------------------------------------------

def test_query_tables_joins_across_tables(tmp_path):
    o = tmp_path / "orders.parquet"
    c = tmp_path / "customers.parquet"
    pd.DataFrame({"order_id": [1, 2, 3], "cust_id": [10, 10, 11]}).to_parquet(o, index=False)
    pd.DataFrame({"cust_id": [10, 11], "region": ["W", "E"]}).to_parquet(c, index=False)

    df = data_access.query_tables(
        [("orders", o), ("customers", c)],
        "SELECT o.order_id, c.region FROM orders o JOIN customers c ON o.cust_id = c.cust_id",
    )
    assert set(df.columns) == {"order_id", "region"}
    assert len(df) == 3
    assert set(df["region"]) == {"W", "E"}


def test_query_tables_rejects_non_select(tmp_path):
    o = tmp_path / "orders.parquet"
    pd.DataFrame({"a": [1]}).to_parquet(o, index=False)
    with pytest.raises(data_access.QueryError):
        data_access.query_tables([("orders", o)], "DROP TABLE orders")


# --- DatasetContext multi-table schema ---------------------------------------

def _multi_ctx() -> DatasetContext:
    tables = [
        {"name": "orders", "filename": "orders.csv", "parquet_path": "/x/o.parquet",
         "row_count": 100, "columns": [
             {"name": "order_id", "dtype": "integer", "distinct_count": 100,
              "null_count": 0, "min_value": "1", "max_value": "100", "sample_values": ["1"]},
             {"name": "cust_id", "dtype": "integer", "distinct_count": 40,
              "null_count": 0, "min_value": "1", "max_value": "40", "sample_values": ["1"]},
         ]},
        {"name": "customers", "filename": "customers.csv", "parquet_path": "/x/c.parquet",
         "row_count": 40, "columns": [
             {"name": "cust_id", "dtype": "integer", "distinct_count": 40,
              "null_count": 0, "min_value": "1", "max_value": "40", "sample_values": ["1"]},
             {"name": "region", "dtype": "categorical", "distinct_count": 4,
              "null_count": 0, "min_value": None, "max_value": None, "sample_values": ["W"]},
         ]},
    ]
    return DatasetContext(
        dataset_id=uuid.uuid4(), parquet_path="/x/o.parquet", filename="shop",
        row_count=140, columns=tables[0]["columns"], tables=tables,
    )


def test_multi_schema_text_lists_tables_and_relationships():
    text = _multi_ctx().schema_text()
    assert "Table `orders`" in text and "Table `customers`" in text
    assert "Shared columns" in text
    assert "`cust_id`" in text  # the join key linking the two tables


def test_is_multi_flag():
    assert _multi_ctx().is_multi() is True


def test_signal_digest_groups_by_table(tmp_path):
    o = tmp_path / "orders.parquet"
    c = tmp_path / "customers.parquet"
    pd.DataFrame({"amount": [100, 200, 300, 400], "region": ["A", "A", "B", "B"]}).to_parquet(o, index=False)
    pd.DataFrame({"x": [1, 2, 3, 4], "y": [2, 4, 6, 8]}).to_parquet(c, index=False)
    ctx = DatasetContext(
        dataset_id=uuid.uuid4(), parquet_path=str(o), filename="shop",
        row_count=8, columns=[],
        tables=[
            {"name": "orders", "filename": "orders.csv", "parquet_path": str(o),
             "row_count": 4, "columns": []},
            {"name": "customers", "filename": "customers.csv", "parquet_path": str(c),
             "row_count": 4, "columns": []},
        ],
    )
    digest = signal_digest(ctx)
    assert "In table `orders`" in digest and "In table `customers`" in digest


def test_single_table_context_unchanged():
    ctx = DatasetContext(
        dataset_id=uuid.uuid4(), parquet_path="/x/data.parquet", filename="sales.csv",
        row_count=5, columns=[
            {"name": "pct", "dtype": "float", "distinct_count": 5, "null_count": 0,
             "min_value": "50.0", "max_value": "100.0", "sample_values": ["90.0"]},
        ],
    )
    assert ctx.is_multi() is False
    text = ctx.schema_text()
    assert "table is named `data`" in text  # legacy wording preserved
    assert "Table `" not in text  # no multi-table blocks
