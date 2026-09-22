# Deploying Prompt Guard

Two separate services — **frontend on Vercel, backend on Render** — matching the tech
stack the project synopsis specifies (Section 8: "Docker containers; hosted on
Render/Railway"). This isn't the only valid split, but it's the one this repo is
configured for.

## Why not all-on-Vercel

The backend depends on `torch` + `transformers` (the fine-tuned DistilBERT classifier)
plus `presidio` + `spacy` — well over 1GB installed, past Vercel's ~250MB unzipped
serverless function limit. It also logs every scan to a SQLite file, which Vercel's
ephemeral serverless filesystem doesn't persist across invocations. Render (or Railway)
runs it as a normal long-lived process instead, so neither issue applies.

## 1. Backend → Render

`render.yaml` at the repo root is a Render Blueprint. In the Render dashboard:
**New → Blueprint**, point it at this repo, and it picks up `render.yaml` automatically.

What it does:
- Installs `backend/requirements.txt` + `ai_ml/requirements.txt` and downloads the
  spaCy model.
- Runs `uvicorn backend.main:app` on Render's assigned `$PORT`.
- Mounts a 1GB persistent disk at `/var/data` and points `DB_PATH` at it, so the SQLite
  event log survives redeploys (the default `promptguard.db` in the repo root would
  otherwise reset on every deploy).
- Leaves a placeholder `CORS_EXTRA_ORIGINS` — after your Vercel deploy has a URL,
  update this env var in the Render dashboard to that URL (comma-separate if you add
  more origins later). Without it, the deployed frontend can't call the deployed
  backend — CORS blocks it.

**Important — the trained ML model isn't in git.** `ai_ml/models/distilbert-promptguard/`
is gitignored (checkpoints are ~260MB, over GitHub's 100MB push limit — see
`ai_ml/README.md`). On a fresh Render deploy, `predict_ml()` automatically falls back
to the keyword-heuristic implementation — the backend still works, just with weaker ML
signal. To deploy with the real trained model, uncomment the two training lines in
`render.yaml`'s `buildCommand` (adds ~15-20 min to every build on the current
1,793-example dataset) — or train once locally and find another way to ship the
checkpoint (e.g. push it to the Hugging Face Hub and have `classifier.py` download it
at startup; that's not wired up yet).

## 2. Frontend → Vercel

`frontend/vercel.json` configures the build. In the Vercel dashboard:
**New Project → import this repo**, and set **Root Directory to `frontend`** (this is a
dashboard project setting, not something `vercel.json` itself can declare for a
monorepo). Vercel then auto-detects Vite and uses the build/output settings from
`frontend/vercel.json`.

Set one environment variable in the Vercel project settings:

| Variable | Value |
| --- | --- |
| `VITE_API_BASE_URL` | Your Render backend's URL, e.g. `https://prompt-guard-backend.onrender.com` |

(`frontend/src/services/api.js` already reads this — falls back to
`http://localhost:8000` if unset, which is only correct for local dev.)

## 3. Order of operations

1. Deploy the backend to Render first — you need its URL for the frontend's env var.
2. Deploy the frontend to Vercel with `VITE_API_BASE_URL` set to that Render URL.
3. Go back to the Render service's env vars and set `CORS_EXTRA_ORIGINS` to the Vercel
   URL you just got, then redeploy the backend (env var changes require a redeploy on
   Render).
4. Open the Vercel URL, submit a prompt, confirm you get a real response (not a CORS
   error or a network error).

## Local development (unaffected by any of this)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt -r ai_ml/requirements.txt
python -m spacy download en_core_web_sm
uvicorn backend.main:app --reload        # :8000

cd frontend && npm install && npm run dev  # :5173, talks to localhost:8000 by default
```
