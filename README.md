# AI Graph Analyzer & Comparator

Upload a chart image and get a structured, AI-generated analysis of it — or upload
two charts and get a side-by-side comparison. The backend uses a Groq multimodal
model to extract structured facts from each image; a deterministic engine computes
the numeric differences; and the AI then writes the interpretive prose over those
facts (so the numbers are real and only the narrative is generated).

## Overview

The project has two workflows:

1. **Single Graph Analysis** — one chart image in, one structured analysis out
   (graph type, axes, highest/lowest values, trends, observations, business
   insights, recommendations, summary).
2. **Graph Comparison** — two chart images in. Each is analyzed independently, a
   deterministic engine computes structural and numeric differences (absolute and
   percent change, trend shifts, significant changes), and the AI interprets those
   computed facts into comparative insights, recommendations, and a summary. When
   the two graphs are not numerically comparable (different units, types, or
   categories), the response says so explicitly instead of inventing numbers.

## Features

- Multimodal graph extraction via Groq (`qwen/qwen3.6-27b`).
- Typed, validated responses (pydantic v2) for both single analysis and comparison;
  malformed or partial model output is normalized rather than crashing the request.
- Deterministic comparison math (real deltas) separated from AI-written prose.
- Honest degradation: if the interpretation call fails, the API falls back to a
  deterministic interpretation derived from the computed comparison and flags that
  it did so.
- Input validation: MIME allow-list (PNG/JPEG/WebP), size limit, and a Pillow
  integrity check that rejects malformed images.
- Production hardening: structured logging, a global exception handler that returns
  a generic message (no stack traces or internal details leak to clients), and
  the blocking Groq SDK call is run in a worker thread to keep the event loop free.
- Configurable CORS and API base URL via environment variables — nothing about the
  deployment target is hardcoded.

## Architecture

```
apps/
  backend/                 FastAPI service
    app/
      main.py              app factory: CORS, logging, global exception handler
      core/
        config.py          env-driven Settings (pydantic-settings)
        logging_config.py  logging setup
        errors.py          error/response helpers
      api/
        routes_health.py   GET  /api/health
        routes_analyze.py  POST /api/v1/analyze
        routes_compare.py  POST /api/v1/compare
      services/
        groq_graph_service.py  Groq calls: extract analysis + interpret comparison
        comparison_engine.py   deterministic deltas, prompt builder, safe fallback
      models/
        analysis.py        SingleGraphAnalysis, ValuePoint
        comparison.py      GraphComparisonResult, ComparisonInterpretation, ...
      utils/
        image_validation.py    MIME/size/integrity checks
    tests/                 pytest suite (endpoint + normalization tests)
    requirements.txt       production dependencies
    requirements-dev.txt   + pytest, httpx (test/dev only)
  frontend/                React + TypeScript + Vite single-page app
    src/
      main.tsx             BrowserRouter root
      app/App.tsx          routes + nav
      pages/               HomePage, AnalyzePage, ComparePage
      services/api.ts      API client (base URL from VITE_API_BASE_URL)
deployment/
  render.yaml              Render Blueprint for the backend (native Python runtime)
docs/                      architecture and API notes
```

Request flow for comparison: `image A, image B → validate → Groq extracts a
structured analysis of each → deterministic engine computes the differences → Groq
interprets those computed facts into prose → validated response`. The raw images
are not re-sent for the interpretation step; the already-extracted structured data
is reused.

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, uvicorn, pydantic v2 / pydantic-settings,
  Pillow, groq SDK.
- **Frontend:** React 18, TypeScript, Vite 6, React Router 6.
- **AI:** Groq multimodal chat completions.

## Local Setup

### Backend

1. From `apps/backend`, create and activate a virtual environment (Python 3.11+):

   ```bash
   cd apps/backend
   python -m venv .venv
   # Windows:      .venv\Scripts\activate
   # macOS/Linux:  source .venv/bin/activate
   ```

2. Install dependencies (production only, or dev for tests):

   ```bash
   pip install -r requirements.txt          # runtime
   pip install -r requirements-dev.txt      # runtime + pytest/httpx
   ```

