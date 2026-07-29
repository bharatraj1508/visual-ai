"""Filesystem layout for uploaded datasets.

    <STORAGE_DIR>/<user_id>/<dataset_id>/original__<filename>
    <STORAGE_DIR>/<user_id>/<dataset_id>/data.parquet

Local disk for now; swap for S3-compatible storage later without touching callers.
"""
import shutil
import uuid
from pathlib import Path

from app.core.config import settings


def dataset_dir(user_id: uuid.UUID, dataset_id: uuid.UUID) -> Path:
    path = Path(settings.STORAGE_DIR) / str(user_id) / str(dataset_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def original_path(user_id: uuid.UUID, dataset_id: uuid.UUID, filename: str) -> Path:
    # Prefix keeps the user's filename readable while avoiding collisions.
    safe = Path(filename).name
    return dataset_dir(user_id, dataset_id) / f"original__{safe}"


def indexed_original_path(
    user_id: uuid.UUID, dataset_id: uuid.UUID, index: int, filename: str
) -> Path:
    """Original-file path for one of several CSVs that form a single dataset.
    The index prevents same-named uploads from clobbering one another; the layout
    convention (the ``original__`` prefix, `Path(...).name` stripping) stays here."""
    safe = Path(filename).name
    return dataset_dir(user_id, dataset_id) / f"original__{index}__{safe}"


def extracted_csv_path(
    user_id: uuid.UUID, dataset_id: uuid.UUID, index: int, member_name: str
) -> Path:
    """Path for a CSV pulled out of an uploaded ZIP. The member's relative path
    is flattened into the name ('2024/players.csv' →
    'extracted__0__2024__players.csv') so nothing inside the archive dictates
    the directory layout."""
    safe = Path(member_name.replace("/", "__")).name
    return dataset_dir(user_id, dataset_id) / f"extracted__{index}__{safe}"


def parquet_path(user_id: uuid.UUID, dataset_id: uuid.UUID) -> Path:
    return dataset_dir(user_id, dataset_id) / "data.parquet"


def remove_dataset_files(user_id: uuid.UUID, dataset_id: uuid.UUID) -> None:
    path = Path(settings.STORAGE_DIR) / str(user_id) / str(dataset_id)
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
