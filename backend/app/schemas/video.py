"""Pydantic schemas for SourceVideo submission and responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.source_video import SourceType, SourceVideoStatus


class SourceVideoCreate(BaseModel):
    """Request body for submitting a YouTube video for processing."""

    source_url: str = Field(..., min_length=1, max_length=2048)

    @field_validator("source_url")
    @classmethod
    def validate_youtube_url(cls, value: str) -> str:
        """Reject anything that doesn't look like a YouTube URL up front."""
        value = value.strip()
        allowed_hosts = (
            "https://www.youtube.com/",
            "https://youtube.com/",
            "https://m.youtube.com/",
            "https://youtu.be/",
            "http://www.youtube.com/",
            "http://youtube.com/",
            "http://m.youtube.com/",
            "http://youtu.be/",
        )
        if not value.startswith(allowed_hosts):
            raise ValueError("source_url must be a valid YouTube URL")
        return value


class SourceVideoResponse(BaseModel):
    """Full representation of a SourceVideo returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: SourceType
    source_url: str | None
    file_path: str | None
    title: str
    duration_seconds: float | None
    status: SourceVideoStatus
    error_message: str | None
    progress_detail: str | None
    created_at: datetime
