"""Aggregate stats endpoint for the dashboard page."""

import logging
from pathlib import Path

from fastapi import APIRouter

from app.config import settings
from app.dependencies import DbSession
from app.models.clip import Clip
from app.models.source_video import SourceVideo
from app.schemas.dashboard import DashboardStats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _storage_used_mb() -> float:
    """Best-effort sum of file sizes under STORAGE_PATH, in MB. Returns 0 if
    the storage directory doesn't exist yet or cannot be read."""
    storage_path = Path(settings.STORAGE_PATH)
    if not storage_path.exists():
        return 0.0

    total_bytes = 0
    try:
        for file_path in storage_path.rglob("*"):
            if file_path.is_file():
                try:
                    total_bytes += file_path.stat().st_size
                except OSError:
                    continue
    except OSError as exc:
        logger.warning("Failed to compute storage usage under %s: %s", storage_path, exc)
        return 0.0

    return round(total_bytes / (1024 * 1024), 2)


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: DbSession) -> DashboardStats:
    """Return counts of videos/clips processed and total storage used."""
    videos_processed = db.query(SourceVideo).count()
    clips_generated = db.query(Clip).count()
    storage_used_mb = _storage_used_mb()

    return DashboardStats(
        videos_processed=videos_processed,
        clips_generated=clips_generated,
        storage_used_mb=storage_used_mb,
    )
