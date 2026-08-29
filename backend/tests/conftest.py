"""Shared pytest fixtures for the backend test suite.

No live PostgreSQL is available in this sandbox, so every test runs against
a throwaway SQLite database file (one per test), and every external
boundary (yt-dlp, faster-whisper, ffmpeg/subprocess, the background
pipeline dispatch) is mocked or monkeypatched rather than exercised for
real.
"""

from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.clip import Clip, ClipStatus
from app.models.source_video import SourceType, SourceVideo, SourceVideoStatus


@pytest.fixture()
def tmp_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point STORAGE_PATH at a throwaway directory for the duration of a test."""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    monkeypatch.setattr(settings, "STORAGE_PATH", str(storage_dir))
    return storage_dir


@pytest.fixture()
def engine(tmp_path: Path) -> Generator[Engine, None, None]:
    """A SQLite file-backed engine, fresh per test."""
    db_path = tmp_path / "test.db"
    test_engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture()
def session_factory(engine: Engine) -> Callable[[], Session]:
    """A sessionmaker bound to the test engine — usable as a drop-in
    replacement for `app.database.SessionLocal` in pipeline tests."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session(session_factory: Callable[[], Session]) -> Generator[Session, None, None]:
    """A single DB session for setting up/inspecting fixture rows directly."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(
    session_factory: Callable[[], Session], tmp_storage: Path
) -> Generator[TestClient, None, None]:
    """A FastAPI TestClient with `get_db` overridden to use the test database."""

    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def patched_pipeline_dispatch(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Prevent the real download/transcribe/render pipeline from ever running
    off the back of an API call. Records the video_id each dispatch was
    called with instead."""
    calls: list[int] = []

    def fake_process_source_video(video_id: int, factory: Callable[[], Session]) -> None:
        calls.append(video_id)

    monkeypatch.setattr("app.routers.videos.process_source_video", fake_process_source_video)
    return calls


@pytest.fixture()
def make_source_video(
    db_session: Session,
) -> Callable[..., SourceVideo]:
    """Factory fixture for creating a persisted SourceVideo row."""

    def _make(**overrides: object) -> SourceVideo:
        defaults: dict[str, object] = {
            "source_type": SourceType.youtube,
            "source_url": "https://www.youtube.com/watch?v=abc123",
            "title": "Sample Video",
            "status": SourceVideoStatus.queued,
        }
        defaults.update(overrides)
        video = SourceVideo(**defaults)
        db_session.add(video)
        db_session.commit()
        db_session.refresh(video)
        return video

    return _make


@pytest.fixture()
def make_clip(db_session: Session) -> Callable[..., Clip]:
    """Factory fixture for creating a persisted Clip row."""

    def _make(source_video_id: int, **overrides: object) -> Clip:
        defaults: dict[str, object] = {
            "source_video_id": source_video_id,
            "start_time": 0.0,
            "end_time": 20.0,
            "video_path": "/nonexistent/fake_clip.mp4",
            "caption_text": "Hello world",
            "has_broll": False,
            "status": ClipStatus.completed,
        }
        defaults.update(overrides)
        clip = Clip(**defaults)
        db_session.add(clip)
        db_session.commit()
        db_session.refresh(clip)
        return clip

    return _make
