"""Unit tests for ffmpeg-based clip rendering, with subprocess.run mocked out."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.exceptions import ProcessingError
from app.services.video_processor import crop_to_vertical


@pytest.fixture()
def source_file(tmp_path: Path) -> Path:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake video bytes")
    return source


class TestCropToVertical:
    def test_missing_source_file_raises_processing_error(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist.mp4"
        output = tmp_path / "out.mp4"

        with pytest.raises(ProcessingError, match="source file not found"):
            crop_to_vertical(missing, 0.0, 10.0, output)

    def test_invalid_time_range_raises_processing_error(
        self, source_file: Path, tmp_path: Path
    ) -> None:
        output = tmp_path / "out.mp4"

        with pytest.raises(ProcessingError, match="Invalid clip range"):
            crop_to_vertical(source_file, 10.0, 5.0, output)

    def test_calls_subprocess_run_with_arg_list_never_shell(
        self, source_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output = tmp_path / "out.mp4"
        captured: dict[str, object] = {}

        def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
            captured["cmd"] = cmd
            captured["kwargs"] = kwargs
            output.write_bytes(b"fake rendered clip")
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        crop_to_vertical(source_file, 1.0, 11.0, output)

        cmd = captured["cmd"]
        assert isinstance(cmd, list)
        assert all(isinstance(part, str) for part in cmd)
        assert "-ss" in cmd
        assert "1.0" in cmd
        assert "-t" in cmd
        assert "10.0" in cmd
        assert str(source_file) in cmd
        assert str(output) in cmd
        # No caption/subtitle burn-in filter should be present.
        assert not any("subtitles=" in part for part in cmd)

        # Never shell=True, and never invoked via a shell string.
        assert captured["kwargs"].get("shell", False) is not True

    def test_nonzero_returncode_raises_processing_error(
        self, source_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output = tmp_path / "out.mp4"

        def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
            return MagicMock(returncode=1, stdout="", stderr="ffmpeg exploded")

        monkeypatch.setattr(subprocess, "run", fake_run)

        with pytest.raises(ProcessingError, match="ffmpeg failed"):
            crop_to_vertical(source_file, 0.0, 10.0, output)

    def test_success_but_missing_output_file_raises_processing_error(
        self, source_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output = tmp_path / "out.mp4"

        def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
            # Simulate ffmpeg "succeeding" without ever writing the file.
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        with pytest.raises(ProcessingError, match="output file is missing"):
            crop_to_vertical(source_file, 0.0, 10.0, output)
