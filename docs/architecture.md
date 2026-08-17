# Architecture

The system is split into a stateless FastAPI backend and a React single-page
frontend. The backend owns all validation, the AI calls, and the comparison math;
the frontend only collects images, calls the API, and renders the response. The
Groq API key lives exclusively on the backend and is never exposed to the browser.

## Components

The **backend** (`apps/backend`) is organized by responsibility:

- `api/` holds the route handlers for `/api/health`, `/api/v1/analyze`, and
  `/api/v1/compare`. Handlers stay thin: they validate input, delegate to a
  service, and shape the response.
- `services/groq_graph_service.py` wraps the Groq client. It sends the image for
  single-graph extraction and, separately, sends already-extracted facts back to
  the model for comparison interpretation.
- `services/comparison_engine.py` computes the deterministic comparison (deltas,
  percent change, structural similarities/differences, comparability flags), builds
  the interpretation prompt, and provides a deterministic fallback interpretation.
- `models/` defines the pydantic schemas (`SingleGraphAnalysis`,
  `GraphComparisonResult`, `ComparisonInterpretation`, and their parts) that every
  response is validated against.
- `utils/image_validation.py` enforces the MIME allow-list, size limit, and a
  Pillow integrity check.
- `core/` holds environment-driven settings, logging setup, and the error schema.

The **frontend** (`apps/frontend`) is a Vite single-page app. `services/api.ts`
centralizes the API base URL (from `VITE_API_BASE_URL`) and the fetch calls; the
pages under `pages/` handle upload, preview, client-side pre-checks, and rendering.

## Request flow

For a single analysis: the image is uploaded, validated in memory (type, size,
and a Pillow decode), then sent to the Groq vision model. The model is asked to
return JSON; the service extracts and normalizes that JSON so missing or malformed
fields become `Not Available` (or `null` for unknown numbers) rather than errors,
and the result is validated against `SingleGraphAnalysis`.

For a comparison: both images are validated and analyzed independently, producing
two structured analyses. The comparison engine then computes the differences from
those structured facts — no numbers come from the model. Those computed facts are
sent to the model for interpretation (insights, recommendations, summary). If the
interpretation call fails, a deterministic fallback interpretation is generated
from the same computed facts and the response notes that it did so. The raw images
are never re-sent for the interpretation step.

## Design rules

- Numbers are computed by code; the model only interprets. When two graphs are not
  numerically comparable (different units, types, or no shared categories), the API
  says so instead of fabricating a comparison.
- Uploads are handled in memory — no filesystem writes and no local key files.
- The API key is read only from the environment and stays on the backend.
- Errors returned to the client are generic. Internal exception text and stack
  traces are logged server-side but never included in responses.
- The blocking Groq SDK call runs in a worker thread so it does not stall the event
  loop or health checks.

## Deployment shape

The backend runs on Render's native Python runtime (see `deployment/render.yaml`
and `DEPLOYMENT_RUNBOOK.md`); the frontend builds to static files and is served by
any static host. The two are connected by `VITE_API_BASE_URL` (frontend → backend)
and `CORS_ALLOWED_ORIGINS` (backend → allowed frontend origin).
