"""SourceVideo model — a user-submitted long-form video (YouTube or upload)."""

import enum

from sqlalchemy import Column, DateTime, Enum, Float, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SourceType(str, enum.Enum):
    """Where the source video came from."""

    youtube = "youtube"
    upload = "upload"


class SourceVideoStatus(str, enum.Enum):
    """Processing status of a source video."""

    queued = "queued"
    downloading = "downloading"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class SourceVideo(Base):
    """A long-form video submitted for clip generation."""

    __tablename__ = "source_videos"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(Enum(SourceType), nullable=False)
    source_url = Column(String(2048), nullable=True)
    file_path = Column(String(1024), nullable=True)
    title = Column(String(255), nullable=False)
    duration_seconds = Column(Float, nullable=True)
    status = Column(
        Enum(SourceVideoStatus), nullable=False, default=SourceVideoStatus.queued
    )
    error_message = Column(String(2048), nullable=True)
    # Coarse human-readable progress within `status="processing"` (e.g.
    # "Transcribing audio", "Rendering clip 2/4"). Cleared on completion.
    progress_detail = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    clips = relationship(
        "Clip", back_populates="source_video", cascade="all, delete-orphan"
    )
