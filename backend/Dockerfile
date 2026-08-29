# syntax=docker/dockerfile:1
# backend/Dockerfile
# Multi-stage build for the FastAPI video-processing backend.
#
# CRITICAL: the video pipeline (app/services/video_processor.py) shells out
# to the `ffmpeg` binary, and yt-dlp also relies on ffmpeg for post-processing
# downloaded streams. ffmpeg is a system package, NOT a pip package, so it
# must be installed via apt-get in the runtime stage below. Do not remove it.

# ---- Builder stage: compile/install Python dependencies ----
FROM python:3.11-slim AS builder

WORKDIR /app

# gcc/libpq-dev are needed to build psycopg2-binary's transitive deps on some
# platforms; kept only in the builder stage so the final image stays slim.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# --mount=type=cache persists pip's download cache across builds, so a retry
# after a flaky-network timeout resumes instead of redownloading everything.
# --user installs into /root/.local, matching the COPY below into the
# runtime stage (this was previously missing, which would have left the
# runtime image with no Python packages installed at all).
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --timeout=100 --retries=5 -r requirements.txt

# ---- Runtime stage ----
FROM python:3.11-slim AS runtime

WORKDIR /app

# Non-root user
RUN useradd -m -u 1000 appuser

# Bring in the Python packages installed in the builder stage. BuildKit runs
# independent stages concurrently by default; this COPY forces the runtime
# stage to block here until the builder stage's pip install has finished, so
# the apt-get install below (which pulls a surprising number of X11/video
# libs for ffmpeg on Debian) never runs at the same time as pip downloading
# large ML wheels (ctranslate2, av, ...) -- on memory-constrained hosts,
# running both heavy installs at once can exhaust the Docker VM entirely
# ("cannot allocate memory").
COPY --from=builder /root/.local /home/appuser/.local

# ffmpeg: required at runtime for clip cropping/caption burn-in and by
# yt-dlp for muxing downloaded YouTube streams.
# libpq5: runtime shared lib needed by psycopg2-binary.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Application code
COPY ./app ./app
# alembic.ini and alembic/ may not exist yet this early in development; the
# wildcard on alembic.ini keeps the build from failing if it's absent, while
# the migrations directory is expected to exist (even if empty).
COPY alembic.ini* ./
COPY ./alembic ./alembic

# Local storage for downloaded source videos + generated clips (mounted as a
# volume in docker-compose.yml so files persist across container restarts).
RUN mkdir -p /app/storage \
    && chown -R appuser:appuser /app /home/appuser/.local

USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
