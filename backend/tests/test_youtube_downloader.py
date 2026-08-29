"""Unit tests for the yt-dlp-backed YouTube downloader, with yt_dlp mocked out."""

from pathlib import Path
from typing import Any, Self

import pytest
import yt_dlp

from app.config import settings
from app.exceptions import ProcessingError
from app.services.youtube_downloader import download_youtube_video

VALID_URL = "https://www.youtube.com/watch?v=abc123"


class _FakeYoutubeDL:
    """Stand-in for yt_dlp.YoutubeDL that never touches the network."""

    def __init__(self, opts: dict[str, Any], *, info: dict[str, Any], write_file: bool = True) -> None:
        self.opts = opts
        self._info = info
        self._write_file = write_file

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def extract_info(self, url: str, download: bool = True) -> dict[str, Any]:
        if self._write_file:
            out_path = Path(self.prepare_filename(self._info))
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"fake downloaded video")
        return self._info

    def prepare_filename(self, info: dict[str, Any]) -> str:
        template: str = self.opts["outtmpl"]
        return template.replace("%(id)s", str(info["id"])).replace("%(ext)s", str(info["ext"]))


class TestDownloadYoutubeVideo:
    def test_rejects_non_youtube_url(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError, match="does not look like a valid YouTube URL"):
            download_youtube_video("https://example.com/not-youtube", tmp_path)

    def test_successful_download_returns_path_title_duration(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        info = {"id": "abc123", "ext": "mp4", "title": "My Video", "duration": 42.5}

        def fake_ydl_factory(opts: dict[str, Any]) -> _FakeYoutubeDL:
            return _FakeYoutubeDL(opts, info=info)

        monkeypatch.setattr(yt_dlp, "YoutubeDL", fake_ydl_factory)

        file_path, title, duration = download_youtube_video(VALID_URL, tmp_path)

        assert file_path.exists()
        assert file_path.name == "abc123.mp4"
        assert title == "My Video"
        assert duration == 42.5

    def test_falls_back_to_mp4_suffix_when_merge_changes_extension(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # extract_info reports a .webm filename, but only the merged .mp4 exists.
        info = {"id": "xyz789", "ext": "webm", "title": "Merged Video", "duration": 10.0}

        class _MergedYoutubeDL(_FakeYoutubeDL):
            def extract_info(self, url: str, download: bool = True) -> dict[str, Any]:
                mp4_path = Path(self.prepare_filename(self._info)).with_suffix(".mp4")
                mp4_path.parent.mkdir(parents=True, exist_ok=True)
                mp4_path.write_bytes(b"fake merged video")
                return self._info

        monkeypatch.setattr(yt_dlp, "YoutubeDL", lambda opts: _MergedYoutubeDL(opts, info=info))

        file_path, _title, _duration = download_youtube_video(VALID_URL, tmp_path)

        assert file_path.suffix == ".mp4"
        assert file_path.exists()

    def test_yt_dlp_exception_translates_to_processing_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _ExplodingYoutubeDL:
            def __init__(self, opts: dict[str, Any]) -> None:
                pass

            def __enter__(self) -> Self:
                return self

            def __exit__(self, *exc: object) -> None:
                return None

            def extract_info(self, url: str, download: bool = True) -> dict[str, Any]:
                raise RuntimeError("network unreachable")

        monkeypatch.setattr(yt_dlp, "YoutubeDL", _ExplodingYoutubeDL)

        with pytest.raises(ProcessingError, match="Failed to download video"):
            download_youtube_video(VALID_URL, tmp_path)

    def test_missing_output_file_raises_processing_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        info = {"id": "ghost", "ext": "mp4", "title": "Ghost Video", "duration": 5.0}

        monkeypatch.setattr(
            yt_dlp, "YoutubeDL", lambda opts: _FakeYoutubeDL(opts, info=info, write_file=False)
        )

        with pytest.raises(ProcessingError, match="output file is missing"):
            download_youtube_video(VALID_URL, tmp_path)

    def test_accepts_shortened_youtu_be_url(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        info = {"id": "short1", "ext": "mp4", "title": "Short URL Video", "duration": 3.0}
        monkeypatch.setattr(yt_dlp, "YoutubeDL", lambda opts: _FakeYoutubeDL(opts, info=info))

        file_path, _title, _duration = download_youtube_video("https://youtu.be/short1", tmp_path)

        assert file_path.exists()

    def test_uses_cookiefile_when_configured_and_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cookies_path = tmp_path / "cookies.txt"
        cookies_path.write_text("# Netscape HTTP Cookie File\n")
        monkeypatch.setattr(settings, "YT_DLP_COOKIES_FILE", str(cookies_path))

        info = {"id": "cookie1", "ext": "mp4", "title": "Cookie Video", "duration": 1.0}
        captured: dict[str, Any] = {}

        def fake_ydl_factory(opts: dict[str, Any]) -> _FakeYoutubeDL:
            captured["opts"] = opts
            return _FakeYoutubeDL(opts, info=info)

        monkeypatch.setattr(yt_dlp, "YoutubeDL", fake_ydl_factory)

        download_youtube_video(VALID_URL, tmp_path)

        assert captured["opts"]["cookiefile"] == str(cookies_path)

    def test_omits_cookiefile_when_configured_path_does_not_exist(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "YT_DLP_COOKIES_FILE", str(tmp_path / "does_not_exist.txt"))

        info = {"id": "nocookie", "ext": "mp4", "title": "No Cookie Video", "duration": 1.0}
        captured: dict[str, Any] = {}

        def fake_ydl_factory(opts: dict[str, Any]) -> _FakeYoutubeDL:
            captured["opts"] = opts
            return _FakeYoutubeDL(opts, info=info)

        monkeypatch.setattr(yt_dlp, "YoutubeDL", fake_ydl_factory)

        download_youtube_video(VALID_URL, tmp_path)

        assert "cookiefile" not in captured["opts"]
