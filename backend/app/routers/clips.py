"""Endpoints for browsing, downloading, and deleting generated clips."""

import logging
from pathlib import Path

from fastapi import APIRouter, Query, status
from fastapi.responses import FileResponse

from app.dependencies import DbSession
from app.exceptions import NotFoundError
from app.models.clip import Clip
from app.schemas.clip import ClipResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clips", tags=["clips"])


@router.get("", response_model=list[ClipResponse])
async def list_clips(
    db: DbSession,
    source_video_id: int | None = Query(default=None),
) -> list[Clip]:
    """List all clips, optionally filtered by source_video_id."""
    query = db.query(Clip)
    if source_video_id is not None:
        query = query.filter(Clip.source_video_id == source_video_id)
    return query.order_by(Clip.created_at.desc()).all()


@router.get("/{clip_id}", response_model=ClipResponse)
async def get_clip(clip_id: int, db: DbSession) -> Clip:
    """Get a single clip's details."""
    clip = db.get(Clip, clip_id)
    if clip is None:
        raise NotFoundError("Clip")
    return clip


@router.get("/{clip_id}/download")
async def download_clip(clip_id: int, db: DbSession) -> FileResponse:
    """Stream the rendered clip file for download."""
    clip = db.get(Clip, clip_id)
    if clip is None:
        raise NotFoundError("Clip")

    file_path = Path(clip.video_path)
    if not file_path.exists():
        raise NotFoundError("Clip file")

    filename = f"clip_{clip.id}{file_path.suffix or '.mp4'}"
    return FileResponse(path=file_path, media_type="video/mp4", filename=filename)


@router.delete("/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clip(clip_id: int, db: DbSession) -> None:
    """Delete a clip's DB row and its file on disk (best-effort file removal)."""
    clip = db.get(Clip, clip_id)
    if clip is None:
        raise NotFoundError("Clip")

    file_path = Path(clip.video_path)
    try:
        file_path.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Failed to remove clip file %s: %s", file_path, exc)

    db.delete(clip)
    db.commit()
