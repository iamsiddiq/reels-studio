"""Endpoints for submitting source videos (YouTube URL or file upload) and
tracking/re-triggering their clip-generation pipeline run."""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, UploadFile, status

from app.config import settings
from app.database import SessionLocal
from app.dependencies import DbSession
from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.source_video import SourceType, SourceVideo, SourceVideoStatus
from app.schemas.video import SourceVideoCreate, SourceVideoResponse
from app.services.pipeline import process_source_video

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["videos"])

_ALLOWED_UPLOAD_CONTENT_TYPE_PREFIX = "video/"


def _dispatch_pipeline(background_tasks: BackgroundTasks, video_id: int) -> None:
    """Schedule the processing pipeline to run after the response is sent,
    using its own DB session (SessionLocal), not the request-scoped one."""
    background_tasks.add_task(process_source_video, video_id, SessionLocal)


@router.post("", response_model=SourceVideoResponse, status_code=status.HTTP_201_CREATED)
async def submit_video(
    payload: SourceVideoCreate,
    background_tasks: BackgroundTasks,
    db: DbSession,
) -> SourceVideo:
    """Submit a YouTube URL for clip generation."""
    video = SourceVideo(
        source_type=SourceType.youtube,
        source_url=payload.source_url,
        title=payload.source_url,
        status=SourceVideoStatus.queued,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    _dispatch_pipeline(background_tasks, video.id)
    logger.info("Queued YouTube video %s for processing (id=%s)", payload.source_url, video.id)
    return video


@router.post("/upload", response_model=SourceVideoResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    db: DbSession,
) -> SourceVideo:
    """Upload a video file directly for clip generation."""
    if not file.content_type or not file.content_type.startswith(_ALLOWED_UPLOAD_CONTENT_TYPE_PREFIX):
        raise ValidationError(f"Unsupported content type: {file.content_type}")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    uploads_dir = Path(settings.STORAGE_PATH) / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    original_suffix = Path(file.filename or "").suffix or ".mp4"
    dest_path = uploads_dir / f"{uuid.uuid4().hex}{original_suffix}"

    size = 0
    try:
        with dest_path.open("wb") as dest_file:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise ValidationError(
                        f"Upload exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB"
                    )
                dest_file.write(chunk)
    except ValidationError:
        dest_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    if size == 0:
        dest_path.unlink(missing_ok=True)
        raise ValidationError("Uploaded file is empty")

    video = SourceVideo(
        source_type=SourceType.upload,
        source_url=None,
        file_path=str(dest_path),
        title=file.filename or dest_path.name,
        status=SourceVideoStatus.queued,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    _dispatch_pipeline(background_tasks, video.id)
    logger.info("Queued uploaded video %s for processing (id=%s)", dest_path, video.id)
    return video


@router.get("", response_model=list[SourceVideoResponse])
async def list_videos(db: DbSession) -> list[SourceVideo]:
    """List all submitted source videos, newest first."""
    return db.query(SourceVideo).order_by(SourceVideo.created_at.desc()).all()


@router.get("/{video_id}", response_model=SourceVideoResponse)
async def get_video(video_id: int, db: DbSession) -> SourceVideo:
    """Get a single source video's details."""
    video = db.get(SourceVideo, video_id)
    if video is None:
        raise NotFoundError("SourceVideo")
    return video


@router.post("/{video_id}/generate", response_model=SourceVideoResponse, status_code=status.HTTP_202_ACCEPTED)
async def regenerate_video(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: DbSession,
) -> SourceVideo:
    """Re-trigger the clip-generation pipeline for an existing video (e.g.
    after a previous run failed)."""
    video = db.get(SourceVideo, video_id)
    if video is None:
        raise NotFoundError("SourceVideo")

    if video.status in (SourceVideoStatus.queued, SourceVideoStatus.downloading, SourceVideoStatus.processing):
        raise ConflictError(
            f"SourceVideo {video_id} is already {video.status.value} — wait for it to finish "
            "before re-triggering the pipeline"
        )

    video.status = SourceVideoStatus.queued
    video.error_message = None
    db.commit()
    db.refresh(video)

    _dispatch_pipeline(background_tasks, video.id)
    logger.info("Re-queued SourceVideo %s for processing", video_id)
    return video


@router.get("/{video_id}/status")
async def get_video_status(video_id: int, db: DbSession) -> dict[str, str | None]:
    """Lightweight polling endpoint for the current processing status."""
    video = db.get(SourceVideo, video_id)
    if video is None:
        raise NotFoundError("SourceVideo")
    return {
        "status": video.status.value,
        "error_message": video.error_message,
        "progress_detail": video.progress_detail,
    }
