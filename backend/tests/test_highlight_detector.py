"""Unit tests for the heuristic and OpenAI-backed highlight-window selectors."""

from itertools import pairwise

import pytest

from app.services import highlight_detector
from app.services.highlight_detector import detect_highlights


def _segment(start: float, end: float, text: str) -> dict:
    return {"start": start, "end": end, "text": text}


class TestDetectHighlightsEmptyInput:
    def test_empty_segments_returns_empty_list(self) -> None:
        assert detect_highlights([]) == []


class TestDetectHighlightsShortInput:
    def test_transcript_shorter_than_min_duration_falls_back_to_single_clip(self) -> None:
        # Total span is only 5 seconds -- well under the 15s default min_duration.
        segments = [
            _segment(0.0, 2.0, "Hello there."),
            _segment(2.0, 5.0, "General Kenobi."),
        ]

        highlights = detect_highlights(segments, min_duration=15.0, max_duration=60.0)

        assert len(highlights) == 1
        clip = highlights[0]
        assert clip["start"] == 0.0
        assert clip["end"] == 5.0
        assert "Hello there." in clip["caption_text"]
        assert "General Kenobi." in clip["caption_text"]

    def test_fallback_clip_is_capped_at_max_duration(self) -> None:
        segments = [_segment(0.0, 100.0, "One very long single segment.")]

        highlights = detect_highlights(segments, min_duration=15.0, max_duration=60.0)

        assert len(highlights) == 1
        assert highlights[0]["start"] == 0.0
        assert highlights[0]["end"] == 60.0


class TestDetectHighlightsMaxClips:
    def _long_transcript(self, num_segments: int) -> list[dict]:
        """Build `num_segments` consecutive 10s segments, each independently
        satisfying min_duration=15 in pairs, so many candidate windows exist."""
        segments = []
        t = 0.0
        for i in range(num_segments):
            segments.append(_segment(t, t + 10.0, f"Segment number {i} has some words in it!"))
            t += 10.0
        return segments

    def test_respects_max_clips(self) -> None:
        segments = self._long_transcript(20)  # 200s of content, plenty of candidate windows

        highlights = detect_highlights(segments, max_clips=3, min_duration=15.0, max_duration=30.0)

        assert len(highlights) <= 3

    def test_respects_min_and_max_duration_bounds(self) -> None:
        segments = self._long_transcript(20)

        highlights = detect_highlights(segments, max_clips=5, min_duration=15.0, max_duration=30.0)

        for clip in highlights:
            duration = clip["end"] - clip["start"]
            assert 15.0 <= duration <= 30.0

    def test_selected_windows_are_non_overlapping(self) -> None:
        segments = self._long_transcript(20)

        highlights = detect_highlights(segments, max_clips=5, min_duration=15.0, max_duration=30.0)

        ordered = sorted(highlights, key=lambda c: c["start"])
        for prev, nxt in pairwise(ordered):
            assert prev["end"] <= nxt["start"]

    def test_results_are_ordered_by_start_time(self) -> None:
        segments = self._long_transcript(20)

        highlights = detect_highlights(segments, max_clips=5, min_duration=15.0, max_duration=30.0)

        starts = [clip["start"] for clip in highlights]
        assert starts == sorted(starts)

    def test_more_segments_than_max_clips_still_caps_output(self) -> None:
        segments = self._long_transcript(50)

        highlights = detect_highlights(segments, max_clips=2, min_duration=15.0, max_duration=20.0)

        assert len(highlights) <= 2


class TestDetectHighlightsWithoutApiKey:
    def test_openai_never_called_when_no_api_key_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(highlight_detector.settings, "OPENAI_API_KEY", None)

        def fail_if_called(*args: object, **kwargs: object) -> None:
            raise AssertionError("OpenAI should not be called when no API key is configured")

        monkeypatch.setattr(highlight_detector, "_call_openai_for_highlights", fail_if_called)

        segments = [_segment(0.0, 2.0, "Hello there."), _segment(2.0, 5.0, "General Kenobi.")]
        highlights = detect_highlights(segments)

        assert len(highlights) == 1
        assert highlights[0]["start"] == 0.0


