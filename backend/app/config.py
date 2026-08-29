"""Application settings, loaded from environment variables / .env file.

This build has NO authentication and NO payments — there is intentionally
no SECRET_KEY, JWT, or OAuth configuration here.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration.

    Values are read from environment variables first, falling back to the
    `.env` file in the backend/ working directory, then to the defaults
    declared below.
    """

    APP_NAME: str = "Shorts/Reels Maker"

    # --- Database ---
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/shorts_reels_maker"

    # --- Storage ---
    # Local directory for downloaded source videos and generated clips.
    STORAGE_PATH: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 500

    # --- Video processing ---
    FFMPEG_PATH: str = "/usr/bin/ffmpeg"
    FFPROBE_PATH: str = "/usr/bin/ffprobe"
    WHISPER_MODEL: str = "base"
    # Reject source videos longer than this before transcription/rendering,
    # since both are O(duration) CPU work with no queue/concurrency cap yet.
    MAX_VIDEO_DURATION_SECONDS: float = 2400.0  # 40 minutes

    # --- Highlight selection (OpenAI) ---
    # When set, highlight_detector.py uses OpenAI to semantically pick the
    # best moments from the transcript instead of the local word-density
    # heuristic. Transcription itself always stays on local faster-whisper.
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # --- Background jobs (optional; MVP uses FastAPI BackgroundTasks) ---
    REDIS_URL: str | None = None

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # `extra="ignore"`: the repo-root .env is shared with docker-compose (POSTGRES_*,
    # VITE_API_URL, etc.) and isn't meant to be an exhaustive whitelist of backend
    # settings — unknown keys should be ignored rather than crashing Settings().
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> str | list[str]:
        """Allow CORS_ORIGINS to be set as a comma-separated string in .env."""
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
