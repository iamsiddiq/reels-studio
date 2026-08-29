# INITIAL.md - Shorts/Reels Maker Product Definition

> Convert long-form videos into multiple short-form clips (Shorts/Reels) for social media.

---

## PRODUCT

### Name
Shorts/Reels Maker

### Description
A tool that converts long-form videos into multiple short, social-media-ready clips. Users submit a video either by pasting a YouTube URL or uploading a file. The system transcribes the video, detects highlight-worthy segments, crops them to vertical 9:16 format, burns in captions, and (post-MVP) inserts relevant B-roll footage into the clips.

### Target User
Content creators, YouTubers, and podcasters who want to repurpose long-form videos into short-form clips for TikTok, Instagram Reels, and YouTube Shorts.

### Type
- [x] SaaS (Software as a Service)

---

## TECH STACK

### Backend
- [x] FastAPI + Python

### Frontend
- [x] React + Vite + TypeScript

### Database
- [x] PostgreSQL (recommended for all stacks)

### Authentication
- [ ] None — single-user app, no login/signup flow for MVP

### UI Framework
- [x] Tailwind + shadcn/ui

### Payments
- [ ] None — no payments needed for MVP

### Additional Integrations (implementation detail, not user-facing choice)
- `yt-dlp` — downloading source video from YouTube URL
- `ffmpeg` — video cropping/cutting, vertical reformatting, caption burn-in
- Speech-to-text model (e.g., faster-whisper) — transcription for highlight detection
- Background job queue (e.g., Celery + Redis, or FastAPI BackgroundTasks for MVP) — async video processing pipeline
- Object storage (local disk for MVP, S3-compatible for production) — source videos and generated clips

---

## MODULES

### Module 1: Video Input

**Description:** Entry point where a user submits a video for processing, either via YouTube URL or direct file upload.

**Models:**
```
SourceVideo:
  - id: int
  - source_type: enum (youtube, upload)
  - source_url: str (nullable, YouTube URL)
  - file_path: str (nullable, uploaded file path)
  - title: str
  - duration_seconds: float (nullable until processed)
  - status: enum (queued, downloading, processing, completed, failed)
  - error_message: str (nullable)
  - created_at: datetime
```

**API Endpoints:**
- `POST /api/v1/videos` — submit a YouTube URL for processing
- `POST /api/v1/videos/upload` — upload a video file (multipart)
- `GET /api/v1/videos` — list all submitted videos
- `GET /api/v1/videos/{id}` — get video details + status

**Frontend Pages:**
- `/new` — input form (YouTube URL field or file upload dropzone)

---

### Module 2: Clip Generation

**Description:** Background processing pipeline. Transcribes the source video, detects highlight segments, crops each segment to vertical 9:16, burns in captions, and (post-MVP) auto-inserts relevant B-roll footage.

**Models:**
```
Clip:
  - id: int
  - source_video_id: FK -> SourceVideo
  - start_time: float
  - end_time: float
  - video_path: str
  - caption_text: str
  - has_broll: bool (default false, post-MVP feature)
  - status: enum (queued, processing, completed, failed)
  - created_at: datetime

BRollAsset:  # post-MVP
  - id: int
  - keyword: str
  - file_path: str
  - source: str (e.g., stock provider name or "user_upload")
  - created_at: datetime
```

**API Endpoints:**
- `POST /api/v1/videos/{id}/generate` — trigger the clip-generation pipeline for a source video
- `GET /api/v1/videos/{id}/status` — poll processing status (queued/processing/done/failed)

**Frontend Pages:**
- `/processing/{videoId}` — live status view (queued → transcribing → clipping → captioning → done)

---

### Module 3: Clip Library

**Description:** Browse, preview, download, and manage all generated clips.

**API Endpoints:**
- `GET /api/v1/clips` — list all clips (filterable by source_video_id)
- `GET /api/v1/clips/{id}` — get clip detail
- `GET /api/v1/clips/{id}/download` — download the clip file
- `DELETE /api/v1/clips/{id}` — delete a clip
- `POST /api/v1/clips/{id}/rerender` — re-render a clip with different settings (post-MVP)

**Frontend Pages:**
- `/library` — grid/list of all generated clips across all videos
- `/clips/{id}` — clip preview player + download button

---

### Module 4: Dashboard

