"""Clip model — a generated vertical short/reel cut from a SourceVideo."""

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ClipStatus(str, enum.Enum):
    """Processing status of a generated clip."""

    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Clip(Base):
    """A single generated vertical clip belonging to a SourceVideo."""

    __tablename__ = "clips"

    id = Column(Integer, primary_key=True, index=True)
    source_video_id = Column(
        Integer,
        ForeignKey("source_videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    video_path = Column(String(1024), nullable=False)
    caption_text = Column(Text, nullable=True)
    has_broll = Column(Boolean, nullable=False, default=False)
    status = Column(Enum(ClipStatus), nullable=False, default=ClipStatus.queued)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    source_video = relationship("SourceVideo", back_populates="clips")
