"""Pydantic schemas for Clip responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.clip import ClipStatus


class ClipResponse(BaseModel):
    """Full representation of a generated Clip returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source_video_id: int
    start_time: float
    end_time: float
    video_path: str
    caption_text: str | None
    has_broll: bool
    status: ClipStatus
    created_at: datetime
