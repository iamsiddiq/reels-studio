"""Integration tests for the /api/v1/videos endpoints.

The real download/transcribe/render pipeline never runs here -- the
`patched_pipeline_dispatch` fixture replaces `process_source_video` with a
no-op that just records which video id it was asked to process.
"""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.models.source_video import SourceVideo, SourceVideoStatus

VALID_YOUTUBE_URL = "https://www.youtube.com/watch?v=abc123"


class TestSubmitYoutubeVideo:
    def test_valid_youtube_url_creates_queued_video(
        self, client: TestClient, patched_pipeline_dispatch: list[int]
    ) -> None:
        response = client.post("/api/v1/videos", json={"source_url": VALID_YOUTUBE_URL})

        assert response.status_code == 201
        body = response.json()
        assert body["source_type"] == "youtube"
        assert body["source_url"] == VALID_YOUTUBE_URL
        assert body["status"] == "queued"
        assert isinstance(body["id"], int)

        assert patched_pipeline_dispatch == [body["id"]]

    def test_invalid_url_is_rejected_before_any_row_is_created(
        self, client: TestClient, patched_pipeline_dispatch: list[int]
    ) -> None:
        response = client.post("/api/v1/videos", json={"source_url": "https://example.com/not-youtube"})

        assert response.status_code == 422
        assert patched_pipeline_dispatch == []

    def test_missing_source_url_is_rejected(self, client: TestClient) -> None:
        response = client.post("/api/v1/videos", json={})
        assert response.status_code == 422


class TestUploadVideo:
    def test_valid_video_upload_saves_file_and_creates_queued_video(
        self,
        client: TestClient,
        patched_pipeline_dispatch: list[int],
        tmp_storage: Path,
    ) -> None:
        response = client.post(
            "/api/v1/videos/upload",
            files={"file": ("clip.mp4", b"fake video bytes", "video/mp4")},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["source_type"] == "upload"
        assert body["status"] == "queued"
        assert body["file_path"] is not None

        saved_path = Path(body["file_path"])
        assert saved_path.exists()
        assert saved_path.read_bytes() == b"fake video bytes"
        assert str(tmp_storage) in str(saved_path)

        assert patched_pipeline_dispatch == [body["id"]]

    def test_rejects_non_video_content_type(
        self, client: TestClient, patched_pipeline_dispatch: list[int]
    ) -> None:
        response = client.post(
            "/api/v1/videos/upload",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )

        assert response.status_code == 422
        assert patched_pipeline_dispatch == []

    def test_rejects_upload_exceeding_max_size(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 0 MB effectively means "anything is too big".
        monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 0)

        response = client.post(
            "/api/v1/videos/upload",
            files={"file": ("clip.mp4", b"x" * 2048, "video/mp4")},
        )

        assert response.status_code == 422

    def test_rejects_empty_upload(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/videos/upload",
            files={"file": ("empty.mp4", b"", "video/mp4")},
        )

        assert response.status_code == 422


class TestListAndGetVideos:
    def test_list_videos_returns_all_newest_first(
        self, client: TestClient, make_source_video: Callable[..., SourceVideo]
    ) -> None:
        # SQLite's CURRENT_TIMESTAMP has only whole-second resolution, so two
        # rows created back-to-back could otherwise tie -- set explicit,
        # clearly-ordered timestamps instead of relying on wall-clock timing.
        now = datetime.now(timezone.utc)
        older = make_source_video(title="Older", created_at=now - timedelta(minutes=5))
        newer = make_source_video(title="Newer", created_at=now)

        response = client.get("/api/v1/videos")

        assert response.status_code == 200
        ids = [row["id"] for row in response.json()]
        assert ids.index(newer.id) < ids.index(older.id)

    def test_list_videos_empty(self, client: TestClient) -> None:
        response = client.get("/api/v1/videos")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_video_by_id(
        self, client: TestClient, make_source_video: Callable[..., SourceVideo]
    ) -> None:
        video = make_source_video(title="My Video")

        response = client.get(f"/api/v1/videos/{video.id}")

        assert response.status_code == 200
        assert response.json()["id"] == video.id
        assert response.json()["title"] == "My Video"

    def test_get_video_not_found(self, client: TestClient) -> None:
        response = client.get("/api/v1/videos/999999")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"


class TestVideoStatus:
    def test_get_status_for_existing_video(
        self, client: TestClient, make_source_video: Callable[..., SourceVideo]
    ) -> None:
        video = make_source_video(status=SourceVideoStatus.processing, progress_detail="Transcribing audio")

        response = client.get(f"/api/v1/videos/{video.id}/status")

        assert response.status_code == 200
        assert response.json() == {
            "status": "processing",
            "error_message": None,
            "progress_detail": "Transcribing audio",
        }

    def test_get_status_not_found(self, client: TestClient) -> None:
        response = client.get("/api/v1/videos/999999/status")
        assert response.status_code == 404


class TestRegenerateVideo:
    def test_regenerate_resets_failed_video_to_queued(
        self,
        client: TestClient,
        make_source_video: Callable[..., SourceVideo],
        patched_pipeline_dispatch: list[int],
    ) -> None:
        video = make_source_video(status=SourceVideoStatus.failed, error_message="boom")

        response = client.post(f"/api/v1/videos/{video.id}/generate")

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "queued"
        assert body["error_message"] is None
        assert patched_pipeline_dispatch == [video.id]

    def test_regenerate_not_found(
        self, client: TestClient, patched_pipeline_dispatch: list[int]
    ) -> None:
        response = client.post("/api/v1/videos/999999/generate")
        assert response.status_code == 404
        assert patched_pipeline_dispatch == []

    def test_regenerate_rejects_video_already_in_flight(
        self,
        client: TestClient,
        make_source_video: Callable[..., SourceVideo],
        patched_pipeline_dispatch: list[int],
    ) -> None:
        for in_flight_status in (
            SourceVideoStatus.queued,
            SourceVideoStatus.downloading,
            SourceVideoStatus.processing,
        ):
            video = make_source_video(status=in_flight_status)

            response = client.post(f"/api/v1/videos/{video.id}/generate")

            assert response.status_code == 409
            assert patched_pipeline_dispatch == []
