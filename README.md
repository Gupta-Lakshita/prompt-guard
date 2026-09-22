# Prompt Guard

An explainable security gateway for prompt-injection, jailbreak and sensitive-data-leakage
detection in generative AI systems — the Micro Project build described in
`CSE4_PromptGuard_Synopsis_Final.md`.

A user submits a prompt → the system screens it for prompt injection, jailbreak intent, and
PII/sensitive-data leakage → computes a transparent 0–100 risk score → applies an
ALLOW / SANITIZE / BLOCK decision → logs the event → the dashboard shows what happened and why.

This README summarizes what's actually built and tested against the synopsis, honestly —
including where results fell short of a target, not just where they met it.

## Who owns what

| Person | Part | Directory |
| --- | --- | --- |
| Lakshita | AI/ML — rule engine, ML classifier, PII detector, dataset, training, evaluation | `ai_ml/` |
| Neha | Backend — FastAPI gateway, risk scoring, decision engine, sanitization, logging | `backend/` |
| Raima | Frontend — React + Tailwind scanner UI and dashboard | `frontend/` |

The three integrate through one frozen shared contract (`POST /scan`, exact field names —
see any of the three directories' code comments, which all reference it), so each part was
built and tested independently before end-to-end integration.

## Quickstart

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt -r ai_ml/requirements.txt
python -m spacy download en_core_web_sm
uvicorn backend.main:app --reload   # http://localhost:8000

# Frontend (separate terminal)
cd frontend && npm install && npm run dev   # http://localhost:5173

# AI/ML: reproduce dataset + trained model (optional — falls back to a
# heuristic if skipped, see ai_ml/README.md)
python ai_ml/training/build_dataset.py
python ai_ml/training/train_classifier.py
python ai_ml/training/evaluate.py
```

Verified end-to-end: backend started, hit `POST /scan` live with a real prompt, got back a
fully-shaped contract response with real RULE + ML signals and a computed risk score/decision.
Frontend builds clean (`npm run build`, 45 modules, no errors).

## Objectives (synopsis Section 4) — status

| Objective | Status |
| --- | --- |
| Prompt-intake gateway that screens before reaching a downstream LLM | ✅ `POST /scan` |
| Hybrid rule + ML classifier for injection/jailbreak intent | ✅ `rule_engine.py` + fine-tuned DistilBERT in `classifier.py` |
| NER-based sensitive-data-leakage module | ✅ Presidio + spaCy NER in `pii_detector.py` |
| Transparent weighted risk-scoring algorithm with Allow/Sanitize/Block bands | ✅ `risk_scorer.py` + `decision_engine.py` |
| Automatic sanitization for medium-risk, logged block for high-risk | ✅ `sanitizer.py`, SQLite logging |
| Interactive dashboard: live decision view + searchable/filterable event log | ✅ `DashboardPage.jsx`, `ScannerPage.jsx` |
| Curated/labelled attack dataset + hybrid-vs-baseline benchmark | ✅ dataset built; ⚠️ benchmark is hybrid-only (no separate rule-only baseline run) — see below |

## Deliverables (synopsis Section 6) — status

- ✅ Working FastAPI gateway exposing `POST /scan`
- ✅ Hybrid rule + fine-tuned-transformer injection/jailbreak module
- ✅ Presidio/spaCy PII module
- ✅ Explainable weighted risk-scoring engine with Allow/Sanitize/Block bands and per-signal
  justification (`signals[]` in every response)
- ✅ Automatic sanitization (redaction) for medium-risk prompts
- ✅ React/Tailwind dashboard with live decision view + searchable/filterable event log
- ⚠️ Labelled, stratified evaluation dataset — **1,793 prompts**, not the ~3,900 target (see
  "Where we fell short" below)
- ⚠️ Benchmark report — accuracy/precision/recall/F1/confusion matrix produced
  (`ai_ml/training/results/`), but not benchmarked against a separate rule-only baseline run

## Evaluation metrics (synopsis Section 7) — actual numbers, not invented ones

| Metric | Micro-stage target | Actual | Met? |
| --- | --- | --- | --- |
| Attack Detection Rate (≈ recall on attack classes) | ≥90% | PROMPT_INJECTION 88.2%, JAILBREAK 75.7% | ❌ (JAILBREAK below target) |
| False Positive Rate (benign flagged as attack) | ≤5% | 5.9% (7/119 NORMAL test examples) | ❌ (just over) |
| F1-score (macro) | ≥0.85 | 0.864 | ✅ |
| Sanitization Success Rate | ≥95% | Not separately measured — sanitizer has unit-level test coverage (`backend/tests`) but no dedicated leakage-rate benchmark | ⚠️ not measured |
| Response Latency | <300ms | Not benchmarked | ⚠️ not measured |

Full numbers, per-class precision/recall/F1, and the confusion matrix:
`ai_ml/training/results/evaluation_report.md` and `confusion_matrix.png`.

**Why JAILBREAK recall and FPR came in under target — explained, not hidden:** the dataset
combines JailbreakBench (harmful → JAILBREAK) and AdvBench (harmful → PROMPT_INJECTION) per
the synopsis's own Section 5.3 source→class mapping. Both are short, direct "do this harmful
thing" style text at the surface level — the stylistic signal that used to reliably separate
JAILBREAK (long roleplay wrappers, from the TrustAIRLab corpus) from PROMPT_INJECTION
(instruction-override phrasing) is now shared across both classes for a meaningful subset of
examples. The confusion matrix shows this directly: 10 of 74 true JAILBREAK test examples were
predicted PROMPT_INJECTION. This is a real, explainable trade-off from enlarging the dataset
(an earlier, smaller 2-source version scored F1 macro 0.928 and 0% FPR — see git history) —
full before/after and root-cause discussion in `ai_ml/README.md`.

## Technology stack (synopsis Section 8) — as built

| Layer | Synopsis said | What's actually running |
| --- | --- | --- |
| Frontend | React + Tailwind | ✅ React + Tailwind (Vite) |
| Backend | FastAPI | ✅ FastAPI |
| Detection | scikit-learn baseline + fine-tuned DistilBERT + rule engine | ✅ DistilBERT + rule engine. ⚠️ No separate TF-IDF/logistic-regression baseline was trained — the "baseline" comparison point in the results is the rule-only signal, not a trained scikit-learn model |
| Sensitive-data | Presidio + spaCy NER | ✅, with a regex/Luhn fallback if Presidio/spaCy aren't installed |
| Database | SQLite | ✅ SQLite |
| Deployment | Docker, Render/Railway | ❌ not containerized or deployed — runs locally only |

## What's NOT done (honest gaps against the synopsis)

- **Dataset scale:** 1,793 examples vs. the ~3,900 target. HarmBench is deliberately excluded
  (the synopsis itself reserves it for the Minor stage). The gap is mostly the synopsis's
  ~500 synthetic-PII prompts and ~300 extra hand-curated benign prompts, which weren't needed
  for classifier training since PII is handled separately by `pii_detector.py`.
- **No separate scikit-learn (TF-IDF + logistic regression/SVM) baseline was trained** to
  quantify "value added by ML over simple pattern matching" (Section 5.4) — the rule engine's
  own score serves as the closest thing to that baseline in current testing, but it wasn't run
  as a formal head-to-head classifier benchmark.
- **Sanitization Success Rate and Response Latency are not benchmarked** — no dedicated
  measurement scripts exist yet for either metric.
- **No Docker/cloud deployment** — Section 8's Docker/Render/Railway target isn't built; the
  system runs locally via `uvicorn` + `vite dev`.
- **No authentication, RBAC, SHAP/LIME explainability, or adversarial/red-team testing** —
  all explicitly scoped to the Minor stage in the synopsis's own roadmap (Section 5.7), not
  expected at Micro stage.
- **Indirect/embedded prompt injection** (malicious instructions hidden inside retrieved
  documents/tool outputs) is listed as a threat category (Section 5.2) but there's no
  dedicated test coverage for it beyond what the general rule engine happens to catch.

## Running the tests

```bash
python -m pytest ai_ml/tests backend/tests -v
```

65/65 passing (22 AI/ML — `detect_rules`/`predict_ml`/`detect_pii` unit + integration tests
across normal/injection/jailbreak/PII/mixed/false-positive/false-negative cases; 43 backend —
contract shape, scoring, decision bands, sanitization, logging, CORS, endpoints).

Frontend has no automated test suite yet — verified manually via `npm run build` and a live
`/scan` round-trip against the running backend.

## Where to look for more detail

- `ai_ml/README.md` — dataset composition and sourcing, training/eval commands, full metrics,
  confusion matrix, and a running log of known limitations found during testing (including
  ones that were fixed and one that was introduced by later changes).
- `ai_ml/training/results/` — `evaluation_report.md`, `confusion_matrix.png`,
  `manual_test_report.md` (category-by-category qualitative test output).
- `backend/schemas/scan.py` — the exact contract field names/types as enforced in code.
- `frontend/src/services/api.js` — the single file that talks to the backend, per the handoff
  doc's own rule.
