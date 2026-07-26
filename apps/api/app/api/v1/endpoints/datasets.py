"""Dataset endpoints: upload a CSV (profiled synchronously for small data),
list/get datasets, fetch the column profile, and delete."""
import asyncio
import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import logger
from app.core.security import get_current_user
from app.models.dataset import Dataset, DatasetStatus
from app.models.dataset_column import DatasetColumn
from app.models.user import User
from app.schemas.dataset import DatasetProfile, DatasetRead, DatasetUpdate
from app.services import ingestion, preprocessing, storage

router = APIRouter()


def _too_large() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        detail=f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit",
    )


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
    request: Request,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are supported",
        )

    # Fail fast on the declared body size before buffering the upload. The
    # header can be absent or wrong, so the post-read check below is the
    # authoritative backstop.
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > settings.max_upload_bytes:
        raise _too_large()

    contents = await file.read()
    if len(contents) > settings.max_upload_bytes:
        raise _too_large()

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
    # Preview what data-cleaning would fix, so the analyze panel can recommend it.
    # A failed audit must never block a successful upload.
    try:
        dataset.preprocessing_summary = (
            await asyncio.to_thread(preprocessing.audit, str(parquet_out))
        ) or None
    except Exception:  # noqa: BLE001
        logger.warning("Preprocess audit failed for dataset %s", dataset.id, exc_info=True)
    await db.commit()
    await db.refresh(dataset)
    logger.info(
        "Dataset %s ready: %d rows x %d cols", dataset.id, row_count, col_count
    )
    return dataset


@router.get("", response_model=list[DatasetRead])
async def list_datasets(
    archived: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.scalars(
        select(Dataset)
        .where(Dataset.user_id == user.id, Dataset.archived == archived)
        .order_by(Dataset.created_at.desc())
    )
    return list(result)


@router.get("/{dataset_id}", response_model=DatasetRead)
async def get_dataset(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = await _get_owned_dataset(dataset_id, user, db)
    # Backfill the cleaning audit for datasets uploaded before this feature (or
    # before the audit was stored). Computed once, then cached on the row.
    if (
        dataset.status == DatasetStatus.ready
        and not dataset.preprocessed
        and dataset.preprocessing_summary is None
        and dataset.parquet_path
    ):
        try:
            dataset.preprocessing_summary = (
                await asyncio.to_thread(preprocessing.audit, dataset.parquet_path)
            ) or []
            await db.commit()
        except Exception:  # noqa: BLE001 — audit is best-effort, never block a read
            logger.warning("Lazy audit failed for dataset %s", dataset.id, exc_info=True)
    return dataset


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


@router.post("/{dataset_id}/preprocess", response_model=DatasetProfile)
async def preprocess_dataset(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Apply safe, report-appropriate cleaning to the dataset IN PLACE: the cleaned
    Parquet replaces the raw one (the original CSV is preserved on disk), columns
    are re-profiled, and reports generated afterwards use the cleaned data."""
    dataset = await _get_owned_dataset(dataset_id, user, db)
    if dataset.status != DatasetStatus.ready or not dataset.parquet_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Dataset is not ready"
        )

    def _run(path: str):
        import pandas as pd

        df = pd.read_parquet(path)
        cleaned, changes = preprocessing.clean_dataframe(df)
        ingestion.write_parquet(cleaned, path)  # overwrite the cache; CSV stays as backup
        profiles = ingestion.profile_dataframe(cleaned)
        return len(cleaned), cleaned.shape[1], profiles, changes

    try:
        row_count, col_count, profiles, changes = await asyncio.to_thread(
            _run, dataset.parquet_path
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Preprocessing failed for dataset %s", dataset.id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not pre-process dataset: {exc}",
        )

    # Replace the column profile with the cleaned one.
    await db.execute(
        delete(DatasetColumn).where(DatasetColumn.dataset_id == dataset.id)
    )
    db.add_all([DatasetColumn(dataset_id=dataset.id, **p) for p in profiles])
    dataset.row_count = row_count
    dataset.col_count = col_count
    dataset.preprocessed = True
    dataset.preprocessing_summary = changes or []
    await db.commit()

    result = await db.scalar(
        select(Dataset)
        .where(Dataset.id == dataset.id)
        .options(selectinload(Dataset.columns))
    )
    logger.info("Dataset %s preprocessed: %d changes", dataset.id, len(changes))
    return result


@router.patch("/{dataset_id}", response_model=DatasetRead)
async def rename_dataset(
    dataset_id: uuid.UUID,
    payload: DatasetUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = await _get_owned_dataset(dataset_id, user, db)
    dataset.filename = payload.filename.strip()
    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.post("/{dataset_id}/archive", response_model=DatasetRead)
async def archive_dataset(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Soft-delete: hide the dataset but keep its data so it can be restored."""
    dataset = await _get_owned_dataset(dataset_id, user, db)
    dataset.archived = True
    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.post("/{dataset_id}/unarchive", response_model=DatasetRead)
async def unarchive_dataset(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = await _get_owned_dataset(dataset_id, user, db)
    dataset.archived = False
    await db.commit()
    await db.refresh(dataset)
    return dataset
