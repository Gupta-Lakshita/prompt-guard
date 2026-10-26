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
- Uses the **free plan** — no persistent disk (Render's free tier doesn't support them;
  attaching one forces the whole Blueprint onto a paid plan, which is why an earlier
  version of this file didn't offer a free option). SQLite therefore writes to the
  default ephemeral filesystem: the event log **resets on every redeploy or restart**.
  Fine for a demo/submission; not durable. If you later upgrade to a paid plan, add a
  `disk:` block and set `DB_PATH` to a path under its mount to make logging persistent.
- Free-plan instances also **spin down after ~15 minutes of inactivity** and take
  10-30s to wake back up on the next request — the first `/scan` after a quiet period
  will be slow, not broken.
- Leaves a placeholder `CORS_EXTRA_ORIGINS` — after your Vercel deploy has a URL,
  update this env var in the Render dashboard to that URL (comma-separate if you add
  more origins later). Without it, the deployed frontend can't call the deployed
  backend — CORS blocks it.

**Important — the trained ML model isn't in git.** `ai_ml/models/distilbert-promptguard/`
is gitignored (checkpoints are ~260MB, over GitHub's 100MB push limit — see
`ai_ml/README.md`). On a fresh Render deploy, `predict_ml()` automatically falls back
to the keyword-heuristic implementation — the backend still works, just with weaker ML
signal, and (deliberately) **without ever importing torch/transformers at runtime**,
which keeps memory well under the free plan's 512MB limit. The training lines in
`render.yaml`'s `buildCommand` are commented out for this reason — uncommenting them
would load the real DistilBERT model into memory on every request and likely exceed
512MB on the free plan. Only uncomment them (or otherwise ship the trained checkpoint)
if you upgrade off the free plan.

### Diagnosed: free-plan 502s caused by a concurrent-build race, not the ML model

Early deploys hit repeated `502 Bad Gateway` errors with Render logs reporting
`Ran out of memory (used over 512MB)`. The ML model was the obvious suspect, but
measuring it directly ruled that out: `predict_ml()` never imports torch/transformers
when no trained checkpoint is present (confirmed by Render's own logs — "no trained
model found... using the keyword-heuristic fallback"), so it was never the cause.

The real cause, found by instrumenting the actual code: `detect_pii()` lazily builds a
Presidio + spaCy engine on first use, adding ~130MB to the process (measured: 43MB →
175MB on a single build). That alone fits comfortably in 512MB. But the lazy-build
check (`if _analyzer_engine is not None: return it, else build it`) had no lock —
and FastAPI runs sync route handlers in a thread pool, so if several requests arrived
close together right after a cold start (very plausible: Render's free plan spins
down after idle, and a frontend retrying a failed request compounds this), each one
could race past the check and build its **own separate ~130MB copy concurrently**.
3-4 concurrent builds comfortably exceeds 512MB — which matches the repeated,
intermittent (not perfectly reproducible) nature of the crashes.

Fixed in `ai_ml/pii_detector.py` and `ai_ml/classifier.py`: both lazy-builders are now
guarded by a lock, and both expose a `warm_up()` function that `backend/main.py`'s
startup `lifespan` now calls once, synchronously, before the app starts accepting
traffic — so the engine is built exactly once, in a controlled single-threaded way,
instead of racing on the first burst of real requests. Verified directly: 5 concurrent
requests against the old code would have built the engine up to 5 times; against the
fixed code, it builds exactly once (confirmed via instrumented test). The tradeoff is
~1.4s added to cold-start time, which is negligible next to the free plan's existing
10-30s spin-up-from-sleep delay.

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
