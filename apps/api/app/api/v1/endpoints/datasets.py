"""Dataset endpoints: upload CSVs or a ZIP of them, watch processing stream in
live over SSE, list/get datasets, fetch the column profile, and delete.

Upload is split so the client can show a real loading screen: POST saves the
raw files fast (real upload progress) and returns the row as `uploading`; the
client then opens GET /{id}/process/stream, which clusters/cleans/profiles the
data and generates report suggestions, emitting a live step for each phase and
flipping the row to `ready` at the end."""
import asyncio
import json
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.agent.context import DatasetContext
from app.agent.streaming import friendly_error_detail
from app.agent.suggestions import suggest_reports
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import logger
from app.core.security import get_current_user
from app.models.dataset import Dataset, DatasetStatus
from app.models.dataset_column import DatasetColumn
from app.models.report_suggestion import ReportSuggestion, SuggestionStatus
from app.models.user import User
from app.schemas.dataset import DatasetProfile, DatasetRead, DatasetUpdate
from app.services import archive, ingestion, preprocessing, storage

router = APIRouter()


# Cap on individually-picked files per upload (a ZIP counts as one file; its
# contents are bounded by settings.MAX_CSV_FILES instead).
_MAX_UPLOAD_FILES = 10


def _too_large() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        detail=f"Upload exceeds the {settings.MAX_UPLOAD_MB} MB limit",
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
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload CSVs — or a ZIP of them — that together form a single dataset.

    A ZIP may hold a whole folder tree; every CSV inside becomes part of the
    dataset, and its folder path is kept in the table name so the AI can lean
    on the structure. This endpoint only validates and persists the raw files
    (fast, so the client's upload progress bar is honest), then returns the row
    as `uploading`. The heavy work — clustering by schema, cleaning, profiling,
    and suggestion generation — runs in GET /{id}/process/stream so the client
    can show it live. A single CSV behaves the same, just streamed.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No file uploaded"
        )
    if len(files) > _MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload at most {_MAX_UPLOAD_FILES} files at once",
        )
    if any(
        not (f.filename or "").lower().endswith((".csv", ".zip")) for f in files
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv and .zip files are supported",
        )

    # Fail fast on the declared body size before buffering the upload. The
    # header can be absent or wrong, so the post-read check below is the
    # authoritative backstop.
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > settings.max_upload_bytes:
        raise _too_large()

    blobs = [await f.read() for f in files]
    if sum(len(b) for b in blobs) > settings.max_upload_bytes:
        raise _too_large()

    names = [f.filename or "upload.csv" for f in files]

    # Expand ZIPs into their CSV members (validated and capped) BEFORE creating
    # the dataset row, so a bad archive never leaves an orphan. Keys are upload
    # indices; plain CSVs ingest straight from their original file.
    zip_members: dict[int, list[tuple[str, bytes]]] = {}
    try:
        for i, (name, blob) in enumerate(zip(names, blobs)):
            if name.lower().endswith(".zip"):
                zip_members[i] = archive.extract_csv_members(blob)
    except archive.ArchiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    csv_count = (len(files) - len(zip_members)) + sum(
        len(m) for m in zip_members.values()
    )
    # Raw files are only ingestion inputs — same-schema files stack into one
    # table, and the LLM-facing bound is settings.MAX_DATASET_TABLES applied
    # after clustering (inside ingest_tables).
    if csv_count > settings.MAX_CSV_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This upload expands to {csv_count} CSV files; the limit "
            f"per dataset is {settings.MAX_CSV_FILES}.",
        )
    if (
        sum(len(b) for ms in zip_members.values() for _, b in ms)
        > settings.max_upload_bytes
    ):
        raise _too_large()

    # A readable name for the combined dataset ("sales_jan.csv +1 more").
    display_name = names[0] if len(names) == 1 else f"{names[0]} +{len(names) - 1} more"

    # Create the dataset row first so we have an id for the storage path.
    dataset = Dataset(
        user_id=user.id,
        filename=display_name[:512],
        storage_path="",
        status=DatasetStatus.uploading,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)

    # Persist each original untouched (kept as a backup even after cleaning). A
    # per-file index keeps same-named uploads from clobbering each other. ZIP
    # members are additionally written out flat as the ingestion sources; their
    # relative path stays in the display name so table names keep the folders.
    dataset_dir = storage.dataset_dir(user.id, dataset.id)
    named_paths: list[tuple[str, str]] = []
    extracted_count = 0
    for i, (name, blob) in enumerate(zip(names, blobs)):
        path = (
            storage.indexed_original_path(user.id, dataset.id, i, name)
            if len(files) > 1
            else storage.original_path(user.id, dataset.id, name)
        )
        path.write_bytes(blob)
        if i == 0:
            dataset.storage_path = str(path)
        if i in zip_members:
            for member_name, content in zip_members[i]:
                member_path = storage.extracted_csv_path(
                    user.id, dataset.id, extracted_count, member_name
                )
                extracted_count += 1
                member_path.write_bytes(content)
                named_paths.append((member_name, str(member_path)))
        else:
            named_paths.append((name, str(path)))

    # Hand the ingestion inputs off to the processing stream. The source count
    # is recorded now so the UI can show it before profiling finishes.
    storage.ingest_manifest_path(user.id, dataset.id).write_text(
        json.dumps({"named_paths": named_paths, "csv_count": csv_count})
    )
    dataset.source_file_count = csv_count
    await db.commit()
    await db.refresh(dataset)
    logger.info(
        "Dataset %s uploaded: %d source CSV(s) saved, awaiting processing",
        dataset.id, csv_count,
    )
    return dataset


