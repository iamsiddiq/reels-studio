# CLAUDE.md - Shorts/Reels Maker Project Rules

> Project-specific rules for Claude Code. This file is read automatically.

---

## Project Overview

**Project Name:** Shorts/Reels Maker
**Description:** Converts long-form videos (via YouTube URL or upload) into multiple short-form vertical clips with auto-detected highlights and (post-MVP) B-roll insertion.

**Tech Stack:**
- Backend: FastAPI + Python 3.11+
- Frontend: React + Vite + TypeScript
- Database: PostgreSQL + SQLAlchemy
- Auth: None (no login/signup for MVP — single-user app)
- UI: Tailwind + shadcn/ui
- Video processing: ffmpeg, yt-dlp, faster-whisper (or similar STT)
- Background jobs: Celery + Redis (or FastAPI BackgroundTasks for MVP)

---

## Project Structure

```
shorts-reels-maker/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── source_video.py
│   │   │   ├── clip.py
│   │   │   └── broll_asset.py
│   │   ├── schemas/
│   │   ├── routers/
│   │   │   ├── videos.py
│   │   │   ├── clips.py
│   │   │   ├── dashboard.py
│   │   │   ├── analytics.py     # post-MVP
│   │   │   └── admin.py         # post-MVP
│   │   ├── services/
│   │   │   ├── youtube_downloader.py   # yt-dlp wrapper
│   │   │   ├── transcription.py        # speech-to-text
│   │   │   ├── highlight_detector.py   # segment scoring
│   │   │   ├── video_processor.py      # ffmpeg crop/caption/broll
│   │   │   └── jobs.py                 # background pipeline orchestration
│   │   └── auth/                # unused for MVP — no auth
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   │   ├── NewVideo.tsx
│   │   │   ├── Processing.tsx
│   │   │   ├── Library.tsx
│   │   │   ├── ClipDetail.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Analytics.tsx    # post-MVP
│   │   │   └── Admin.tsx        # post-MVP
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── context/
│   │   └── types/
│   └── package.json
├── .claude/
│   └── commands/
├── skills/
├── agents/
└── PRPs/
```

---

## Code Standards

### Python (Backend)
```python
# ALWAYS use type hints
def get_clip(db: Session, clip_id: int) -> Clip:
    pass

# ALWAYS add docstrings for public functions
def generate_clips(db: Session, video: SourceVideo) -> list[Clip]:
    """
    Run the highlight-detection + clipping pipeline for a source video.

    Args:
        db: Database session
        video: The source video to process

    Returns:
        List of created Clip objects
    """
    pass
```

### TypeScript (Frontend)
```typescript
// ALWAYS define interfaces for props and data
interface ClipProps {
  id: number;
  videoPath: string;
  captionText: string;
  status: "queued" | "processing" | "completed" | "failed";
}

// NO any types allowed
const fetchClip = async (id: number): Promise<Clip> => {
  // ...
};
```

---

## Forbidden Patterns

### Backend
- ❌ Never use `print()` — use `logging` module
- ❌ Never hardcode secrets — use environment variables
- ❌ Never use `SELECT *` — specify columns
- ❌ Never skip input validation (especially on YouTube URLs and uploaded files)
- ❌ Never run ffmpeg/yt-dlp with unsanitized user input passed to shell commands (use subprocess arg lists, never `shell=True` with interpolated strings)
- ❌ Never block the request/response cycle on video processing — always dispatch to a background job

### Frontend
- ❌ Never use `any` type
- ❌ Never leave `console.log` in production
- ❌ Never skip error handling in async operations
- ❌ Never use inline styles — use Tailwind

---

## Module-Specific Rules

### Video Input
- Validate YouTube URLs against expected domain/format before passing to `yt-dlp`
- Enforce upload file size and MIME-type restrictions (video formats only)
- `SourceVideo.status` must be one of: `queued`, `downloading`, `processing`, `completed`, `failed`

### Clip Generation
- All clips must belong to a `SourceVideo` (`source_video_id` foreign key)
- `Clip.status` must be one of: `queued`, `processing`, `completed`, `failed`
- Vertical crop target is 9:16. No burned-in captions — clips are rendered without subtitles; `Clip.caption_text` is stored only as transcript metadata for the library UI, not composited into the video
- B-roll insertion (`has_broll`) is post-MVP — gate behind a feature flag/config, don't block MVP clip generation on it

### Clip Library
- Clip downloads must stream the file, not load it fully into memory
- Deleting a clip must also remove its file from storage

---

## API Conventions

- All endpoints prefixed with `/api/v1/`
- Use plural nouns for resources: `/videos`, `/clips`
- Return appropriate HTTP status codes:
  - 200: Success
  - 201: Created
  - 400: Bad Request
  - 404: Not Found
  - 409: Conflict
  - 422: Processing/validation failure (e.g., unsupported video format)

---

## Authentication

None for MVP — this is a single-user/local-use app with no login, signup, or protected routes. Do not add auth scaffolding unless explicitly requested later.

---

## Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/shorts_reels_maker

# Storage
STORAGE_PATH=./storage
MAX_UPLOAD_SIZE_MB=500

# Video processing
FFMPEG_PATH=/usr/bin/ffmpeg
WHISPER_MODEL=base

# Background jobs (if using Celery)
REDIS_URL=redis://localhost:6379/0

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## Development Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Docker (must include ffmpeg + yt-dlp in the image)
docker-compose up -d

# Tests
pytest backend/tests -v
cd frontend && npm test

# Linting
ruff check backend/
cd frontend && npm run lint
```

---

## Commit Message Format

```
feat([module]): add [feature]
fix([module]): fix [bug]
refactor([module]): refactor [component]
test([module]): add tests for [feature]
docs: update [documentation]
```

---

## Skills Reference

| Task | Skill to Read |
|------|---------------|
| Database models | skills/DATABASE.md |
| API + Auth | skills/BACKEND.md |
| React + UI | skills/FRONTEND.md |
| Testing | skills/TESTING.md |
| Deployment | skills/DEPLOYMENT.md |

---

## Agent Coordination

For complex tasks, the ORCHESTRATOR coordinates:
- DATABASE-AGENT → Backend models (SourceVideo, Clip, BRollAsset)
- BACKEND-AGENT → API development (video input, clip generation pipeline, clip library, dashboard)
- FRONTEND-AGENT → UI components (input form, processing status, library, dashboard)
- TEST-AGENT → Testing
- REVIEW-AGENT → Code review
- DEVOPS-AGENT → Deployment (must bundle ffmpeg + yt-dlp in the Docker image)

Read agent definitions in `/agents/` folder.
