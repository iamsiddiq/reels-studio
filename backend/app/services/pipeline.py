"""End-to-end clip-generation pipeline orchestrator.

Meant to be dispatched as a FastAPI `BackgroundTasks` job, so it opens its
own DB session (via the passed-in session factory) rather than reusing the
request-scoped session, which is closed by the time the background task
runs.
"""

import logging
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import ProcessingError
from app.models.clip import Clip, ClipStatus
from app.models.source_video import SourceType, SourceVideo, SourceVideoStatus
from app.services import highlight_detector, transcription, video_processor
from app.services.youtube_downloader import download_youtube_video

logger = logging.getLogger(__name__)


def process_source_video(video_id: int, db_session_factory: Callable[[], Session]) -> None:
    """Run the full download -> transcribe -> detect -> render pipeline for
    the SourceVideo with id `video_id`.

    Any exception raised during processing is caught and recorded on the
    SourceVideo row (status="failed", error_message=...) rather than
    propagated, since this runs detached from the original request.
    """
    db = db_session_factory()
    try:
        video = db.get(SourceVideo, video_id)
        if video is None:
            logger.error("process_source_video: SourceVideo %s not found", video_id)
            return

        try:
            _run_pipeline(db, video)
        except Exception as exc:
            logger.error("Pipeline failed for SourceVideo %s: %s", video_id, exc, exc_info=exc)
            db.rollback()
            video = db.get(SourceVideo, video_id)
            if video is not None:
                video.status = SourceVideoStatus.failed
                video.error_message = str(exc)[:2048]
                db.commit()
    finally:
        db.close()


def _run_pipeline(db: Session, video: SourceVideo) -> None:
    clips_dir = Path(settings.STORAGE_PATH) / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    # --- Stage 1: acquire the source file ---
    video.status = SourceVideoStatus.downloading
    video.progress_detail = "Downloading source video" if video.source_type == SourceType.youtube else "Reading uploaded file"
    db.commit()

    if video.source_type == SourceType.youtube:
        downloads_dir = Path(settings.STORAGE_PATH) / "downloads"
        file_path, title, duration = download_youtube_video(video.source_url or "", downloads_dir)
        video.file_path = str(file_path)
        video.title = title or video.title
        video.duration_seconds = duration
        db.commit()
    else:
        if not video.file_path:
            raise ValueError("Uploaded SourceVideo is missing file_path")
        file_path = Path(video.file_path)
        video.duration_seconds = video_processor.probe_duration_seconds(file_path)
        db.commit()

    if (video.duration_seconds or 0) > settings.MAX_VIDEO_DURATION_SECONDS:
        raise ProcessingError(
            f"Video duration {video.duration_seconds:.0f}s exceeds the "
            f"maximum of {settings.MAX_VIDEO_DURATION_SECONDS:.0f}s"
        )

    # --- Stage 2: transcribe + detect highlights + render clips ---
    video.status = SourceVideoStatus.processing
    video.progress_detail = "Transcribing audio"
    db.commit()

    segments = transcription.transcribe(file_path)

    video.progress_detail = "Selecting highlights"
    db.commit()
    highlights = highlight_detector.detect_highlights(segments)

    if not highlights:
        logger.warning("No highlights detected for SourceVideo %s", video.id)

    total = len(highlights)
    for index, highlight in enumerate(highlights):
        video.progress_detail = f"Rendering clip {index + 1}/{total}"
        db.commit()

        output_path = clips_dir / f"{video.id}_{index}.mp4"
        clip = Clip(
            source_video_id=video.id,
            start_time=highlight["start"],
            end_time=highlight["end"],
            video_path=str(output_path),
            caption_text=highlight["caption_text"],
            has_broll=False,
            status=ClipStatus.processing,
        )
        db.add(clip)
        db.commit()
        db.refresh(clip)

        try:
            video_processor.crop_to_vertical(
                source_path=file_path,
                start=highlight["start"],
                end=highlight["end"],
                output_path=output_path,
            )
            clip.status = ClipStatus.completed
        except Exception as exc:  # noqa: BLE001 - isolate one bad clip from the rest
            logger.error("Failed to render clip %s for SourceVideo %s: %s", index, video.id, exc)
            clip.status = ClipStatus.failed
        db.commit()

    video.status = SourceVideoStatus.completed
    video.progress_detail = None
    db.commit()
