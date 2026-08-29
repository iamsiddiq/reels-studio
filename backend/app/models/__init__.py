"""SQLAlchemy models for the Shorts/Reels Maker.

This build has NO authentication and NO User model — only video-pipeline
tables are defined here.
"""

from app.database import Base
from app.models.broll_asset import BRollAsset
from app.models.clip import Clip, ClipStatus
from app.models.source_video import SourceType, SourceVideo, SourceVideoStatus

__all__ = [
    "BRollAsset",
    "Base",
    "Clip",
    "ClipStatus",
    "SourceType",
    "SourceVideo",
    "SourceVideoStatus",
]
