# Prompt Guard

**An explainable security gateway for prompt-injection, jailbreak, and sensitive-data-leakage
detection in generative AI systems.**

Micro Project build for `CSE4_PromptGuard_Synopsis_Final.md`. This document is written to
double as the basis for the Micro Project report/presentation: what was built, what was
measured (with real numbers, not estimates), and what fell short of a target and why.

> **Live demo:** frontend on Vercel, backend on Render — see [Deployment](#deployment) for URLs
> and setup, [DEPLOYMENT.md](DEPLOYMENT.md) for the full guide and a real incident writeup.

---

## 1. Problem & Objectives

LLM-integrated applications accept free-form user prompts, which creates three risks a
conventional input-validation layer doesn't catch:

1. **Prompt injection** — a user tries to override the system's instructions ("ignore previous
   instructions and...").
2. **Jailbreak attempts** — a user tries to bypass the model's safety alignment via role-play,
   persona framing, or explicit "no restrictions" framing.
3. **Sensitive-data leakage** — a user (often unintentionally) pastes PII, credentials, or other
   sensitive data into a prompt that then gets sent to a downstream model/log.

Prompt Guard sits between the user and the downstream LLM as a **pre-processing gateway**:
every prompt is screened, scored (0–100, explainable), and routed to **ALLOW / SANITIZE /
BLOCK** before it reaches the model. Every decision is logged and explorable via a dashboard,
so the reasoning behind any decision is auditable after the fact — not a black box.

**Synopsis objectives (Section 4) and their status:**

| Objective | Status |
| --- | --- |
| Prompt-intake gateway that screens before reaching a downstream LLM | ✅ `POST /scan` |
| Hybrid rule + ML classifier for injection/jailbreak intent | ✅ rule engine + fine-tuned DistilBERT |
| NER-based sensitive-data-leakage module | ✅ Presidio + spaCy NER |
| Transparent weighted risk-scoring algorithm with decision bands | ✅ `risk_scorer.py` + `decision_engine.py` |
| Automatic sanitization / logged block | ✅ `sanitizer.py`, SQLite logging |
| Interactive dashboard: live decision view + searchable event log | ✅ `DashboardPage.jsx` |
| Curated/labelled attack dataset + hybrid-vs-baseline benchmark | ✅ 2,593-example dataset; scikit-learn baseline trained and compared |

---

## 2. System Architecture

```
User Prompt
   │
   ▼
React Frontend (Vite, Tailwind)  ──POST /scan──▶  FastAPI Backend
   ▲                                                   │
   │                                        normalize_prompt()
   │                                                   │
   │                              ┌────────────────────┼────────────────────┐
   │                              ▼                     ▼                    ▼
   │                      detect_rules()         predict_ml()         detect_pii()
   │                      (regex/heuristic)   (DistilBERT, with     (Presidio + spaCy,
   │                                          keyword fallback)      regex/Luhn fallback)
   │                              │                     │                    │
   │                              └────────────────────┬────────────────────┘
   │                                                    ▼
   │                                       compute_risk_score() — weighted formula
   │                                                    │
   │                                                    ▼
   │                                       make_decision() — ALLOW/SANITIZE/BLOCK
   │                                                    │
   │                                     sanitize_prompt() if SANITIZE
   │                                                    │
   │                                          insert_event() → SQLite
   │                                                    │
   └────────────────── ScanResponse (JSON) ◀────────────┘
```

Three independently-built, independently-tested components integrate through **one frozen
shared contract** — `POST /scan`, exact field names (`scan_id`, `original_prompt`,
`sanitized_prompt`, `risk_score`, `decision`, `threats`, `signals`, `pii`, `timestamp`). No
component computes logic that belongs to another: the AI/ML layer never decides ALLOW/SANITIZE/
BLOCK, the frontend never computes a risk score, the backend never reimplements detection logic.

### Repository layout

```
ai_ml/          Rule engine, ML classifier, PII detector, dataset/training/evaluation scripts
backend/        FastAPI gateway — scan orchestration, risk scoring, decision, sanitization, logging
frontend/       React + Tailwind — scanner page, dashboard, API client
render.yaml, backend/Dockerfile, frontend/Dockerfile, docker-compose.yml   Deployment config
DEPLOYMENT.md   Full deployment guide + a real production-incident writeup
```

---

## 3. Team & Contributions

| Person | Part | Owns |
| --- | --- | --- |
| Lakshita | AI/ML | `ai_ml/` — rule engine, ML classifier, PII detector, dataset curation, training, evaluation, benchmarking |
| Neha | Backend | `backend/` — FastAPI gateway, risk scoring formula, decision engine, sanitization, SQLite logging |
| Raima | Frontend | `frontend/` — React + Tailwind scanner UI and dashboard |

Each part was built and unit-tested independently against the frozen contract before
integration, which is why the contract (not any one person's internal implementation) is the
thing that must never change without all three agreeing.

---

## 4. Methodology

### 4.1 Rule engine (`ai_ml/rule_engine.py`)

Regex/heuristic layer, normalizes input (lowercase, collapsed whitespace) and matches known
attack phrasing:

- **Prompt injection patterns:** "ignore all/the/your previous instructions", "disregard
  the above/your previous instructions", "forget all previous instructions", "reveal the
  system prompt / hidden instructions / hidden information", "show me the system prompt",
  "override your instructions", "ignore all safety policies/rules".
- **Jailbreak patterns:** "enable developer mode", "you are now in developer mode / an
  unrestricted AI", "act as an unrestricted assistant", "no safety restrictions/limitations",
  "disable/bypass safety restrictions", "ignore safety policies", DAN mode / "do anything now".

This is the fast, fully auditable first line of defence — cheap, but evadable by paraphrasing,
which is exactly why the ML layer exists alongside it (defense in depth, not either/or).

### 4.2 ML classifier (`ai_ml/classifier.py`)

A fine-tuned **DistilBERT** sequence classifier for 3-class NORMAL / PROMPT_INJECTION /
JAILBREAK classification, trained via `ai_ml/training/train_classifier.py`
(`distilbert-base-uncased`, 4 epochs, batch size 16, lr 2e-5, best-validation-F1 checkpoint
selection).

**The trained checkpoint (~260MB) is not committed to git** — GitHub rejects files over 100MB,
and it's a reproducible build artifact, not source. `predict_ml()` lazily loads it if present;
if absent (e.g. a fresh clone before training is run), it **automatically falls back to a
keyword heuristic** so the backend never breaks either way. This fallback is also deliberately
the only thing ever deployed to Render (see [Deployment](#deployment)) — loading the real model
would exceed the free tier's memory budget.

### 4.3 PII detector (`ai_ml/pii_detector.py`)

Primary path: **Microsoft Presidio** (`AnalyzerEngine`) + **spaCy NER** (`en_core_web_sm`),
covering EMAIL, PHONE, CREDIT_CARD (regex + Luhn check), API_KEY (custom pattern recognizer —
Presidio has no built-in one), GOVERNMENT_ID, and NER-derived PERSON/LOCATION. Fallback: a
deterministic regex/Luhn-checksum implementation if Presidio/spaCy aren't installed — same
function signature, same output shape, so the rest of the system never has to know which path
ran.

### 4.4 Dataset (`ai_ml/training/build_dataset.py`)

A 3-class (NORMAL / PROMPT_INJECTION / JAILBREAK) dataset assembled from **every data-source
role the synopsis names** (Section 5.3):

| Source | Role | Size used |
| --- | --- | --- |
| deepset/prompt-injections | legit→NORMAL, injection→PROMPT_INJECTION | 546 |
| TrustAIRLab in-the-wild jailbreak corpus (Shen et al., *"Do Anything Now"*) | →JAILBREAK | 400 sampled |
| JailbreakBench / JBB-Behaviors | harmful→JAILBREAK, benign→NORMAL | 100+100 (full) |
| AdvBench (Zou et al., via the original GitHub CSV) | harmful instructions→PROMPT_INJECTION | 250 sampled |
| XSTest ("safe" subset only) | →NORMAL, for over-refusal/false-positive reduction | 250 |
| Hand-written benign prompts (incl. PII-in-context) | →NORMAL | ~40 |
| **Synthetic PII-bearing benign prompts** (Faker-generated identities in task templates) | →NORMAL | ~500 |
| **Template-expanded benign prompts** (8 action templates × 40 topics) | →NORMAL | ~300 |

HarmBench is deliberately excluded — the synopsis itself reserves it for Minor-stage
adversarial/red-team evaluation, not Micro-stage classifier training.

**Result: 2,593 examples** (NORMAL 1,591 / PROMPT_INJECTION 508 / JAILBREAK 494) after
dedup/length filtering, split **70/15/15 stratified** (train 1,815 / val 389 / test 389). Built
CSVs are gitignored (the jailbreak/harmful source text is appropriate as local training data
but not to publish verbatim) — re-run `build_dataset.py` (fixed seed) to reproduce exactly.

Still short of the synopsis's ~3,900-prompt target, but every named dataset *role* is now
represented — the remaining gap is raw volume per source, not a missing technique.

---

## 5. Risk Scoring & Decision Pipeline

Computed in `backend/core/risk_scorer.py`:

$$\text{Base Risk} = 0.50 \times \text{rule\_score} + 0.30 \times (\text{ML\_confidence} \times 100) + 0.20 \times \text{PII\_severity}$$

- Clamped to `[0, 100]`, rounded (`math.floor(base_risk + 0.5)`).
- **Safety floor:** if `rule_score >= 70`, the final score is forced to at least 70 — a
  strong rule match can never be out-voted into ALLOW by low ML confidence or PII severity.

**Decision thresholds** (`backend/core/decision_engine.py`), mapped deterministically:

| Score | Decision | Behaviour |
| --- | --- | --- |
| 0–34 | ALLOW | Prompt forwarded unmodified |
| 35–69 | SANITIZE | PII entities redacted (`[TYPE_REDACTED]`), sanitized prompt forwarded |
| 70–100 | BLOCK | Prompt rejected, event logged with full justification |

Risk score and decision are strictly aligned by construction — a contradictory output (e.g.
score 80 + ALLOW) is structurally impossible, not just untested.

---

## 6. Results & Evaluation

### 6.1 DistilBERT classifier (held-out test set, 389 examples)

| Metric | Target (synopsis Section 7) | Actual | Met? |
| --- | --- | --- | --- |
| Attack Detection Rate (PROMPT_INJECTION recall) | ≥90% | **90.8%** | ✅ |
| Attack Detection Rate (JAILBREAK recall) | ≥90% | 86.5% | ❌ (near target) |
| False Positive Rate (benign flagged as attack) | ≤5% | **2.1%** (5/239) | ✅ |
| F1-score (macro) | ≥0.85 | **0.919** | ✅ |
| Sanitization Success Rate | ≥95% | 92.7% (278/300) | ❌ (just under) |
| Response Latency (p95, in-process) | <300ms | **43.9ms** | ✅ |

4 of 6 synopsis evaluation targets met; the two misses are explained with root causes below, not
just reported as numbers.

Per-class breakdown and confusion matrix: `ai_ml/training/results/evaluation_report.md` /
`confusion_matrix.png`.

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| NORMAL | 0.975 | 0.979 | 0.977 | 239 |
| PROMPT_INJECTION | 0.885 | 0.908 | 0.896 | 76 |
| JAILBREAK | 0.901 | 0.865 | 0.883 | 74 |

### 6.2 scikit-learn baseline comparison

Synopsis Section 5.4 explicitly requires quantifying "the value added by ML over simple pattern
matching" — `ai_ml/training/train_baseline.py` trains TF-IDF+Logistic Regression and
TF-IDF+Linear SVM on the **identical** train/test split:

| Model | Accuracy | F1 (macro) |
| --- | --- | --- |
| TF-IDF + Logistic Regression | 0.918 | 0.892 |
| TF-IDF + Linear SVM | 0.941 | **0.923** |
| DistilBERT (fine-tuned transformer) | **0.943** | 0.919 |

**Reported as measured:** the Linear SVM baseline's macro F1 is marginally *higher* than
DistilBERT's (+0.004). On a dataset this size, with fairly distinct lexical signals per class, a
strong classical baseline is genuinely competitive with the transformer — a legitimate finding
worth stating in the report, not a result to massage. Full breakdown:
`ai_ml/training/results/baseline_vs_distilbert.md`.

### 6.3 Why JAILBREAK recall is still under target

JailbreakBench (harmful→JAILBREAK) and AdvBench (harmful→PROMPT_INJECTION) both contain short,
direct "do this harmful thing" style text that reads almost identically at the surface level —
yet the synopsis's own source→class mapping assigns them to *different* classes. This creates a
genuine class-boundary ambiguity the model can't fully resolve. Three dataset iterations show the
trend clearly:

| Dataset version | Examples | Macro F1 | NORMAL FPR | PROMPT_INJECTION recall | JAILBREAK recall |
| --- | --- | --- | --- | --- | --- |
| v1 (2/5 sources) | 1,048 | 0.928 | 0% | 79.5% | 96.2% |
| v2 (+JailbreakBench, AdvBench) | 1,793 | 0.865 | 5.9% | 88.2% | 75.7% |
| **v3 (current, +synthetic PII, +extra benign)** | **2,593** | **0.919** | **2.1%** | **90.8%** | 86.5% |

v2 traded JAILBREAK recall for broader source coverage; v3's extra NORMAL-class data recovered
the FPR and PROMPT_INJECTION losses (and then some — v3's FPR beats even v1's) but couldn't
recover JAILBREAK recall, because more *benign* data doesn't resolve an ambiguity between two
*attack* classes. Full discussion: `ai_ml/aiml.md`.

### 6.4 Why Sanitization Success Rate is just under target

Benchmarked directly (`ai_ml/training/benchmark_sanitization.py`): 300 prompts with known
ground-truth PII values run through the real `detect_pii()` → `sanitize_prompt()` pipeline.
22 failures (92.7% success) — nearly all are phone numbers in formats `detect_pii()` doesn't
match (synthetic numbers with extensions like `311.279.8843x81667`, or unusual international
grouping). A real, specific PII-detection coverage gap, not a redaction bug: whatever isn't
detected can't be redacted. Root-cause detail:
`ai_ml/training/results/sanitization_benchmark.md`.

---

## 7. Interactive Dashboard

`frontend/src/pages/DashboardPage.jsx` reads live from `GET /events` (backed by SQLite, no
mock/hardcoded data):

- Aggregate metrics — total scans, ALLOW/SANITIZE/BLOCK counts
- Threat-category breakdown — PROMPT_INJECTION / JAILBREAK / SENSITIVE_DATA / SOCIAL_ENGINEERING
- Live event log — timestamp, prompt, risk score, decision badge, threat chips
- Search/filter by decision or prompt text/scan ID
- Expandable rows — per-signal breakdown (RULE/ML/PII) and original-vs-sanitized diff

---

## 8. Testing

```bash
python -m pytest ai_ml/tests backend/tests -v
```

**66/66 passing:**
- 22 AI/ML tests — `detect_rules`/`predict_ml`/`detect_pii` unit + integration tests across
  normal/injection/jailbreak/PII/mixed/false-positive/false-negative cases.
- 44 backend tests — contract shape, scoring, decision bands, sanitization, logging, CORS,
  endpoints.

Plus 4 dedicated benchmark scripts (not unit tests — measurement tools) in `ai_ml/training/`:
`evaluate.py`, `train_baseline.py`, `benchmark_latency.py`, `benchmark_sanitization.py`, each
writing a report to `ai_ml/training/results/`.

Frontend has no automated test suite yet — verified manually via `npm run build` and live
`/scan`/`/events` round-trips against a running backend, including against the deployed
instances (not just localhost).

---

## 9. Deployment

Two services, matching the synopsis's own Section 8 plan (Docker, Render/Railway):

- **Backend → Render** (free tier), via `render.yaml` Blueprint
- **Frontend → Vercel**, via `frontend/vercel.json`

Both are **actually deployed**, not just configured — `https://prompt-guard-backend-ob5u.onrender.com`
and `https://prompt-guard-lyart.vercel.app` (URLs specific to this build; see `DEPLOYMENT.md`
for how to point your own fork at new ones).

Also fully **containerized**: `backend/Dockerfile`, `frontend/Dockerfile`,
`docker-compose.yml` — `docker compose up --build` runs both services locally, confirmed
working end-to-end (startup logs clean, no errors) on a real machine.

### Real incidents found and fixed post-deploy

Worth including in the report as engineering-process evidence, not just the end state — three
real production issues were diagnosed and fixed after initial deployment, each confirmed by
direct measurement rather than guesswork:

1. **Concurrent-request race** (502s, intermittent OOM): the PII-engine lazy-singleton had no
   lock, so FastAPI's thread pool could build multiple ~130MB copies of it concurrently under
   load right after a cold start. Fixed with a lock + eager startup warm-up.
2. **The real memory cause** (958MB on startup, instantly exceeding Render's 512MB free-tier
   limit): `render.yaml` installed the *full* training requirements file (with `transformers`
   → `torch`) into the deployed environment. Even though `predict_ml()` never imports torch at
   runtime, spaCy's backend auto-imports it just because it's present. Proved with a controlled
   side-by-side test (888MB with torch installed vs. 105MB without, for the identical
   `import presidio_analyzer` statement). Fixed with a separate lean
   `ai_ml/requirements-runtime.txt`, bringing real measured startup memory down to ~172MB.
3. **CORS misconfiguration**: `CORS_EXTRA_ORIGINS` was left at its placeholder value, so the
   deployed frontend's requests were silently blocked by the browser (surfacing as a generic
   "can't reach backend" error, not an obvious CORS error). Fixed by setting it to the real
   Vercel origin and verified via a direct preflight request.

Full writeup with the actual measurements, commands, and before/after numbers:
[DEPLOYMENT.md](DEPLOYMENT.md).

---

## 10. Technology Stack

| Layer | Synopsis said | What's running |
| --- | --- | --- |
| Frontend | React + Tailwind | ✅ React + Tailwind (Vite) |
| Backend | FastAPI | ✅ FastAPI — `POST /scan`, `GET /events`, `GET /health` |
| Detection | scikit-learn baseline + fine-tuned DistilBERT + rule engine | ✅ all three |
| Sensitive-data | Presidio + spaCy NER | ✅, with regex/Luhn fallback |
| Database | SQLite | ✅ (`promptguard.db`, `events` table) |
| Deployment | Docker, Render/Railway | ✅ Dockerized + actually deployed (Render + Vercel) |

---

## 11. Honest Gaps Against the Synopsis

Not everything is done — listed plainly rather than omitted:

- **Dataset scale:** 2,593 vs. ~3,900 target. Every named source *role* is represented; the
  remainder is volume, not a missing technique.
- **JAILBREAK recall (86.5%)** still under the 90% target — a labelled-data class-boundary
  issue between two sources (§6.3), not something more volume alone fixes.
- **Sanitization Success Rate (92.7%)** just under the 95% target — a specific, root-caused
  phone-number-format detection gap (§6.4), benchmarked not estimated.
- **No authentication, RBAC, SHAP/LIME explainability, or adversarial/red-team testing** — all
  explicitly scoped to the Minor stage in the synopsis's own roadmap (Section 5.7).
- **Indirect/embedded prompt injection** (malicious instructions hidden inside retrieved
  documents/tool outputs) is a named threat category (Section 5.2) with no dedicated test
  coverage beyond what the general rule engine happens to catch.
- **Frontend has no automated test suite.**

---

## 12. Quickstart

```bash
# Backend (from repo root)
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt -r ai_ml/requirements.txt
python -m spacy download en_core_web_sm
uvicorn backend.main:app --reload --port 8000   # http://localhost:8000

# Frontend (separate terminal)
cd frontend && npm install && npm run dev   # http://localhost:5173

# AI/ML: reproduce dataset + trained model + all benchmarks (optional — the
# local demo automatically uses the fallback classifier without this)
python ai_ml/training/build_dataset.py
python ai_ml/training/train_classifier.py
python ai_ml/training/evaluate.py
python ai_ml/training/train_baseline.py
python ai_ml/training/benchmark_latency.py
python ai_ml/training/benchmark_sanitization.py
```

Or run both services as containers:

```bash
docker compose up --build   # http://localhost:8080
```

---

## 13. Where to Look for More Detail

- `ai_ml/aiml.md` — full dataset sourcing, training/eval commands, all metrics, confusion
  matrix, and a running log of known limitations (including ones found, fixed, and
  reintroduced across dataset iterations).
- `DEPLOYMENT.md` — deployment guide + the full production-incident writeup (§9).
- `ai_ml/rule_engine.py` / `classifier.py` / `pii_detector.py` — detection implementations.
- `ai_ml/training/` — dataset build, training, evaluation, baseline, and benchmark scripts;
  `ai_ml/training/results/` — their generated reports.
- `backend/core/risk_scorer.py` / `decision_engine.py` — scoring formula and thresholds.
- `backend/sanitizer/sanitizer.py` — redaction logic.
- `backend/schemas/scan.py` — exact contract field names/types.
- `frontend/src/pages/DashboardPage.jsx` / `services/api.js` — dashboard and API client.
