# Shorts/Reels Maker — Project Workflow

> How this project was built, and how a video actually becomes a set of shorts at runtime.

---

## 1. What This Project Is

Converts a long-form video (YouTube URL or direct upload) into multiple short,
vertical (9:16), captioned clips ready for TikTok/Reels/Shorts. No login,
no payments — single-user local/self-hosted app.

**Tech stack:** FastAPI + Python 3.11 · React + Vite + TypeScript · PostgreSQL +
SQLAlchemy · Tailwind + shadcn/ui · ffmpeg + yt-dlp + faster-whisper · Docker.

---

## 2. How This Project Was Built (meta-workflow)

This repo was scaffolded using the template's own multi-agent build pipeline,
driven by three slash commands run in sequence:

```
/setup-project  →  INITIAL.md + CLAUDE.md
      ↓
/generate-prp INITIAL.md  →  PRPs/shorts-reels-maker-prp.md
      ↓
/execute-prp PRPs/shorts-reels-maker-prp.md  →  full backend + frontend + infra
```

### 2.1 `/setup-project` — interactive product definition
Asked a series of questions (product basics, tech stack, core modules, MVP
scope) and generated `INITIAL.md` (product spec) and `CLAUDE.md` (project
rules/conventions). Key decisions locked in here: **no auth**, **no
payments**, Tailwind + shadcn/ui, and the module list (Video Input, Clip
Generation, Clip Library, Dashboard, plus post-MVP Analytics/Admin).

### 2.2 `/generate-prp` — implementation blueprint
Read `INITIAL.md` + `CLAUDE.md` and produced `PRPs/shorts-reels-maker-prp.md`:
database models, API endpoints per module, frontend pages, a phased execution
plan, and validation gates.

### 2.3 `/execute-prp` — parallel agent build
Ran the PRP through three phases, each dispatching multiple agents in
parallel (background subagents, not sequential turns):

```
Phase 1 — Foundation (4 agents in parallel)
├─ DATABASE-AGENT   → SourceVideo, Clip, BRollAsset models + Alembic migration
├─ BACKEND-AGENT    → FastAPI app skeleton, config, exceptions
├─ FRONTEND-AGENT   → Vite + React + TS + Tailwind + shadcn/ui scaffold
└─ DEVOPS-AGENT     → Dockerfiles (ffmpeg bundled), docker-compose, CI

        ↓ Validation Gate 1 (alembic upgrade, npm install, docker compose config)

Phase 2 — MVP Modules (2 agents in parallel, one per stack to avoid
                        both editing shared files like main.py/App.tsx)
├─ BACKEND-AGENT    → Video Input + Clip Generation pipeline + Clip Library + Dashboard APIs
└─ FRONTEND-AGENT   → NewVideo, Processing, Library, ClipDetail, Dashboard pages

        ↓ Validation Gate 2 (ruff, npm lint/type-check)

Phase 3 — Quality (3 agents in parallel)
├─ TEST-AGENT       → pytest + Vitest suites (63 backend tests, 95% coverage)
├─ REVIEW-AGENT     → OWASP-style security + performance review
└─ RESEARCH-AGENT   → validated yt-dlp/whisper/ffmpeg usage against best practices
```

Findings from REVIEW-AGENT and RESEARCH-AGENT (max video duration cap,
double-trigger guard on regenerate, ffmpeg/ffprobe timeouts, `ffmpeg_location`
pin for yt-dlp, a `.env` loading bug) were applied as follow-up fixes with
regression tests added for each.

**Later addition:** highlight selection was upgraded to optionally use
OpenAI (see §3.3) — added after the initial PRP execution, on request.

---

## 3. Runtime Pipeline Workflow (what happens to a video)

This is the actual request lifecycle once the app is running.

```
User submits YouTube URL or uploads a file
              ↓
   POST /api/v1/videos  or  /api/v1/videos/upload
   (creates SourceVideo row, status=queued, dispatches
    background task, returns immediately)
              ↓
┌─────────────────────────────────────────────────────────┐
│  process_source_video()  — runs as a FastAPI             │
│  BackgroundTask, own DB session, isolated from the        │
│  request that triggered it                                │
│                                                             │
│  1. ACQUIRE          status → downloading                  │
│     ├─ youtube: yt-dlp downloads the video                 │
│     └─ upload:  file already on disk; ffprobe measures     │
│                  its duration                               │
│                                                             │
│     ⛔ duration > MAX_VIDEO_DURATION_SECONDS (2400s/40min)? │
│        → fail fast, never reaches transcription             │
│                                                             │
│  2. TRANSCRIBE       status → processing                    │
│     faster-whisper (local, CPU, int8) → timestamped         │
│     segments [{start, end, text}, ...]                      │
│                                                             │
│  3. SELECT HIGHLIGHTS                                        │
│     OPENAI_API_KEY set?                                     │
│       yes → GPT reads the transcript, picks up to            │
│             max_clips (default 4) genuinely engaging          │
│             windows (hooks/punchlines/insights),              │
│             15–60s each, non-overlapping                      │
│             → output validated/clamped against real           │
│               transcript bounds (defends against               │
│               hallucinated timestamps)                          │
│             → falls back to heuristic below if the API           │
│               call fails or returns nothing valid                 │
│       no  → local heuristic: score candidate windows by            │
│             word-count × sentence-density, pick top-scoring         │
│             non-overlapping windows                                  │
│                                                                        │
│     (caption text for a chosen window always comes from the           │
│      real transcript, never authored by the LLM — keeps               │
│      burned-in captions in sync with the actual audio)                │
│                                                                        │
│  4. RENDER (per highlight)                                            │
│     ffmpeg: cut [start,end] → scale+crop to 1080×1920 (9:16)          │
│             → burn in captions via a generated .srt                   │
│             → one Clip row per rendered highlight                     │
│             (a single clip's render failure doesn't abort              │
│              the rest — that clip is marked failed, others             │
│              continue)                                                  │
│                                                                          │
│  5. status → completed  (or failed, with error_message, if              │
│     any stage above raised)                                             │
└───────────────────────────────────────────────────────────────────────┘
              ↓
   Frontend polls GET /api/v1/videos/{id}/status every 3s
              ↓
   User browses/downloads clips via Clip Library
   (GET /api/v1/clips, GET /api/v1/clips/{id}/download)
```

