"""Highlight-window selection from a transcript.

Two selection strategies:
  - LLM (OpenAI): reads the full transcript and picks the actual most
    interesting moments (hooks, punchlines, insights) via a JSON-mode chat
    completion. Used whenever `settings.OPENAI_API_KEY` is configured.
  - Heuristic fallback: a local word-count/sentence-density scoring function,
    used when no API key is configured or the OpenAI call fails for any
    reason, so the pipeline never hard-fails just because highlight
    selection had a bad day.

Either strategy only decides *window boundaries* -- the burned-in caption
text for a chosen window is always derived from the real transcript
(`_window_text`), never authored by the LLM, so captions stay in sync with
the actual spoken audio.
"""

import json
import logging
import re
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_SENTENCE_END_RE = re.compile(r"[.!?]")


def _window_text(segments: list[dict]) -> str:
    return " ".join(seg["text"].strip() for seg in segments if seg["text"].strip())


def _overlaps(a: dict, b: dict) -> bool:
    return a["start"] < b["end"] and b["start"] < a["end"]


def _segments_in_window(segments: list[dict], start: float, end: float) -> list[dict]:
    return [seg for seg in segments if seg["start"] < end and seg["end"] > start]


# --------------------------------------------------------------------------
# Heuristic fallback (word-count / sentence-density scoring)
# --------------------------------------------------------------------------


def _score_window(segments: list[dict], duration: float) -> float:
    """Score a candidate window: denser speech (more words, more sentence
    boundaries per second) scores higher, as a rough proxy for "eventful"."""
    if duration <= 0:
        return 0.0
    text = _window_text(segments)
    word_count = len(text.split())
    sentence_count = len(_SENTENCE_END_RE.findall(text))
    density = sentence_count / duration
    return word_count * (1.0 + density)


def _build_candidates(segments: list[dict], min_duration: float, max_duration: float) -> list[dict]:
    """Generate candidate (start, end, segments) windows made of consecutive
    segments whose total duration falls within [min_duration, max_duration]."""
    candidates = []
    n = len(segments)
    for i in range(n):
        window_segments: list[dict] = []
        start = segments[i]["start"]
        for j in range(i, n):
            window_segments.append(segments[j])
            end = segments[j]["end"]
            duration = end - start
            if duration > max_duration:
                break
            if duration >= min_duration:
                candidates.append(
                    {
                        "start": start,
                        "end": end,
                        "segments": list(window_segments),
                        "duration": duration,
                    }
                )
    return candidates


def _fallback_single_clip(segments: list[dict], max_duration: float) -> list[dict]:
    start = segments[0]["start"]
    end = min(segments[-1]["end"], start + max_duration)
    fallback_segments = _segments_in_window(segments, start, end)
    return [{"start": start, "end": end, "caption_text": _window_text(fallback_segments)}]


def _heuristic_detect_highlights(
    segments: list[dict], max_clips: int, min_duration: float, max_duration: float
) -> list[dict]:
    candidates = _build_candidates(segments, min_duration, max_duration)

    if not candidates:
        # Transcript is shorter than min_duration end-to-end (or segments are
        # sparse) -- fall back to a single clip covering everything we have,
        # capped at max_duration, rather than returning nothing.
        logger.info("No candidate windows met duration bounds; using fallback single clip")
        return _fallback_single_clip(segments, max_duration)

    for candidate in candidates:
        candidate["score"] = _score_window(candidate["segments"], candidate["duration"])

    candidates.sort(key=lambda c: c["score"], reverse=True)

    selected: list[dict] = []
    for candidate in candidates:
        if len(selected) >= max_clips:
            break
        if any(_overlaps(candidate, chosen) for chosen in selected):
            continue
        selected.append(candidate)

    selected.sort(key=lambda c: c["start"])

    logger.info("Selected %d highlight window(s) via heuristic from %d segment(s)", len(selected), len(segments))
    return [
        {"start": c["start"], "end": c["end"], "caption_text": _window_text(c["segments"])} for c in selected
    ]


# --------------------------------------------------------------------------
# LLM-based selection (OpenAI)
# --------------------------------------------------------------------------


def _format_transcript_for_prompt(segments: list[dict]) -> str:
    lines = [
        f"[{seg['start']:.1f}-{seg['end']:.1f}] {seg['text'].strip()}"
        for seg in segments
        if seg["text"].strip()
    ]
    return "\n".join(lines)


