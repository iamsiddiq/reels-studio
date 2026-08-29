# PRP: Shorts/Reels Maker

> Implementation blueprint for parallel agent execution

---

## METADATA

| Field | Value |
|-------|-------|
| **Product** | Shorts/Reels Maker |
| **Type** | SaaS |
| **Version** | 1.0 |
| **Created** | 2026-08-29 |
| **Complexity** | Medium-High (async video processing pipeline: download, transcription, highlight detection, ffmpeg rendering) |

---

## PRODUCT OVERVIEW

**Description:** Converts long-form videos into multiple short, social-media-ready clips. Users submit a video either by pasting a YouTube URL or uploading a file. The system transcribes it, detects highlight-worthy segments, crops them to vertical 9:16, burns in captions, and (post-MVP) inserts relevant B-roll footage.

**Value Proposition:** Content creators spend hours manually clipping long videos into shorts. This automates highlight detection, vertical reformatting, and captioning so a single upload produces multiple ready-to-post clips in minutes.

**MVP Scope:**
- [ ] Submit a video via YouTube URL or file upload
- [ ] Automatic transcription + AI highlight detection to find clip-worthy segments
- [ ] Auto-crop to vertical 9:16 with burned-in captions
- [ ] Clip Library — preview and download generated clips
- [ ] Basic processing status view (queued/processing/done)

**Post-MVP:** B-roll auto-insertion, analytics dashboard, admin panel, custom B-roll asset management, multiple caption styles, direct social publishing.

---

## TECH STACK

| Layer | Technology | Skill Reference |
|-------|------------|-----------------|
| Backend | FastAPI + Python 3.11+ | skills/BACKEND.md |
| Frontend | React + TypeScript + Vite | skills/FRONTEND.md |
| Database | PostgreSQL + SQLAlchemy | skills/DATABASE.md |
| Auth | None (no login/signup for MVP) | — |
| UI | Tailwind + shadcn/ui | skills/FRONTEND.md |
| Video Processing | ffmpeg (crop/caption burn-in), yt-dlp (YouTube download), faster-whisper (transcription) | — |
| Background Jobs | FastAPI BackgroundTasks (MVP) → Celery + Redis (scale-up) | — |
| Testing | pytest + React Testing Library | skills/TESTING.md |
| Deployment | Docker + GitHub Actions (image must bundle ffmpeg + yt-dlp) | skills/DEPLOYMENT.md |

---

## DATABASE MODELS

### SourceVideo
- `id`: int, PK
- `source_type`: enum (`youtube`, `upload`)
- `source_url`: str, nullable (YouTube URL)
- `file_path`: str, nullable (uploaded file path)
- `title`: str
- `duration_seconds`: float, nullable until processed
- `status`: enum (`queued`, `downloading`, `processing`, `completed`, `failed`)
- `error_message`: str, nullable
- `created_at`: datetime

### Clip
- `id`: int, PK
- `source_video_id`: FK -> SourceVideo, cascade delete
- `start_time`: float
- `end_time`: float
- `video_path`: str
- `caption_text`: str
- `has_broll`: bool, default false (post-MVP)
- `status`: enum (`queued`, `processing`, `completed`, `failed`)
- `created_at`: datetime

### BRollAsset (post-MVP; create table now, wire up later)
- `id`: int, PK
- `keyword`: str
- `file_path`: str
- `source`: str (stock provider name or `user_upload`)
- `created_at`: datetime

**Relationships:** `SourceVideo` 1—N `Clip` (cascade delete: removing a video removes its clips and files).

---

## MODULES

> No Authentication module — this build has no login/signup/protected routes.

### Module 1: Video Input
**Agents:** DATABASE-AGENT + BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/videos | Submit a YouTube URL for processing |
| POST | /api/v1/videos/upload | Upload a video file (multipart) |
| GET | /api/v1/videos | List all submitted videos |
| GET | /api/v1/videos/{id} | Get video details + status |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /new | NewVideoPage | YouTubeUrlInput, FileDropzone, SubmitButton |

---

### Module 2: Clip Generation
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/videos/{id}/generate | Trigger the clip-generation pipeline |
| GET | /api/v1/videos/{id}/status | Poll processing status |

**Pipeline (services/ layer, invoked as a background task):**
1. `youtube_downloader.py` — download via yt-dlp if `source_type == youtube`
2. `transcription.py` — transcribe audio (faster-whisper)
3. `highlight_detector.py` — score transcript segments, select top N highlight windows
4. `video_processor.py` — ffmpeg: cut segment, crop/pad to 9:16, burn in captions
5. Persist each result as a `Clip` row; update `SourceVideo.status`

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /processing/{videoId} | ProcessingPage | StatusStepper, PollingIndicator |