def _sse(event: str, payload: dict) -> dict:
    return {"event": event, "data": json.dumps(payload, default=str)}


def _apply_ingest_result(
    dataset: Dataset,
    db: AsyncSession,
    tables_info: list[dict],
    changes: list[dict],
    preprocessed: bool,
    csv_count: int,
) -> None:
    """Write the ingestion outcome onto the dataset row (mirrors what the old
    synchronous upload did once ingest_tables returned)."""
    primary = tables_info[0]
    dataset.parquet_path = primary["parquet_path"]
    dataset.preprocessed = preprocessed
    dataset.preprocessing_summary = changes or []
    # Ingestion summary for the UI: files in, resultant Parquet bytes out.
    dataset.source_file_count = csv_count
    dataset.size_bytes = sum(
        p.stat().st_size
        for t in tables_info
        if (p := Path(t["parquet_path"])).exists()
    )
    if len(tables_info) == 1:
        # Single table — the legacy shape: no tables JSONB, counts from that table.
        dataset.tables = None
        dataset.row_count = primary["row_count"]
        dataset.col_count = primary["col_count"]
    else:
        # Multiple tables queried together; totals span all of them.
        dataset.tables = tables_info
        dataset.row_count = sum(t["row_count"] for t in tables_info)
        dataset.col_count = sum(t["col_count"] for t in tables_info)
    # DatasetColumn rows hold the PRIMARY table (keeps the profile endpoint and
    # single-table assumptions working); per-table columns live in tables JSONB.
    db.add_all(
        [DatasetColumn(dataset_id=dataset.id, **p) for p in primary["columns"]]
    )
    dataset.status = DatasetStatus.ready


