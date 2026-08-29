"""Download a YouTube video to local storage via yt-dlp.

yt-dlp is invoked through its Python API (not a subprocess), so there is no
shell involved here at all. The public helper still validates the URL shape
before doing any network work, and translates any yt-dlp failure into a
`ProcessingError` so callers (the pipeline) don't need to know about yt-dlp
internals.
"""

import logging
import re
from pathlib import Path

from app.config import settings
from app.exceptions import ProcessingError

logger = logging.getLogger(__name__)

_YOUTUBE_URL_RE = re.compile(
    r"^https?://(www\.|m\.)?(youtube\.com/watch\?v=[\w-]+|youtu\.be/[\w-]+|youtube\.com/shorts/[\w-]+)",
    re.IGNORECASE,
)


def _looks_like_youtube_url(url: str) -> bool:
    """Cheap sanity check before shelling out to yt-dlp."""
    return bool(_YOUTUBE_URL_RE.match(url.strip()))


def download_youtube_video(url: str, dest_dir: Path) -> tuple[Path, str, float]:
    """Download `url` into `dest_dir` and return (file_path, title, duration_seconds).

    Raises:
        ProcessingError: if the URL doesn't look like YouTube, or the
            download otherwise fails.
    """
    if not _looks_like_youtube_url(url):
        raise ProcessingError(f"'{url}' does not look like a valid YouTube URL")

    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        import yt_dlp
    except ImportError as exc:  # pragma: no cover - environment issue
        raise ProcessingError(f"yt-dlp is not installed: {exc}") from exc

    output_template = str(dest_dir / "%(id)s.%(ext)s")
    ydl_opts = {
        "outtmpl": output_template,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        # Pin the same ffmpeg binary the rest of the pipeline uses for muxing,
        # instead of silently falling back to whatever "ffmpeg" resolves to on PATH.
        "ffmpeg_location": settings.FFMPEG_PATH,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = Path(ydl.prepare_filename(info))
            # merge_output_format can change the extension after muxing.
            if not file_path.exists():
                candidate = file_path.with_suffix(".mp4")
                if candidate.exists():
                    file_path = candidate
    except Exception as exc:  # yt_dlp raises its own DownloadError subclasses
        logger.error("yt-dlp failed to download %s: %s", url, exc)
        raise ProcessingError(f"Failed to download video: {exc}") from exc

    if not file_path.exists():
        raise ProcessingError(f"yt-dlp reported success but output file is missing: {file_path}")

    title = str(info.get("title") or file_path.stem)
    duration = float(info.get("duration") or 0.0)

    logger.info("Downloaded YouTube video %s -> %s (%.1fs)", url, file_path, duration)
    return file_path, title, duration