---

### Module 3: Clip Library
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/clips | List all clips (filter by source_video_id) |
| GET | /api/v1/clips/{id} | Get clip detail |
| GET | /api/v1/clips/{id}/download | Stream clip file for download |
| DELETE | /api/v1/clips/{id} | Delete clip (row + file) |
| POST | /api/v1/clips/{id}/rerender | Re-render with different settings (post-MVP) |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /library | LibraryPage | ClipGrid, ClipCard |
| /clips/{id} | ClipDetailPage | VideoPlayer, DownloadButton, DeleteButton |

---

### Module 4: Dashboard
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/dashboard/stats | Videos processed, clips generated, storage used |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /dashboard | DashboardPage | StatWidget, RecentActivityList |

---

### Module 5: Analytics Dashboard (Post-MVP)
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/analytics/usage | Usage over time (videos/day, clips/day, storage growth) |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /analytics | AnalyticsPage | UsageChart |

---

### Module 6: Admin Panel (Post-MVP)
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/admin/stats | Platform-wide stats |
| GET | /api/v1/admin/videos | List/manage all source videos |
| DELETE | /api/v1/admin/videos/{id} | Force-remove a video and its clips |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /admin | AdminDashboardPage | AdminStatWidget |
| /admin/videos | AdminVideosPage | VideoManagementTable |

---

## PHASE EXECUTION PLAN

**Phase 1: Foundation (4 agents in parallel)**
- DATABASE-AGENT: `SourceVideo`, `Clip`, `BRollAsset` models + Alembic migration, `database.py`
- BACKEND-AGENT: `main.py`, `config.py`, project structure, storage path setup, `/health` endpoint
- FRONTEND-AGENT: Vite + Tailwind + shadcn/ui setup, folder structure, base layout/nav (no auth guards needed)
- DEVOPS-AGENT: Dockerfile (bundling `ffmpeg` + `yt-dlp`), docker-compose (backend, frontend, postgres, redis if used), env files

**Validation Gate 1:** `alembic upgrade head`, `pip install -r requirements.txt`, `npm install`, `docker-compose config`, `ffmpeg -version` inside container

**Phase 2: Modules (backend + frontend parallel per module)**
- Video Input: upload/URL endpoints + NewVideoPage
- Clip Generation: pipeline services + ProcessingPage
- Clip Library: CRUD/download endpoints + LibraryPage/ClipDetailPage
- Dashboard: stats endpoint + DashboardPage
- (Post-MVP, only if time allows) Analytics + Admin modules

**Validation Gate 2:** `ruff check backend/`, `npm run type-check`, manual smoke test: submit a short YouTube URL end-to-end and confirm at least one clip is produced

**Phase 3: Quality (3 agents in parallel)**
- TEST-AGENT: pytest (mock ffmpeg/yt-dlp/whisper calls) + RTL tests, 80%+ coverage
- REVIEW-AGENT: security audit (input validation on URLs/uploads, subprocess arg-list safety, file size limits), performance review (streaming downloads, background task isolation)
- RESEARCH-AGENT: validate ffmpeg/yt-dlp/whisper usage against current best practices

**Final Validation:** Full test suite, `docker-compose up -d`, `curl localhost:8000/health`, end-to-end manual run (URL → clips downloadable)

---

## VALIDATION GATES

| Gate | Commands |
|------|----------|
| 1 | `alembic upgrade head`, `npm install`, `docker-compose config`, `ffmpeg -version` |
| 2 | `ruff check backend/`, `npm run type-check` |
| 3 | `pytest --cov --cov-fail-under=80`, `npm test` |
| Final | `docker-compose up -d`, `curl localhost:8000/health` |

---

## ENVIRONMENT VARIABLES

```env
DATABASE_URL=postgresql://user:password@localhost:5432/shorts_reels_maker
STORAGE_PATH=./storage
MAX_UPLOAD_SIZE_MB=500
FFMPEG_PATH=/usr/bin/ffmpeg
WHISPER_MODEL=base
REDIS_URL=redis://localhost:6379/0
VITE_API_URL=http://localhost:8000
```

---

## NEXT STEP

Execute with parallel agents:
```bash
/execute-prp PRPs/shorts-reels-maker-prp.md
```
