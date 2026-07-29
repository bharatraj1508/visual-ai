"""Safe ZIP extraction: folder traversal, junk filtering, and bomb caps.

Archives are built in memory — no fixtures on disk.
"""
import zipfile
from io import BytesIO

import pytest

from app.core.config import settings
from app.services.archive import ArchiveError, extract_csv_members


def _zip(entries: dict[str, bytes]) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_extracts_nested_csvs_keeping_folder_paths():
    data = _zip(
        {
            "players.csv": b"a,b\n1,2\n",
            "2024/history/gameweeks.csv": b"c,d\n3,4\n",
        }
    )
    members = dict(extract_csv_members(data))
    assert set(members) == {"players.csv", "2024/history/gameweeks.csv"}
    assert members["players.csv"] == b"a,b\n1,2\n"


def test_skips_junk_and_non_csv_members():
    data = _zip(
        {
            "data/players.csv": b"a\n1\n",
            "__MACOSX/data/._players.csv": b"junk",
            "data/.DS_Store": b"junk",
            ".hidden/secret.csv": b"junk",
            "readme.txt": b"not data",
            "chart.png": b"\x89PNG",
        }
    )
    members = extract_csv_members(data)
    assert [name for name, _ in members] == ["data/players.csv"]


def test_traversal_names_are_neutralized():
    data = _zip({"../../etc/evil.csv": b"a\n1\n", "/abs/path.csv": b"b\n2\n"})
    names = [name for name, _ in extract_csv_members(data)]
    assert names == ["etc/evil.csv", "abs/path.csv"]
    assert all(".." not in n and not n.startswith("/") for n in names)


def test_rejects_corrupt_archive():
    with pytest.raises(ArchiveError, match="valid ZIP"):
        extract_csv_members(b"definitely not a zip")


def test_rejects_archive_without_csvs():
    with pytest.raises(ArchiveError, match="No CSV"):
        extract_csv_members(_zip({"readme.txt": b"hi", "img.png": b"x"}))


def test_rejects_too_many_csvs(monkeypatch):
    # The cap is env-tunable (settings.MAX_CSV_FILES); shrink it for the test.
    monkeypatch.setattr(settings, "MAX_CSV_FILES", 3)
    entries = {f"t{i}.csv": b"a\n1\n" for i in range(4)}
    with pytest.raises(ArchiveError, match="limit"):
        extract_csv_members(_zip(entries))


def test_rejects_oversized_contents():
    data = _zip({"big.csv": b"x" * 1000})
    with pytest.raises(ArchiveError, match="limit once extracted"):
        extract_csv_members(data, max_total_bytes=100)


def test_size_cap_spans_members_cumulatively():
    data = _zip({"a.csv": b"x" * 60, "b.csv": b"y" * 60})
    with pytest.raises(ArchiveError, match="limit once extracted"):
        extract_csv_members(data, max_total_bytes=100)
    # Each alone fits.
    assert len(extract_csv_members(data, max_total_bytes=200)) == 2
