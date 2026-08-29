"""Integration tests for the /api/v1/clips endpoints."""

from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.clip import Clip
from app.models.source_video import SourceVideo


class TestListClips:
    def test_list_all_clips(
        self,
        client: TestClient,
        make_source_video: Callable[..., SourceVideo],
        make_clip: Callable[..., Clip],
    ) -> None:
        video = make_source_video()
        make_clip(video.id, caption_text="first")
        make_clip(video.id, caption_text="second")

        response = client.get("/api/v1/clips")

        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_list_clips_filtered_by_source_video_id(
        self,
        client: TestClient,
        make_source_video: Callable[..., SourceVideo],
        make_clip: Callable[..., Clip],
    ) -> None:
        video_a = make_source_video(title="A")
        video_b = make_source_video(title="B")
        make_clip(video_a.id, caption_text="from a")
        make_clip(video_b.id, caption_text="from b 1")
        make_clip(video_b.id, caption_text="from b 2")

        response = client.get("/api/v1/clips", params={"source_video_id": video_b.id})

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert all(clip["source_video_id"] == video_b.id for clip in body)

    def test_list_clips_empty(self, client: TestClient) -> None:
        response = client.get("/api/v1/clips")
        assert response.status_code == 200
        assert response.json() == []


class TestGetClip:
    def test_get_existing_clip(
        self,
        client: TestClient,
        make_source_video: Callable[..., SourceVideo],
        make_clip: Callable[..., Clip],
    ) -> None:
        video = make_source_video()
        clip = make_clip(video.id, caption_text="hello")

        response = client.get(f"/api/v1/clips/{clip.id}")

        assert response.status_code == 200
        assert response.json()["id"] == clip.id
        assert response.json()["caption_text"] == "hello"

    def test_get_clip_not_found(self, client: TestClient) -> None:
        response = client.get("/api/v1/clips/999999")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"


class TestDownloadClip:
    def test_download_existing_file_succeeds(
        self,
        client: TestClient,
        make_source_video: Callable[..., SourceVideo],
        make_clip: Callable[..., Clip],
        tmp_path: Path,
    ) -> None:
        video = make_source_video()
        real_file = tmp_path / "rendered.mp4"
        real_file.write_bytes(b"fake rendered clip bytes")
        clip = make_clip(video.id, video_path=str(real_file))

        response = client.get(f"/api/v1/clips/{clip.id}/download")

        assert response.status_code == 200
        assert response.content == b"fake rendered clip bytes"
        assert response.headers["content-type"] == "video/mp4"

    def test_download_missing_file_returns_404(
        self,
        client: TestClient,
        make_source_video: Callable[..., SourceVideo],
        make_clip: Callable[..., Clip],
    ) -> None:
        video = make_source_video()
        clip = make_clip(video.id, video_path="/nonexistent/path/does_not_exist.mp4")

        response = client.get(f"/api/v1/clips/{clip.id}/download")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"

    def test_download_clip_row_not_found(self, client: TestClient) -> None:
        response = client.get("/api/v1/clips/999999/download")
        assert response.status_code == 404


class TestDeleteClip:
    def test_delete_removes_row_and_file(
        self,
        client: TestClient,
        make_source_video: Callable[..., SourceVideo],
        make_clip: Callable[..., Clip],
        db_session: Session,
        tmp_path: Path,
    ) -> None:
        video = make_source_video()
        real_file = tmp_path / "to_delete.mp4"
        real_file.write_bytes(b"bytes")
        clip = make_clip(video.id, video_path=str(real_file))
        clip_id = clip.id

        response = client.delete(f"/api/v1/clips/{clip_id}")

        assert response.status_code == 204
        assert not real_file.exists()

        # Roll back the idle transaction left over from fixture setup and
        # drop the (now stale) identity map entry -- Session.get() on an
        # identity-mapped-but-expired instance whose row is gone raises
        # ObjectDeletedError rather than returning None, so query fresh
        # instead, using the id captured above (the ORM object itself is
        # now detached).
        db_session.rollback()
        db_session.expunge_all()
        assert db_session.query(Clip).filter(Clip.id == clip_id).one_or_none() is None

    def test_delete_missing_file_still_removes_row(
        self,
        client: TestClient,
        make_source_video: Callable[..., SourceVideo],
        make_clip: Callable[..., Clip],
        db_session: Session,
    ) -> None:
        video = make_source_video()
        clip = make_clip(video.id, video_path="/nonexistent/already_gone.mp4")
        clip_id = clip.id

        response = client.delete(f"/api/v1/clips/{clip_id}")

        assert response.status_code == 204
        db_session.rollback()
        db_session.expunge_all()
        assert db_session.query(Clip).filter(Clip.id == clip_id).one_or_none() is None

    def test_delete_not_found(self, client: TestClient) -> None:
        response = client.delete("/api/v1/clips/999999")
        assert response.status_code == 404