**Description:** Overview of processing activity.

**API Endpoints:**
- `GET /api/v1/dashboard/stats` — counts of videos processed, clips generated, storage used

**Frontend Pages:**
- `/dashboard` — overview widgets (videos processed, clips generated, recent activity)

---

### Module 5: Analytics Dashboard (Post-MVP)

**Description:** Deeper usage metrics beyond the basic dashboard.

**API Endpoints:**
- `GET /api/v1/analytics/usage` — usage over time (videos/day, clips/day, storage growth)

**Frontend Pages:**
- `/analytics` — charts and usage breakdowns

---

### Module 6: Admin Panel (Post-MVP)

**Description:** System-level management view (no user accounts since there's no auth — this manages content/system state, not users).

**API Endpoints:**
- `GET /api/v1/admin/stats` — platform-wide stats
- `GET /api/v1/admin/videos` — list/manage all source videos
- `DELETE /api/v1/admin/videos/{id}` — force-remove a video and its clips

**Frontend Pages:**
- `/admin` — admin dashboard
- `/admin/videos` — video management table

---

## MVP SCOPE

### Must Have (MVP)
- [x] Submit a video via YouTube URL or file upload
- [x] Automatic transcription + AI highlight detection to find clip-worthy segments
- [x] Auto-crop to vertical 9:16 with burned-in captions
- [x] Clip Library — preview and download generated clips
- [x] Basic processing status view (queued/processing/done)

### Nice to Have (Post-MVP)
- [ ] B-roll auto-insertion into clips
- [ ] Analytics dashboard (usage metrics, storage)
- [ ] Admin panel
- [ ] Custom B-roll asset upload/management
- [ ] Multiple caption style templates
- [ ] Direct publish to YouTube/TikTok/Instagram

---

## ACCEPTANCE CRITERIA

### Video Input
- [ ] User can paste a YouTube URL and the video is downloaded server-side
- [ ] User can upload a video file directly (with reasonable size/format limits)
- [ ] Invalid URLs / unsupported formats show a clear error

### Clip Generation
- [ ] Source video is transcribed automatically
- [ ] Pipeline identifies multiple (3+) highlight segments per source video
- [ ] Each clip is cropped to 9:16 vertical format
- [ ] Captions are burned into the clip video, synced to speech
- [ ] Processing status updates in real time (polling or websocket)

### Clip Library
- [ ] All generated clips for a video are listed and previewable
- [ ] User can download any clip as an MP4 file
- [ ] User can delete a clip

### Quality
- [ ] All API endpoints documented in OpenAPI
- [ ] Backend test coverage 80%+
- [ ] Frontend TypeScript strict mode passes
- [ ] Docker builds and runs successfully (including ffmpeg dependency)

---

## SPECIAL REQUIREMENTS

### Security
- [x] Input validation on all endpoints (especially YouTube URL and file upload)
- [x] File upload size/type restrictions (video files only, size cap)
- [x] SQL injection prevention
- [x] XSS prevention
- [ ] Auth: not required for MVP (single-user/local use assumed)

### Integrations
- [x] `yt-dlp` for YouTube video download
- [x] `ffmpeg` for video processing (crop, cut, caption burn-in)
- [x] Speech-to-text (e.g., faster-whisper) for transcription
- [x] Background job processing for the async clip-generation pipeline
- [ ] Stripe/Dodo/LemonSqueezy — not needed (no payments)

---

## AGENTS

> These agents build your product in parallel:

| Agent | Role | Works On |
|-------|------|----------|
| DATABASE-AGENT | Creates all models and migrations | SourceVideo, Clip, BRollAsset models |
| BACKEND-AGENT | Builds API endpoints and services | Video input, clip generation pipeline, clip library, dashboard APIs |
| FRONTEND-AGENT | Creates UI pages and components | Input form, processing status, clip library, dashboard |
| DEVOPS-AGENT | Sets up Docker, CI/CD, environments | Dockerfile with ffmpeg/yt-dlp deps, docker-compose |
| TEST-AGENT | Writes unit and integration tests | All code |
| REVIEW-AGENT | Security and code quality audit | All code |

---

# READY?

```bash
/generate-prp INITIAL.md
```

Then:

```bash
/execute-prp PRPs/shorts-reels-maker-prp.md
```