class TestDetectHighlightsWithOpenAI:
    def _transcript(self) -> list[dict]:
        return [
            _segment(0.0, 10.0, "This is the boring intro."),
            _segment(10.0, 25.0, "Here is the surprising punchline everyone loves."),
            _segment(25.0, 40.0, "Some more filler content follows here."),
        ]

    def test_uses_openai_result_when_valid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(highlight_detector.settings, "OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr(
            highlight_detector,
            "_call_openai_for_highlights",
            lambda segments, max_clips, min_duration, max_duration: [{"start": 10.0, "end": 25.0}],
        )

        highlights = detect_highlights(self._transcript(), max_clips=4, min_duration=10.0, max_duration=30.0)

        assert len(highlights) == 1
        assert highlights[0]["start"] == 10.0
        assert highlights[0]["end"] == 25.0
        assert "punchline" in highlights[0]["caption_text"]

    def test_falls_back_to_heuristic_when_openai_call_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(highlight_detector.settings, "OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr(
            highlight_detector,
            "_call_openai_for_highlights",
            lambda *args, **kwargs: None,
        )

        segments = self._transcript()
        via_public_api = detect_highlights(segments, max_clips=4, min_duration=10.0, max_duration=30.0)
        via_heuristic_directly = highlight_detector._heuristic_detect_highlights(segments, 4, 10.0, 30.0)

        assert via_public_api == via_heuristic_directly

    def test_falls_back_to_heuristic_when_openai_returns_no_valid_highlights(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(highlight_detector.settings, "OPENAI_API_KEY", "sk-test")
        # Wildly out-of-bounds timestamps -- should all be rejected by validation.
        monkeypatch.setattr(
            highlight_detector,
            "_call_openai_for_highlights",
            lambda *args, **kwargs: [{"start": 9999.0, "end": 10050.0}],
        )

        segments = self._transcript()
        via_public_api = detect_highlights(segments, max_clips=4, min_duration=10.0, max_duration=30.0)
        via_heuristic_directly = highlight_detector._heuristic_detect_highlights(segments, 4, 10.0, 30.0)

        assert via_public_api == via_heuristic_directly


class TestValidateLlmHighlights:
    def _transcript(self) -> list[dict]:
        return [
            _segment(0.0, 10.0, "First part."),
            _segment(10.0, 20.0, "Second part."),
            _segment(20.0, 30.0, "Third part."),
            _segment(30.0, 40.0, "Fourth part."),
        ]

    def test_clamps_start_and_end_to_transcript_bounds(self) -> None:
        segments = self._transcript()
        raw = [{"start": -50.0, "end": 500.0}]

        validated = highlight_detector._validate_llm_highlights(raw, segments, max_clips=4, min_duration=5.0, max_duration=15.0)

        assert len(validated) == 1
        assert validated[0]["start"] == 0.0
        assert validated[0]["end"] == 15.0  # clamped to start + max_duration

    def test_drops_malformed_entries(self) -> None:
        segments = self._transcript()
        raw = [{"start": "not-a-number", "end": 10.0}, {"end": 10.0}, {"start": 5.0}]

        validated = highlight_detector._validate_llm_highlights(raw, segments, max_clips=4, min_duration=5.0, max_duration=15.0)

        assert validated == []

    def test_dedupes_overlapping_windows(self) -> None:
        segments = self._transcript()
        raw = [{"start": 0.0, "end": 10.0}, {"start": 5.0, "end": 15.0}]

        validated = highlight_detector._validate_llm_highlights(raw, segments, max_clips=4, min_duration=5.0, max_duration=15.0)

        assert len(validated) == 1

    def test_drops_start_after_end(self) -> None:
        segments = self._transcript()
        raw = [{"start": 20.0, "end": 10.0}]

        validated = highlight_detector._validate_llm_highlights(raw, segments, max_clips=4, min_duration=5.0, max_duration=15.0)

        assert validated == []
