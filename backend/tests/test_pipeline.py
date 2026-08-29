"""Unit tests for the end-to-end pipeline orchestrator (`process_source_video`
/ `_run_pipeline`). Every external boundary (download, transcribe, highlight
detection, ffmpeg rendering) is monkeypatched -- only the SQLite-backed
SourceVideo/Clip rows are real."""

from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import pytest
from sqlalchemy.orm import Session

from app.models.clip import Clip, ClipStatus
from app.models.source_video import SourceType, SourceVideo, SourceVideoStatus
from app.services import pipeline

T = TypeVar("T")


def _dedupe_consecutive(values: list[T]) -> list[T]:
    result: list[T] = []
    for value in values:
        if not result or result[-1] != value:
            result.append(value)
    return result


def _refresh(db_session: Session, video_id: int) -> SourceVideo | None:
    """Read back the current state of a SourceVideo written by a *different*
    session (the pipeline's own session, opened via a fresh factory call).

    `db_session` may be holding an idle transaction opened while seeding
    fixtures (e.g. from `make_source_video`'s `db.refresh(...)` call); under
    SQLite's rollback-journal mode that idle transaction pins a stale
    snapshot, so it must be rolled back before re-querying to observe writes
    committed by the other session.
    """
    db_session.rollback()
    return db_session.get(SourceVideo, video_id)


@pytest.fixture()
def status_log_factory(
    session_factory: Callable[[], Session],
) -> tuple[Callable[[int], Callable[[], Session]], list[str], list[str | None]]:
    """Builds a session factory that, given a video_id, records that video's
    status and progress_detail (as read back through the very session doing
    the commits) after every commit -- letting tests assert the order of
    status transitions and the progress messages shown alongside them."""
    log: list[str] = []
    progress_log: list[str | None] = []

    def make_factory(video_id: int) -> Callable[[], Session]:
        def spy_factory() -> Session:
            session = session_factory()
            original_commit = session.commit

            def commit_and_log() -> None:
                original_commit()
                video = session.get(SourceVideo, video_id)
                if video is not None:
                    log.append(video.status.value)
                    progress_log.append(video.progress_detail)

            session.commit = commit_and_log  # type: ignore[method-assign]
            return session

        return spy_factory

    return make_factory, log, progress_log