### 3.1 Where each stage lives in code
| Stage | File |
|---|---|
| Download (YouTube) | `backend/app/services/youtube_downloader.py` |
| Duration probe | `backend/app/services/video_processor.py::probe_duration_seconds` |
| Transcription | `backend/app/services/transcription.py` |
| Highlight selection | `backend/app/services/highlight_detector.py` |
| Rendering (crop + captions) | `backend/app/services/video_processor.py::crop_to_vertical_with_captions` |
| Orchestration | `backend/app/services/pipeline.py` |
| API endpoints | `backend/app/routers/videos.py`, `clips.py`, `dashboard.py` |

### 3.2 Guardrails already in place
- **Duration cap** (`MAX_VIDEO_DURATION_SECONDS`, default 2400s) rejects a video before transcription/rendering ever run.
- **In-flight guard**: `POST /videos/{id}/generate` returns `409 Conflict` if the video is already `queued`/`downloading`/`processing`, preventing two concurrent pipeline runs racing on the same output files.
- **ffmpeg/ffprobe timeouts** (600s / 30s) so a hung subprocess doesn't pin a worker thread forever.
- **Per-clip failure isolation**: one bad highlight render doesn't fail the whole video.
- **Command-injection-safe**: all `ffmpeg` calls use argument lists (never `shell=True`); yt-dlp is invoked via its Python API, not a shell-out.

### 3.3 Highlight selection: heuristic vs. OpenAI
Set in `backend/.env` (or root `.env` for docker-compose):
```env
OPENAI_API_KEY=        # leave blank to always use the local heuristic
OPENAI_MODEL=gpt-4o-mini
```
- **No key** → word-density heuristic (`_heuristic_detect_highlights`), fully offline, free.
- **Key set** → GPT call (`_call_openai_for_highlights`) picks windows semantically; any failure (bad response, network error, no valid windows after validation) silently falls back to the heuristic so the pipeline never hard-fails because of it.
- Transcription always stays on local faster-whisper regardless of this setting.

---

## 4. Project Structure

```
backend/app/
├── main.py            FastAPI app, CORS, router wiring, /health
├── config.py           Settings (env-driven; no secrets hardcoded)
├── database.py         SQLAlchemy engine/session
├── exceptions.py        NotFoundError/ConflictError/ValidationError/ProcessingError
├── models/              SourceVideo, Clip, BRollAsset
├── schemas/              Pydantic request/response models
├── routers/              videos.py, clips.py, dashboard.py
└── services/             youtube_downloader, transcription, highlight_detector,
                          video_processor, pipeline

frontend/src/
├── pages/               NewVideoPage, ProcessingPage, LibraryPage, ClipDetailPage, DashboardPage
├── services/             videoService, clipService, dashboardService (Axios)
├── components/ui/        shadcn Button/Card/Badge
└── components/layout/    AppLayout (nav)
```

---

## 5. Running It

**Docker (recommended):**
```bash
cd "Offline CC"
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```
- Frontend: http://localhost:5173
- Backend: http://localhost:8000 (docs at `/docs`)

**Bare metal:**
```bash
# backend
cd backend && source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload

# frontend
cd frontend && npm run dev
```

Copy `.env.example` → `.env` first and fill in real values. `.env` is
git-ignored; `.env.example` must never contain real secrets (only
blank/placeholder values) since it *is* committed.

---

## 6. Testing & Quality

```bash
cd backend && source .venv/bin/activate
pytest tests -v --cov=app --cov-report=term-missing   # 63+ tests, 95% coverage
ruff check app/                                         # lint

cd frontend
npm test          # Vitest + RTL
npm run lint       # oxlint
npm run type-check # tsc -b
```

All external boundaries (yt-dlp, faster-whisper, ffmpeg subprocess, OpenAI)
are mocked in tests — no network/GPU/ffmpeg binary required to run the suite.

---

## 7. Known Limitations (post-MVP roadmap)

- **FastAPI `BackgroundTasks`** shares the request thread pool — fine for a single user, but concurrent submissions will contend for CPU/threads. Swap for Celery/RQ before supporting multiple concurrent users.
- **No content-sniffing** on uploads (trusts the client-supplied `Content-Type` header); low risk since downstream ffmpeg/whisper calls are already injection-safe.
- **No cleanup job** yet for orphaned files left behind by a failed pipeline run.
- **B-roll auto-insertion, Analytics Dashboard, Admin Panel** are scoped in the PRP but not implemented (explicitly deferred to post-MVP).
