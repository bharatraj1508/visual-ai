"""Dataset endpoints: upload a CSV (profiled synchronously for small data),
list/get datasets, fetch the column profile, and delete."""
import asyncio
import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import logger
from app.core.security import get_current_user
from app.models.dataset import Dataset, DatasetStatus
from app.models.dataset_column import DatasetColumn
from app.models.user import User
from app.schemas.dataset import DatasetProfile, DatasetRead
from app.services import ingestion, storage

router = APIRouter()

_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB (small-data tier)


async def _get_owned_dataset(
    dataset_id: uuid.UUID, user: User, db: AsyncSession
) -> Dataset:
    dataset = await db.scalar(
        select(Dataset).where(
            Dataset.id == dataset_id, Dataset.user_id == user.id
        )
    )
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found"
        )
    return dataset


@router.post(
    "", response_model=DatasetRead, status_code=status.HTTP_201_CREATED
)
async def upload_dataset(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are supported",
        )

    contents = await file.read()
    if len(contents) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 50 MB limit",
        )

    # Create the dataset row first so we have an id for the storage path.
    dataset = Dataset(
        user_id=user.id,
        filename=file.filename,
        storage_path="",
        status=DatasetStatus.uploading,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)

    csv_path = storage.original_path(user.id, dataset.id, file.filename)
    csv_path.write_bytes(contents)
    dataset.storage_path = str(csv_path)
    dataset.status = DatasetStatus.profiling
    await db.commit()

    parquet_out = storage.parquet_path(user.id, dataset.id)
    try:
        # pandas is blocking — run off the event loop.
        row_count, col_count, profiles = await asyncio.to_thread(
            ingestion.ingest_csv, csv_path, parquet_out
        )
    except Exception as exc:  # noqa: BLE001 — surface any parse/IO failure to the user
        logger.exception("Ingestion failed for dataset %s", dataset.id)
        dataset.status = DatasetStatus.failed
        dataset.error = str(exc)[:2048]
        await db.commit()
        await db.refresh(dataset)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not process CSV: {exc}",
        )

    dataset.parquet_path = str(parquet_out)
    dataset.row_count = row_count
    dataset.col_count = col_count
    dataset.status = DatasetStatus.ready
    db.add_all(
        [DatasetColumn(dataset_id=dataset.id, **p) for p in profiles]
    )
    await db.commit()
    await db.refresh(dataset)
    logger.info(
        "Dataset %s ready: %d rows x %d cols", dataset.id, row_count, col_count
    )
    return dataset


@router.get("", response_model=list[DatasetRead])
async def list_datasets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.scalars(
        select(Dataset)
        .where(Dataset.user_id == user.id)
        .order_by(Dataset.created_at.desc())
    )
    return list(result)


@router.get("/{dataset_id}", response_model=DatasetRead)
async def get_dataset(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _get_owned_dataset(dataset_id, user, db)


@router.get("/{dataset_id}/profile", response_model=DatasetProfile)
async def get_dataset_profile(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = await db.scalar(
        select(Dataset)
        .where(Dataset.id == dataset_id, Dataset.user_id == user.id)
        .options(selectinload(Dataset.columns))
    )
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found"
        )
    return dataset


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = await _get_owned_dataset(dataset_id, user, db)
    await db.delete(dataset)
    await db.commit()
    storage.remove_dataset_files(user.id, dataset_id)