3. Create your local env file from the template and add your Groq key:

   ```bash
   cp .env.example .env        # Windows: copy .env.example .env
   # edit .env: set GROQ_API_KEY=your_key
   ```

### Frontend

1. From `apps/frontend`, install dependencies and create an env file:

   ```bash
   cd apps/frontend
   npm install
   cp .env.example .env        # Windows: copy .env.example .env
   # edit .env: set VITE_API_BASE_URL (defaults to http://localhost:8000)
   ```

## Environment Variables

Backend (`apps/backend/.env`, template in `apps/backend/.env.example`):

| Variable                  | Purpose                                         | Default (dev)                              |
|---------------------------|-------------------------------------------------|--------------------------------------------|
| `GROQ_API_KEY`            | Groq API key. Read only from the environment.   | *(none — required)*                        |
| `GROQ_MODEL`              | Groq model id.                                  | `qwen/qwen3.6-27b`                         |
| `APP_ENV`                 | Environment name.                               | `development`                              |
| `LOG_LEVEL`               | Logging level.                                  | `INFO`                                      |
| `CORS_ALLOWED_ORIGINS`    | Comma-separated allowed browser origins.        | `http://localhost:5173`                    |
| `MAX_UPLOAD_MB`           | Max upload size (MB).                            | `8`                                         |
| `REQUEST_TIMEOUT_SECONDS` | Groq request timeout.                            | `45`                                        |
| `PORT`                    | Provided by the host (e.g. Render).             | `8000` locally                             |

Frontend (`apps/frontend/.env`, template in `apps/frontend/.env.example`):

| Variable            | Purpose                          | Default (dev)           |
|---------------------|----------------------------------|-------------------------|
| `VITE_API_BASE_URL` | Base URL of the backend API.     | `http://localhost:8000` |

The Groq API key is **never** placed in the frontend or committed to source.
`.env` files are gitignored; only `.env.example` templates are tracked.

## Running Locally

Backend (from `apps/backend`, with the venv active and `.env` set):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend (from `apps/frontend`):

```bash
npm run dev        # dev server on http://localhost:5173
npm run build      # type-check + production build into dist/
npm run preview    # serve the production build locally
```

## API Endpoints

- `GET /api/health` — fast liveness check. Returns
  `{"status":"ok","service":"graph-analyzer-api","version":"0.1.0"}`. No Groq call,
  no auth, no image.
- `POST /api/v1/analyze` — multipart form, field `file` (PNG/JPEG/WebP). Returns the
  structured single-graph analysis.
- `POST /api/v1/compare` — multipart form, fields `graph_a` and `graph_b`. Returns
  both analyses plus the comparison (similarities, differences, value deltas, trend
  comparison, significant changes, comparability flags, and AI-interpreted insights,
  recommendations, and summary).

Interactive API docs are available at `/api/docs` when the server is running.

## Deployment

The backend deploys to **Render as a native Python Web Service** via the Blueprint
at `deployment/render.yaml`. See `DEPLOYMENT_RUNBOOK.md` for the
full step-by-step guide. In short:

1. Push the repo to GitHub.
2. In Render, create a **Blueprint** from the repo; it detects `deployment/render.yaml`
   and configures the `graph-analyzer-api` service (build: `pip install -r
   requirements.txt`, start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`,
   health check: `/api/health`).
3. Set the `GROQ_API_KEY` secret in the Render dashboard (it is declared with
   `sync: false`, so it is never committed).
4. After deploy, set `CORS_ALLOWED_ORIGINS` to your frontend's public URL.

The frontend is a static single-page app and can be deployed to any static host
(Render Static Site, Netlify, Cloudflare Pages, etc.):

- Build command: `npm run build`; publish directory: `apps/frontend/dist`.
- Set `VITE_API_BASE_URL` to your deployed backend URL at build time.
- Because it uses client-side routing (React Router), add a **rewrite** so all
  paths serve `index.html`. A `public/_redirects` file (`/* /index.html 200`) is
  included for hosts that honor it; on Render Static Sites add the equivalent
  rewrite rule (Source `/*` → Destination `/index.html`, Action Rewrite).
