"""Integration tests for the /api/v1/dashboard/stats endpoint."""

from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient

from app.models.clip import Clip
from app.models.source_video import SourceVideo


class TestDashboardStats:
    def test_stats_are_zero_with_no_data(self, client: TestClient) -> None:
        response = client.get("/api/v1/dashboard/stats")

        assert response.status_code == 200
        assert response.json() == {
            "videos_processed": 0,
            "clips_generated": 0,
            "storage_used_mb": 0.0,
        }

    def test_stats_reflect_seeded_counts(
        self,
        client: TestClient,
        make_source_video: Callable[..., SourceVideo],
        make_clip: Callable[..., Clip],
    ) -> None:
        video_a = make_source_video(title="A")
        video_b = make_source_video(title="B")
        make_clip(video_a.id)
        make_clip(video_a.id)
        make_clip(video_b.id)

        response = client.get("/api/v1/dashboard/stats")

        assert response.status_code == 200
        body = response.json()
        assert body["videos_processed"] == 2
        assert body["clips_generated"] == 3

    def test_storage_used_mb_reflects_files_under_storage_path(
        self,
        client: TestClient,
        tmp_storage: Path,
    ) -> None:
        (tmp_storage / "clips").mkdir()
        (tmp_storage / "clips" / "one.mp4").write_bytes(b"x" * (1024 * 1024))  # exactly 1 MB

        response = client.get("/api/v1/dashboard/stats")

        assert response.status_code == 200
        assert response.json()["storage_used_mb"] == 1.0
