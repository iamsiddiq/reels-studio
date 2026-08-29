"""Pydantic schemas for the dashboard stats endpoint."""

from pydantic import BaseModel


class DashboardStats(BaseModel):
    """Aggregate counters shown on the dashboard."""

    videos_processed: int
    clips_generated: int
    storage_used_mb: float
