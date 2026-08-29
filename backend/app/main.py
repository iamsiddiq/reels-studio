"""FastAPI application entrypoint.

No authentication/authorization is configured anywhere in this app — this
build has no login/signup/protected routes by design.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.exceptions import register_exception_handlers
from app.routers.clips import router as clips_router
from app.routers.dashboard import router as dashboard_router
from app.routers.videos import router as videos_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

# --- Module routers ---
app.include_router(videos_router, prefix="/api/v1")
app.include_router(clips_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    """Simple liveness check used by Docker/CI and manual smoke tests."""
    return {"status": "ok"}
