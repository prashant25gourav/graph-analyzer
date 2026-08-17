# API Reference

Base URL is the backend origin (for local development, `http://localhost:8000`).
Interactive docs are available at `/api/docs` when the server is running.

## GET /api/health

Liveness check for local and cloud monitoring. No Groq call, no auth, no image.

Response `200`:

```json
{ "status": "ok", "service": "graph-analyzer-api", "version": "0.1.0" }
```

## POST /api/v1/analyze

Analyze a single graph image and return a structured analysis.

Request: `multipart/form-data` with one field:

- `file` — the image. Accepted types: PNG, JPEG, WebP.

Response `200`: file metadata plus an `analysis` object (graph type, axis labels,
units, categories/legends, highest/lowest values, trends, observations, business
insights, recommendations, summary, and uncertainty notes). Fields that cannot be
determined come back as `Not Available`, and unknown numeric values as `null`.

## POST /api/v1/compare

Analyze two graph images independently and return both analyses plus a comparison.

Request: `multipart/form-data` with two fields:

- `graph_a` — the first image.
- `graph_b` — the second image.

Both fields accept PNG, JPEG, or WebP.

Response `200`: `graph_a` and `graph_b` (each with metadata and its `analysis`) and
a `comparison` object. The comparison contains deterministic output — similarities,
differences, value deltas (absolute and percent change), trend comparison,
significant changes, and comparability flags — alongside AI-interpreted comparative
insights, recommendations, and a summary. When the graphs are not numerically
comparable, the comparability flags and reasons say so rather than fabricating a
numeric comparison.

## Errors

Errors use a consistent JSON envelope with an `error_code` and a client-safe
`message` (internal details are never included). Common statuses for both upload
endpoints:

- `400` — invalid request (e.g. missing filename or empty file)
- `413` — file too large
- `415` — unsupported image type
- `422` — malformed or corrupted image
- `502` — upstream AI provider error
- `504` — AI provider timeout
