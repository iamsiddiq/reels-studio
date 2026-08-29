"""ffmpeg-based rendering: crop a source clip to 9:16 vertical.

All ffmpeg invocations go through `subprocess.run` with an explicit argument
list -- never `shell=True` -- so there is no shell-injection surface even
though clip metadata (file paths) ultimately comes from user-submitted video
titles.
"""

import logging
import subprocess
from pathlib import Path

from app.config import settings
from app.exceptions import ProcessingError

logger = logging.getLogger(__name__)

# Standard vertical short/reel resolution (9:16).
_TARGET_WIDTH = 1080
_TARGET_HEIGHT = 1920

# Hard ceiling on how long a single ffmpeg/ffprobe invocation may run before
# we give up and fail the clip rather than pin a background-task thread forever.
_FFMPEG_TIMEOUT_SECONDS = 600
_FFPROBE_TIMEOUT_SECONDS = 30


def probe_duration_seconds(source_path: Path) -> float:
    """Return the duration (seconds) of the media file at `source_path`.

    Raises:
        ProcessingError: if ffprobe fails, times out, or returns unparsable output.
    """
    cmd = [
        settings.FFPROBE_PATH,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(source_path),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=_FFPROBE_TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired as exc:
        raise ProcessingError(f"ffprobe timed out inspecting {source_path}") from exc

    if result.returncode != 0:
        raise ProcessingError(f"ffprobe failed (exit {result.returncode}): {result.stderr[-2000:]}")

    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise ProcessingError(f"ffprobe returned an unparsable duration: {result.stdout!r}") from exc


def crop_to_vertical(
    source_path: Path,
    start: float,
    end: float,
    output_path: Path,
) -> None:
    """Cut [start, end) out of `source_path`, crop/pad it to 9:16, and write
    the result to `output_path`. No captions are burned in.

    Raises:
        ProcessingError: if the source file is missing, the time range is
            invalid, or the ffmpeg process exits non-zero.
    """
    if not source_path.exists():
        raise ProcessingError(f"Cannot render clip: source file not found: {source_path}")

    duration = end - start
    if duration <= 0:
        raise ProcessingError(f"Invalid clip range: start={start} end={end}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    video_filter = (
        f"scale=w={_TARGET_WIDTH}:h={_TARGET_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={_TARGET_WIDTH}:{_TARGET_HEIGHT}"
    )

    cmd = [
        settings.FFMPEG_PATH,
        "-y",
        "-ss",
        str(start),
        "-i",
        str(source_path),
        "-t",
        str(duration),
        "-vf",
        video_filter,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    logger.info("Rendering clip %s [%.2f-%.2f] -> %s", source_path, start, end, output_path)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=_FFMPEG_TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired as exc:
        raise ProcessingError(f"ffmpeg timed out rendering {output_path}") from exc

    if result.returncode != 0:
        logger.error("ffmpeg failed for %s: %s", output_path, result.stderr)
        raise ProcessingError(f"ffmpeg failed (exit {result.returncode}): {result.stderr[-2000:]}")

    if not output_path.exists():
        raise ProcessingError(f"ffmpeg reported success but output file is missing: {output_path}")

    logger.info("Rendered clip %s", output_path)
