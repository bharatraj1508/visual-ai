"""Safe extraction of CSVs from an uploaded ZIP archive.

A ZIP may carry a whole folder tree of exports. We pull out only the CSV
members — wherever they sit in the tree — and keep each member's relative path
as its display name ("2024/players.csv"), so downstream table names and LLM
prompts retain the folder context. Everything else in the archive (other file
types, OS junk like __MACOSX, hidden files) is ignored.

Extraction is bytes-in, bytes-out: member paths are never used to build
filesystem paths, so hostile names (../, absolute paths) can't escape anywhere.
Explicit caps on member count and uncompressed size keep zip bombs out.
"""
from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import PurePosixPath

from app.core.config import settings


class ArchiveError(Exception):
    """The archive can't be used. The message is user-facing."""


def _clean_name(raw: str) -> str:
    """Member path as a safe, relative, forward-slash display name — drive
    letters, anchors and traversal components dropped."""
    parts = [
        p
        for p in PurePosixPath(raw.replace("\\", "/")).parts
        if p not in ("", ".", "..", "/") and ":" not in p
    ]
    return "/".join(parts)


def _is_junk(name: str) -> bool:
    return any(p.startswith(".") or p == "__MACOSX" for p in name.split("/"))


def extract_csv_members(
    data: bytes, max_total_bytes: int | None = None
) -> list[tuple[str, bytes]]:
    """Return ``(relative_name, content)`` for every CSV inside the archive.

    Raises ArchiveError — with a user-facing message — when the archive is
    corrupt, password-protected, contains no CSVs, or exceeds the member-count
    or uncompressed-size caps.
    """
    cap = max_total_bytes if max_total_bytes is not None else settings.max_upload_bytes
    too_big = ArchiveError(
        f"ZIP contents exceed the {settings.MAX_UPLOAD_MB} MB limit once extracted."
    )
    try:
        zf = zipfile.ZipFile(BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ArchiveError("This file isn't a valid ZIP archive.") from exc

    with zf:
        members: list[tuple[str, zipfile.ZipInfo]] = []
        declared = 0
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = _clean_name(info.filename)
            if not name or _is_junk(name) or not name.lower().endswith(".csv"):
                continue
            if info.flag_bits & 0x1:
                raise ArchiveError("Password-protected ZIPs aren't supported.")
            declared += info.file_size
            if declared > cap:
                raise too_big
            members.append((name, info))

        if not members:
            raise ArchiveError("No CSV files found inside the ZIP.")
        if len(members) > settings.MAX_CSV_FILES:
            raise ArchiveError(
                f"ZIP contains {len(members)} CSV files; the limit is "
                f"{settings.MAX_CSV_FILES}. Combine or drop some and try again."
            )

        # Headers can lie about sizes, so the declared-size check above is only
        # a fast fail — enforce the cap on the bytes actually decompressed.
        out: list[tuple[str, bytes]] = []
        budget = cap
        for name, info in members:
            try:
                with zf.open(info) as fh:
                    content = fh.read(budget + 1)
            except RuntimeError as exc:  # encrypted member missed by the flag check
                raise ArchiveError("Password-protected ZIPs aren't supported.") from exc
            if len(content) > budget:
                raise too_big
            budget -= len(content)
            out.append((name, content))
        return out