def _call_openai_for_highlights(
    segments: list[dict], max_clips: int, min_duration: float, max_duration: float
) -> list[dict] | None:
    """Ask OpenAI to pick highlight windows.

    Returns a list of raw (untrusted) `{"start": ..., "end": ...}` dicts that
    the caller must validate/clamp against the real transcript bounds, or
    `None` if the call could not be completed for any reason (missing
    package, missing/invalid API key, network error, malformed response).
    """
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not installed; falling back to heuristic highlight detection")
        return None

    transcript = _format_transcript_for_prompt(segments)
    prompt = (
        "You are selecting short-form highlight clips from a video transcript, to be "
        "repurposed into YouTube Shorts / TikTok / Instagram Reels.\n\n"
        f"Pick up to {max_clips} non-overlapping highlight windows from the transcript below. "
        f"Each window must be between {min_duration:.0f} and {max_duration:.0f} seconds long, "
        "measured using the timestamps given. Choose moments that are genuinely engaging on "
        "their own: hooks, punchlines, surprising claims, actionable tips, emotional peaks, or "
        "strong opinions -- not just the busiest chatter.\n\n"
        'Respond with strict JSON only, no prose: {"highlights": [{"start": <seconds>, '
        '"end": <seconds>}, ...]}\n\n'
        f"Transcript (timestamps in seconds):\n{transcript}"
    )

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        raw_highlights = data.get("highlights", [])
        if not isinstance(raw_highlights, list):
            raise TypeError(f"Expected 'highlights' to be a list, got {type(raw_highlights).__name__}")
        return raw_highlights
    except Exception as exc:  # noqa: BLE001 - any failure here should degrade, not crash the pipeline
        logger.warning("OpenAI highlight selection failed, falling back to heuristic: %s", exc)
        return None


def _validate_llm_highlights(
    raw_highlights: list[Any],
    segments: list[dict],
    max_clips: int,
    min_duration: float,
    max_duration: float,
) -> list[dict]:
    """Defensively clamp/validate LLM output against the real transcript
    bounds before trusting it -- a model can hallucinate timestamps outside
    the video, overlapping windows, or malformed durations."""
    transcript_start = segments[0]["start"]
    transcript_end = segments[-1]["end"]

    candidates: list[dict] = []
    for item in raw_highlights:
        try:
            start = max(float(item["start"]), transcript_start)
            end = min(float(item["end"]), transcript_end)
        except (KeyError, TypeError, ValueError):
            continue

        if start >= end:
            continue

        end = min(end, start + max_duration)
        duration = end - start

        # Give the model some slack rather than rejecting outright on a
        # slightly-off duration, but don't accept wildly out-of-bounds windows.
        if duration < min_duration * 0.5 or duration > max_duration * 1.5:
            continue

        candidates.append({"start": start, "end": end})

    selected: list[dict] = []
    for candidate in sorted(candidates, key=lambda c: c["start"]):
        if len(selected) >= max_clips:
            break
        if any(_overlaps(candidate, chosen) for chosen in selected):
            continue
        selected.append(candidate)

    return [
        {
            "start": c["start"],
            "end": c["end"],
            "caption_text": _window_text(_segments_in_window(segments, c["start"], c["end"])),
        }
        for c in selected
    ]


# --------------------------------------------------------------------------
# Public entrypoint
# --------------------------------------------------------------------------


def detect_highlights(
    segments: list[dict],
    max_clips: int = 4,
    min_duration: float = 15.0,
    max_duration: float = 60.0,
) -> list[dict]:
    """Pick up to `max_clips` non-overlapping highlight windows from `segments`.

    Uses OpenAI to semantically pick the best moments when
    `settings.OPENAI_API_KEY` is configured, falling back to a local
    word-density heuristic if no key is set or the API call fails.

    Returns:
        A list of `{"start": float, "end": float, "caption_text": str}`
        dicts, ordered by start time.
    """
    if not segments:
        return []

    if settings.OPENAI_API_KEY:
        raw_highlights = _call_openai_for_highlights(segments, max_clips, min_duration, max_duration)
        if raw_highlights:
            validated = _validate_llm_highlights(raw_highlights, segments, max_clips, min_duration, max_duration)
            if validated:
                logger.info("Selected %d highlight window(s) via OpenAI", len(validated))
                return validated
            logger.warning("OpenAI returned no valid highlight windows; falling back to heuristic")

    return _heuristic_detect_highlights(segments, max_clips, min_duration, max_duration)
