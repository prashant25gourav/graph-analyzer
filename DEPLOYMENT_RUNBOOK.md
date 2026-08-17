# Backend Deployment Runbook — Render (native Python Blueprint)

Target: deploy the FastAPI backend (`apps/backend`) to Render using the
`deployment/render.yaml` blueprint, which runs on Render's native Python runtime.
The frontend is deployed separately as a static site (see the "Frontend" section at
the end and the README).

This runbook covers **GitHub → Render Blueprint → verify live**. You are handling
Git/GitHub yourself; steps that touch your accounts are marked **[you]**.

---

## Prerequisites

- A [Groq API key](https://console.groq.com) (**API Keys** section). Keep it handy
  for Step 3. Never commit it or put it in `render.yaml`.
- A GitHub account and a Render account.

---

## 1. Push the repo to GitHub **[you]**

From the project root (`graph-analyzer/`):

```bash
git init
git add .
git commit -m "chore: initial commit of graph-analyzer for deployment"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

Before pushing, confirm no secrets are staged:

```bash
git ls-files | grep -i groq        # expect: only source files (services/tests), NOT a key file
git ls-files | grep -E "\.env$"    # expect: NOTHING (only .env.example files should appear)
```

If either shows a real key or a real `.env`, stop and remove it before pushing.

---

## 2. Create the Render Blueprint service **[you]**

1. Go to https://dashboard.render.com → **New** → **Blueprint**.
2. Connect your GitHub account and select the repo you just pushed.
3. Render auto-detects `deployment/render.yaml` and shows one service:
   `graph-analyzer-api` (Python, free plan).
4. Click **Apply** / **Create**.

The blueprint sets:

- `rootDir: apps/backend`
- `buildCommand: pip install -r requirements.txt`
- `startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- `healthCheckPath: /api/health`

Render injects `PORT`; the start command binds `0.0.0.0:$PORT`, so the port is
never hardcoded.

---

## 3. Set the secret env var **[you]**

`render.yaml` declares `GROQ_API_KEY` with `sync: false`, so Render prompts for it
(or add it under the service's **Environment** tab):

- `GROQ_API_KEY` = your Groq API key.

The other vars (`APP_ENV`, `LOG_LEVEL`, `GROQ_MODEL`, `CORS_ALLOWED_ORIGINS`,
`MAX_UPLOAD_MB`, `REQUEST_TIMEOUT_SECONDS`) come from `render.yaml` automatically.

> `CORS_ALLOWED_ORIGINS` defaults to `http://localhost:5173`. That is fine for a
> backend-only deploy (health checks, `/api/docs`, and curl/Postman tests don't
> enforce CORS). Update it to your frontend's public URL once the frontend is
> deployed. Multiple origins are supported as a comma-separated list.

---

## 4. Wait for build + deploy **[you]**

- Watch the **Logs** tab. The first build installs dependencies and takes a few minutes.
- Success looks like: `Uvicorn running on http://0.0.0.0:<port>`.
- Render assigns a URL like `https://graph-analyzer-api.onrender.com`.

**Free-plan caveat:** the instance sleeps after ~15 min idle; the first request
after sleep can take 30–60s to cold-start. This is normal.

---

## 5. Verify the live service

Once you have the live base URL, check:

```
GET  <URL>/api/health      → {"status":"ok","service":"graph-analyzer-api","version":"0.1.0"}
GET  <URL>/api/docs        → Swagger UI loads
POST <URL>/api/v1/analyze  → real Groq call with a small test PNG (field name: file)
```

The `analyze` check is the important one: it proves the Groq key, model, and the
full validate → AI → structured-response pipeline all work in the cloud.

Example analyze call:

```bash
curl -X POST "<URL>/api/v1/analyze" -F "file=@some_chart.png;type=image/png"
```

---

## Frontend (static site) **[you]**

The frontend is a Vite single-page app deployed to any static host:

1. In Render, create **New → Static Site** from the same repo.
2. Set **Root Directory** to `apps/frontend`, **Build Command** to `npm run build`,
   and **Publish Directory** to `dist`.
3. Add an environment variable `VITE_API_BASE_URL` = your backend URL from Step 4.
   (Vite inlines it at build time.)
4. Add a rewrite rule so client-side routes work: Source `/*` → Destination
   `/index.html`, Action **Rewrite**. (A `public/_redirects` file is included for
   hosts that read it.)
5. After the frontend is live, update the backend's `CORS_ALLOWED_ORIGINS` to the
   frontend's public URL and redeploy the backend.

---

## Rollback

Render keeps previous deploys. If a deploy is bad: service → **Deploys** tab →
pick the last good deploy → **Rollback**. No repo change needed.
