"""Audio transcription via faster-whisper.

The whisper model is expensive to load (it pulls weights into memory), so we
keep a single lazily-initialized module-level instance and reuse it across
calls instead of reloading it per request/pipeline run.
"""

import logging
from pathlib import Path
from threading import Lock
from typing import Any

from app.config import settings
from app.exceptions import ProcessingError

logger = logging.getLogger(__name__)

_model: Any = None
_model_lock = Lock()


def _get_model() -> Any:
    """Return the cached WhisperModel, creating it on first use."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                try:
                    from faster_whisper import WhisperModel
                except ImportError as exc:  # pragma: no cover - environment issue
                    raise ProcessingError(f"faster-whisper is not installed: {exc}") from exc
                logger.info("Loading faster-whisper model '%s'", settings.WHISPER_MODEL)
                _model = WhisperModel(settings.WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


def transcribe(file_path: Path) -> list[dict]:
    """Transcribe the audio/video at `file_path` into timestamped segments.

    Returns:
        A list of `{"start": float, "end": float, "text": str}` dicts, in
        chronological order.

    Raises:
        ProcessingError: if the file is missing or transcription fails.
    """
    if not file_path.exists():
        raise ProcessingError(f"Cannot transcribe: file not found: {file_path}")

    model = _get_model()

    try:
        segments_iter, _info = model.transcribe(str(file_path), vad_filter=True)
        segments = [
            {"start": float(segment.start), "end": float(segment.end), "text": segment.text.strip()}
            for segment in segments_iter
        ]
    except Exception as exc:
        logger.error("Transcription failed for %s: %s", file_path, exc)
        raise ProcessingError(f"Transcription failed: {exc}") from exc

    logger.info("Transcribed %s into %d segments", file_path, len(segments))
    return segments
