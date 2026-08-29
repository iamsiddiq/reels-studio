"""Unit tests for the faster-whisper-backed transcription service.

The whisper model is never actually loaded here -- both the module-level
model cache and any faster_whisper internals are monkeypatched out.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.exceptions import ProcessingError
from app.services import transcription


class _FakeSegment:
    def __init__(self, start: float, end: float, text: str) -> None:
        self.start = start
        self.end = end
        self.text = text


@pytest.fixture(autouse=True)
def _reset_model_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts from a clean (unloaded) model cache."""
    monkeypatch.setattr(transcription, "_model", None)


@pytest.fixture()
def media_file(tmp_path: Path) -> Path:
    path = tmp_path / "audio.mp4"
    path.write_bytes(b"fake media bytes")
    return path


class TestTranscribe:
    def test_missing_file_raises_processing_error(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing.mp4"

        with pytest.raises(ProcessingError, match="file not found"):
            transcription.transcribe(missing)

    def test_returns_timestamped_segments(
        self, media_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_segments = [
            _FakeSegment(0.0, 2.5, "  Hello world  "),
            _FakeSegment(2.5, 5.0, "Goodbye."),
        ]
        fake_model = MagicMock()
        fake_model.transcribe.return_value = (iter(fake_segments), MagicMock())
        monkeypatch.setattr(transcription, "_get_model", lambda: fake_model)

        result = transcription.transcribe(media_file)

        assert result == [
            {"start": 0.0, "end": 2.5, "text": "Hello world"},
            {"start": 2.5, "end": 5.0, "text": "Goodbye."},
        ]
        fake_model.transcribe.assert_called_once_with(str(media_file), vad_filter=True)

    def test_transcription_exception_translates_to_processing_error(
        self, media_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_model = MagicMock()
        fake_model.transcribe.side_effect = RuntimeError("boom")
        monkeypatch.setattr(transcription, "_get_model", lambda: fake_model)

        with pytest.raises(ProcessingError, match="Transcription failed"):
            transcription.transcribe(media_file)

    def test_empty_segments_returns_empty_list(
        self, media_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_model = MagicMock()
        fake_model.transcribe.return_value = (iter([]), MagicMock())
        monkeypatch.setattr(transcription, "_get_model", lambda: fake_model)

        assert transcription.transcribe(media_file) == []


class TestGetModel:
    def test_loads_and_caches_model_instance(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_model_instance = MagicMock()
        fake_model_cls = MagicMock(return_value=fake_model_instance)

        import faster_whisper

        monkeypatch.setattr(faster_whisper, "WhisperModel", fake_model_cls)

        first = transcription._get_model()
        second = transcription._get_model()

        assert first is fake_model_instance
        assert second is fake_model_instance
        fake_model_cls.assert_called_once()

    def test_missing_faster_whisper_translates_to_processing_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import builtins

        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "faster_whisper":
                raise ImportError("no faster_whisper installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        with pytest.raises(ProcessingError, match="faster-whisper is not installed"):
            transcription._get_model()