@router.get("/{dataset_id}/process/stream")
async def stream_processing(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Run (and stream, live) everything between raw upload and a ready dataset:
    cluster the CSVs into tables, clean + profile them, and generate the first
    batch of report suggestions. Mirrors the report stream's SSE shape.

    Events: `step` ({key, state, label, detail}) for each phase, `done`
    ({dataset_id, row_count, col_count, tables, source_file_count}) when the
    dataset is ready to analyze, or `error` ({detail}) on failure. Re-opening
    the stream after completion just replays `done` (safe on reconnect)."""
    dataset = await _get_owned_dataset(dataset_id, user, db)

    if dataset.status == DatasetStatus.ready:
        async def replay():
            yield _sse("done", {
                "dataset_id": str(dataset.id),
                "row_count": dataset.row_count,
                "col_count": dataset.col_count,
                "tables": len(dataset.tables) if dataset.tables else 1,
                "source_file_count": dataset.source_file_count,
            })
        return EventSourceResponse(replay())

    manifest_path = storage.ingest_manifest_path(user.id, dataset.id)
    if not manifest_path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This upload can't be processed — please upload the file again.",
        )
    manifest = json.loads(manifest_path.read_text())
    named_paths: list[tuple[str, str]] = [tuple(p) for p in manifest["named_paths"]]
    csv_count: int = manifest["csv_count"]
    dataset_dir = storage.dataset_dir(user.id, dataset.id)

    async def event_generator():
        # A retried stream (e.g. after a transient failure) starts clean.
        dataset.status = DatasetStatus.profiling
        dataset.error = None
        await db.commit()

        # Bridge the blocking ingest's thread-side progress callback onto this
        # event loop's queue, then relay each item as an SSE `step`.
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def on_progress(key: str, state: str, label: str, detail: str | None) -> None:
            loop.call_soon_threadsafe(
                queue.put_nowait,
                _sse("step", {"key": key, "state": state, "label": label, "detail": detail}),
            )

        try:
            task = asyncio.create_task(
                asyncio.to_thread(
                    ingestion.ingest_tables, named_paths, str(dataset_dir),
                    on_progress,
                )
            )
            while not task.done() or not queue.empty():
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=0.2)
                except asyncio.TimeoutError:
                    continue
            tables_info, changes, preprocessed = await task

            _apply_ingest_result(dataset, db, tables_info, changes, preprocessed, csv_count)
            await db.commit()
            await db.refresh(dataset)

            # Generate the first batch of report ideas so the analyze page lands
            # ready — unless some already exist (a re-run of this stream).
            existing = await db.scalar(
                select(ReportSuggestion.id).where(
                    ReportSuggestion.dataset_id == dataset.id,
                    ReportSuggestion.user_id == user.id,
                ).limit(1)
            )
            if existing is None:
                yield _sse("step", {"key": "ideas", "state": "active",
                                    "label": "Generating report ideas", "detail": None})
                columns = list(await db.scalars(
                    select(DatasetColumn)
                    .where(DatasetColumn.dataset_id == dataset.id)
                    .order_by(DatasetColumn.position)
                ))
                ctx = DatasetContext.from_models(dataset, columns)
                ideas = await suggest_reports(ctx, use_purpose=user.use_purpose)
                db.add_all([
                    ReportSuggestion(
                        user_id=user.id, dataset_id=dataset.id,
                        title=i["title"], question=i["question"],
                        rationale=i["rationale"], chart_types=i["chart_types"],
                        status=SuggestionStatus.suggested,
                    )
                    for i in ideas
                ])
                await db.commit()
                yield _sse("step", {"key": "ideas", "state": "done",
                                    "label": "Generating report ideas",
                                    "detail": f"{len(ideas)} ready"})

            manifest_path.unlink(missing_ok=True)
            logger.info(
                "Dataset %s ready: %d rows x %d cols across %d table(s)",
                dataset.id, dataset.row_count, dataset.col_count, len(tables_info),
            )
            yield _sse("done", {
                "dataset_id": str(dataset.id),
                "row_count": dataset.row_count,
                "col_count": dataset.col_count,
                "tables": len(tables_info),
                "source_file_count": csv_count,
            })
        except ingestion.TooManyTablesError as exc:
            # User-facing message — pass through without parse-failure framing.
            dataset.status = DatasetStatus.failed
            dataset.error = str(exc)[:2048]
            await db.commit()
            yield _sse("error", {"detail": str(exc)})
        except Exception as exc:  # noqa: BLE001 — surface any failure to the client
            logger.exception("Processing failed for dataset %s", dataset.id)
            detail = friendly_error_detail(exc)
            dataset.status = DatasetStatus.failed
            dataset.error = detail[:2048]
            await db.commit()
            yield _sse("error", {"detail": detail})

    return EventSourceResponse(event_generator())


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

    try:
        row_count, col_count, profiles, changes = await asyncio.to_thread(
            preprocessing.apply_cleaning, dataset.parquet_path
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
