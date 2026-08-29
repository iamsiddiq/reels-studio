"""BRollAsset model — a stock or user-uploaded B-roll clip (post-MVP wiring)."""

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class BRollAsset(Base):
    """A B-roll video asset that can be inserted into generated clips."""

    __tablename__ = "broll_assets"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255), nullable=False, index=True)
    file_path = Column(String(1024), nullable=False)
    source = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