class TestProcessSourceVideoSuccess:
    def test_youtube_video_transitions_through_expected_statuses(
        self,
        make_source_video: Callable[..., SourceVideo],
        db_session: Session,
        status_log_factory: tuple[Callable[[int], Callable[[], Session]], list[str], list[str | None]],
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        video = make_source_video(source_type=SourceType.youtube)
        make_factory, log, progress_log = status_log_factory

        fake_downloaded = tmp_path / "downloaded.mp4"
        fake_downloaded.write_bytes(b"fake")

        monkeypatch.setattr(
            pipeline, "download_youtube_video", lambda url, dest_dir: (fake_downloaded, "Real Title", 123.4)
        )
        monkeypatch.setattr(pipeline.transcription, "transcribe", lambda path: [{"start": 0.0, "end": 20.0, "text": "hi"}])
        monkeypatch.setattr(
            pipeline.highlight_detector,
            "detect_highlights",
            lambda segments: [
                {"start": 0.0, "end": 10.0, "caption_text": "clip one"},
                {"start": 10.0, "end": 20.0, "caption_text": "clip two"},
            ],
        )
        monkeypatch.setattr(pipeline.video_processor, "crop_to_vertical", lambda **kwargs: None)

        pipeline.process_source_video(video.id, make_factory(video.id))

        refreshed = _refresh(db_session, video.id)
        assert refreshed is not None
        assert refreshed.status == SourceVideoStatus.completed
        assert refreshed.title == "Real Title"
        assert refreshed.duration_seconds == 123.4
        assert refreshed.file_path == str(fake_downloaded)

        clips = db_session.query(Clip).filter(Clip.source_video_id == video.id).order_by(Clip.start_time).all()
        assert len(clips) == 2
        assert clips[0].caption_text == "clip one"
        assert clips[0].status == ClipStatus.completed
        assert clips[1].caption_text == "clip two"
        assert clips[1].status == ClipStatus.completed

        assert _dedupe_consecutive(log) == ["downloading", "processing", "completed"]
        assert _dedupe_consecutive(progress_log) == [
            "Downloading source video",
            "Transcribing audio",
            "Selecting highlights",
            "Rendering clip 1/2",
            "Rendering clip 2/2",
            None,
        ]
        assert refreshed.progress_detail is None

    def test_upload_source_never_invokes_downloader(
        self,
        make_source_video: Callable[..., SourceVideo],
        db_session: Session,
        session_factory: Callable[[], Session],
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        source_file = tmp_path / "uploaded.mp4"
        source_file.write_bytes(b"fake upload")
        video = make_source_video(source_type=SourceType.upload, source_url=None, file_path=str(source_file))

        def fail_if_called(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError("download_youtube_video should not be called for uploads")

        monkeypatch.setattr(pipeline, "download_youtube_video", fail_if_called)
        monkeypatch.setattr(pipeline.video_processor, "probe_duration_seconds", lambda path: 20.0)
        monkeypatch.setattr(pipeline.transcription, "transcribe", lambda path: [{"start": 0.0, "end": 20.0, "text": "hi"}])
        monkeypatch.setattr(
            pipeline.highlight_detector,
            "detect_highlights",
            lambda segments: [{"start": 0.0, "end": 15.0, "caption_text": "only clip"}],
        )
        monkeypatch.setattr(pipeline.video_processor, "crop_to_vertical", lambda **kwargs: None)

        pipeline.process_source_video(video.id, session_factory)

        refreshed = _refresh(db_session, video.id)
        assert refreshed is not None
        assert refreshed.status == SourceVideoStatus.completed
        assert refreshed.duration_seconds == 20.0

    def test_no_highlights_detected_still_completes_with_no_clips(
        self,
        make_source_video: Callable[..., SourceVideo],
        db_session: Session,
        session_factory: Callable[[], Session],
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        fake_downloaded = tmp_path / "downloaded.mp4"
        fake_downloaded.write_bytes(b"fake")
        video = make_source_video(source_type=SourceType.youtube)

        monkeypatch.setattr(pipeline, "download_youtube_video", lambda url, dest_dir: (fake_downloaded, "T", 1.0))
        monkeypatch.setattr(pipeline.transcription, "transcribe", lambda path: [])
        monkeypatch.setattr(pipeline.highlight_detector, "detect_highlights", lambda segments: [])

        pipeline.process_source_video(video.id, session_factory)

        refreshed = _refresh(db_session, video.id)
        assert refreshed is not None
        assert refreshed.status == SourceVideoStatus.completed
        assert db_session.query(Clip).filter(Clip.source_video_id == video.id).count() == 0

    def test_video_exceeding_max_duration_fails_before_transcription(
        self,
        make_source_video: Callable[..., SourceVideo],
        db_session: Session,
        session_factory: Callable[[], Session],
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        fake_downloaded = tmp_path / "downloaded.mp4"
        fake_downloaded.write_bytes(b"fake")
        video = make_source_video(source_type=SourceType.youtube)

        monkeypatch.setattr(
            pipeline, "download_youtube_video", lambda url, dest_dir: (fake_downloaded, "T", 999_999.0)
        )

        def fail_if_called(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError("transcribe should not run for an over-limit video")

        monkeypatch.setattr(pipeline.transcription, "transcribe", fail_if_called)

        pipeline.process_source_video(video.id, session_factory)

        refreshed = _refresh(db_session, video.id)
        assert refreshed is not None
        assert refreshed.status == SourceVideoStatus.failed
        assert refreshed.error_message is not None
        assert "exceeds the maximum" in refreshed.error_message


class TestProcessSourceVideoPerClipFailureIsolation:
    def test_one_failed_clip_render_does_not_abort_the_others(
        self,
        make_source_video: Callable[..., SourceVideo],
        db_session: Session,
        session_factory: Callable[[], Session],
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        fake_downloaded = tmp_path / "downloaded.mp4"
        fake_downloaded.write_bytes(b"fake")
        video = make_source_video(source_type=SourceType.youtube)

        monkeypatch.setattr(pipeline, "download_youtube_video", lambda url, dest_dir: (fake_downloaded, "T", 1.0))
        monkeypatch.setattr(pipeline.transcription, "transcribe", lambda path: [{"start": 0.0, "end": 20.0, "text": "hi"}])
        monkeypatch.setattr(
            pipeline.highlight_detector,
            "detect_highlights",
            lambda segments: [
                {"start": 0.0, "end": 10.0, "caption_text": "will fail"},
                {"start": 10.0, "end": 20.0, "caption_text": "will succeed"},
            ],
        )

        call_count = {"n": 0}

        def flaky_render(**kwargs: Any) -> None:
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("ffmpeg exploded on this one clip")

        monkeypatch.setattr(pipeline.video_processor, "crop_to_vertical", flaky_render)

        pipeline.process_source_video(video.id, session_factory)

        refreshed = _refresh(db_session, video.id)
        assert refreshed is not None
        assert refreshed.status == SourceVideoStatus.completed  # pipeline still completes overall

        clips = db_session.query(Clip).filter(Clip.source_video_id == video.id).order_by(Clip.start_time).all()
        assert len(clips) == 2
        assert clips[0].status == ClipStatus.failed
        assert clips[1].status == ClipStatus.completed


class TestProcessSourceVideoPipelineFailure:
    def test_pipeline_exception_marks_video_failed_with_error_message(
        self,
        make_source_video: Callable[..., SourceVideo],
        db_session: Session,
        session_factory: Callable[[], Session],
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        fake_downloaded = tmp_path / "downloaded.mp4"
        fake_downloaded.write_bytes(b"fake")
        video = make_source_video(source_type=SourceType.youtube)

        monkeypatch.setattr(pipeline, "download_youtube_video", lambda url, dest_dir: (fake_downloaded, "T", 1.0))

        def exploding_transcribe(path: Path) -> list[dict]:
            raise RuntimeError("transcription boom")

        monkeypatch.setattr(pipeline.transcription, "transcribe", exploding_transcribe)

        pipeline.process_source_video(video.id, session_factory)

        refreshed = _refresh(db_session, video.id)
        assert refreshed is not None
        assert refreshed.status == SourceVideoStatus.failed
        assert refreshed.error_message is not None
        assert "transcription boom" in refreshed.error_message

    def test_missing_video_id_returns_without_raising(
        self, session_factory: Callable[[], Session]
    ) -> None:
        # No row with this id exists -- process_source_video should just log
        # and return, never raise.
        pipeline.process_source_video(999_999, session_factory)

    def test_upload_source_missing_file_path_marks_failed(
        self,
        make_source_video: Callable[..., SourceVideo],
        db_session: Session,
        session_factory: Callable[[], Session],
    ) -> None:
        video = make_source_video(source_type=SourceType.upload, source_url=None, file_path=None)

        pipeline.process_source_video(video.id, session_factory)

        refreshed = _refresh(db_session, video.id)
        assert refreshed is not None
        assert refreshed.status == SourceVideoStatus.failed
        assert refreshed.error_message is not None
