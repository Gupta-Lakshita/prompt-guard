# Prompt Guard — AI/ML Detection Modules

This directory contains the AI/ML detection layer of Prompt Guard, owned by the AI/ML
role in the shared API contract. The backend calls these three functions
directly; their names and output shapes must not change without updating the contract.

## Modules

| Module | Function | Purpose |
| --- | --- | --- |
| `rule_engine.py` | `detect_rules(prompt)` | Regex/heuristic detection of prompt-injection, jailbreak and social-engineering patterns |
| `classifier.py` | `predict_ml(prompt)` | Fine-tuned DistilBERT classifier for injection/jailbreak intent, with a keyword-heuristic fallback if no trained model is present |
| `pii_detector.py` | `detect_pii(prompt)` | Presidio + spaCy NER sensitive-data detection, with a regex/Luhn-checksum fallback if Presidio/spaCy aren't installed |

## Output contracts (unchanged)

```python
detect_rules(prompt) -> {
    "rule_score": 0-100,
    "threats": ["PROMPT_INJECTION" | "JAILBREAK" | "SENSITIVE_DATA" | "SOCIAL_ENGINEERING", ...],
    "signals": [{"type": "RULE", "message": str, "severity": 0-100, "confidence": None}, ...],
}

predict_ml(prompt) -> {
    "label": "PROMPT_INJECTION" | "JAILBREAK" | None,
    "confidence": 0.0-1.0,
}

detect_pii(prompt) -> {
    "data_leakage_severity": 0-100,
    "pii": [{"type": str, "text": str, "severity": 0-100}, ...],
}
```

These three functions do **not** compute the final risk score or the
ALLOW/SANITIZE/BLOCK decision — that is the backend's responsibility
(`Risk Score = 0.45 * ML confidence(0-100) + 0.30 * data_leakage_severity + 0.25 * rule_score`).
The backend imports these functions by name and is unaffected by the internal
swap from heuristic to trained model — only the *inside* of `predict_ml()` and
`detect_pii()` changed.

## The ML classifier: dataset, training, evaluation

### Dataset

`ai_ml/training/build_dataset.py` builds a 3-class (NORMAL / PROMPT_INJECTION /
JAILBREAK) dataset from **4 of the 5 sources named in the project synopsis's
own dataset table (Section 5.3)**, using the exact source→class role the
synopsis assigns each one:

- **deepset/prompt-injections** (Hugging Face) — 546 examples, binary
  legit/injection labels. Legit → NORMAL, injection → PROMPT_INJECTION. Ref [15].
- **TrustAIRLab/in-the-wild-jailbreak-prompts** (the dataset behind Shen et
  al., *"Do Anything Now"*) — 1,405 real-world jailbreak prompts collected
  from Reddit/Discord/prompt-sharing sites; a random sample of 400 (the
  synopsis's own target size) is used for the JAILBREAK class. Ref [5].
- **JailbreakBench / JBB-Behaviors** (Hugging Face) — 100 harmful + 100
  benign behaviours, used in full. Harmful → JAILBREAK, benign → NORMAL,
  per the synopsis's "primary labelled jailbreak/benign pair set" role. Ref [4].
- **AdvBench** (Zou et al.; fetched from the original `llm-attacks` GitHub
  release CSV — the Hugging Face mirror is gated) — 520 harmful/adversarial
  instructions; 250 sampled (the synopsis's own target size) → PROMPT_INJECTION,
  per the synopsis's "adversarial-suffix and harmful-instruction style
  injection examples" role. Ref [3].
- **XSTest** (Hugging Face, `Paul/XSTest`) — only the 250-example "safe"
  subset is used, as NORMAL, specifically for the over-refusal/false-positive
  reduction purpose XSTest was built for (Section 3.1). The 200-example
  "unsafe" subset is harmful-content requests, not injection/jailbreak
  patterns, so it's deliberately **not** folded into PROMPT_INJECTION/
  JAILBREAK — that would mislabel a different threat class as this
  classifier's target. Ref [7].
- ~40 hand-written benign prompts, including everyday task prompts and,
  after an evaluation finding (see Known limitations below), prompts that
  mention contact info in an ordinary, non-adversarial context (e.g. *"My
  email is john.doe@example.com, please send the invoice there"*) — added
  specifically to reduce a PII-triggers-false-injection-flag failure mode.
- **HarmBench is intentionally not included** — the synopsis itself reserves
  it for adversarial/red-team evaluation from the Minor Project stage
  onward (Section 5.3), not Micro-stage classifier training.

After deduplication and length filtering: **1,793 examples** — NORMAL 791,
PROMPT_INJECTION 508, JAILBREAK 494 — split **70/15/15**, stratified by class
(train 1,255 / val 269 / test 269). The built CSVs are not committed to git
(see below); re-run `build_dataset.py` to regenerate the exact same split.

This is still smaller than the ~3,900-prompt target in the synopsis (which
also folds in ~500 synthetic-PII prompts and ~300 more hand-curated benign
prompts than are used here), but now covers 4 of 5 named sources at close to
their specified sample sizes, up from 2 of 5 in an earlier pass (see git
history for that ~1,048-example version and its evaluation numbers).

### Training

`ai_ml/training/train_classifier.py` fine-tunes `distilbert-base-uncased`
(Hugging Face `transformers`, CPU) for 4 epochs, batch size 16, learning rate
2e-5, selecting the checkpoint with the best validation F1. Run:

```bash
pip install -r ai_ml/requirements.txt
python -m spacy download en_core_web_sm
python ai_ml/training/build_dataset.py
python ai_ml/training/train_classifier.py
python ai_ml/training/evaluate.py
```

This produces `ai_ml/models/distilbert-promptguard/`, which `classifier.py`
loads automatically at runtime (lazily, on first call to `predict_ml()`).

**The trained checkpoint (~260MB) is intentionally not committed to git** —
GitHub rejects files over 100MB on a normal push, and a checkpoint is a
reproducible build artifact, not source. If `ai_ml/models/distilbert-promptguard/`
doesn't exist (e.g. right after a fresh clone, before training has been run),
`predict_ml()` automatically falls back to the original keyword-heuristic
implementation and logs a warning — the backend keeps working either way,
just with lower-quality ML signal until training is run.

### Evaluation results (held-out test set, 269 examples)

| Metric | Value |
| --- | --- |
| Accuracy | 0.870 |
| Precision (macro) | 0.878 |
| Recall (macro) | 0.860 |
| F1-score (macro) | 0.865 |

| Class | Precision | Recall | F1-score | Support |
| --- | --- | --- | --- | --- |
| NORMAL | 0.889 | 0.941 | 0.914 | 119 |
| PROMPT_INJECTION | 0.807 | 0.882 | 0.843 | 76 |
| JAILBREAK | 0.933 | 0.757 | 0.836 | 74 |

Confusion matrix (rows = true, columns = predicted):

| | NORMAL | PROMPT_INJECTION | JAILBREAK |
| --- | --- | --- | --- |
| NORMAL | 112 | 6 | 1 |
| PROMPT_INJECTION | 6 | 67 | 3 |
| JAILBREAK | 8 | 10 | 56 |

Full report + plotted confusion matrix: `ai_ml/training/results/evaluation_report.md`
and `ai_ml/training/results/confusion_matrix.png` — both suitable for the
project report/PPT. Regenerate with `python ai_ml/training/evaluate.py` after
any retrain.

**Honest before/after of enlarging the dataset (1,048 → 1,793 examples,
2 → 4 of the 5 synopsis-named sources):** macro F1 went from 0.928 to
0.865, and NORMAL false-positive rate from 0% to 5.9% (7/119) — both still
essentially at or just past the synopsis's Micro-stage targets (F1 macro
≥0.85: met at 0.865; NORMAL FPR ≤5%: 5.9%, just over). This is a real
trade-off, not a bug: the earlier, smaller dataset was easier because
deepset/prompt-injections + TrustAIRLab jailbreak are two stylistically
distinct, internally-consistent corpora. Adding JailbreakBench and AdvBench
introduced a harder ambiguity — **JailbreakBench's harmful "Goal" prompts and
AdvBench's harmful instructions are both short, direct harmful-task requests
that read almost identically at the surface level, yet the synopsis's own
Section 5.3 table assigns them to different classes (JBB harmful →
JAILBREAK, AdvBench → PROMPT_INJECTION)**. The confusion matrix shows this
directly: 10 of 74 true JAILBREAK test examples were misclassified as
PROMPT_INJECTION (most of JAILBREAK's recall drop), consistent with that
class-boundary ambiguity rather than a general quality regression —
PROMPT_INJECTION recall actually *improved* (0.795 → 0.882) with the larger,
more diverse injection data. This is worth stating plainly in the report
as a discussion point: a broader, more realistic dataset can make a
classification problem measurably harder, and "bigger dataset, worse
top-line accuracy" is a legitimate, explainable outcome — not evidence the
larger run is inferior.

### Qualitative testing across categories

`ai_ml/training/manual_test_cases.py` runs `detect_rules()` / `predict_ml()`
/ `detect_pii()` together against hand-picked prompts spanning normal,
prompt-injection, jailbreak, PII, mixed injection+PII, and known tricky
false-positive/false-negative probes. Output:
`ai_ml/training/results/manual_test_report.md`. The same cases are also
asserted in `ai_ml/tests/test_integration_cases.py`.

## Known limitations (found during testing, not glossed over)

- **PII-plus-task-framing false positive (fixed, and still fixed after the
  dataset was enlarged).** Initial training data had too few benign examples
  that mention an email/phone in an ordinary request ("My email is X, please
  process this"). The first-trained model flagged these as PROMPT_INJECTION
  with ~0.8 confidence. Fixed by adding more such examples to the NORMAL
  class; still correct after the later dataset expansion (`label: null`,
  confidence ~0.11 on the original failing case). See `manual_test_report.md`.
- **JAILBREAK vs. PROMPT_INJECTION confusion — got more pronounced after
  enlarging the dataset, not less.** Adding JailbreakBench (harmful →
  JAILBREAK) and AdvBench (harmful → PROMPT_INJECTION) means two classes now
  both contain short, direct "do this harmful thing" style text — the
  surface style that used to reliably separate JAILBREAK (long roleplay
  wrappers) from PROMPT_INJECTION (instruction-override phrasing) is now
  shared across both classes for a subset of examples. Test-set JAILBREAK
  recall dropped from 0.96 (smaller dataset) to 0.76 (larger dataset); the
  confusion matrix shows 10 of 74 true JAILBREAK test examples predicted as
  PROMPT_INJECTION. All three hand-written DAN-style manual test prompts are
  now also predicted PROMPT_INJECTION rather than JAILBREAK. This doesn't
  change the ALLOW/SANITIZE/BLOCK outcome (the backend's risk formula uses
  confidence, not which attack label was assigned — either label confirms
  "this looks like an attack"), but the label itself is less reliable as a
  subclass indicator than before. Likely fix: either merge JBB-harmful into
  PROMPT_INJECTION for consistency with AdvBench's similar style (a contract
  discussion, since it changes the source→class mapping), or add explicit
  jailbreak-wrapper phrasing to the JBB-harmful examples before training.
- **New false positive introduced by the larger dataset:** *"I'll ignore the
  noise outside and focus on finishing this report"* — an XSTest-style
  benign edge case that correctly produced no rule-engine signal — is now
  classified PROMPT_INJECTION by the ML layer at 0.70 confidence (it wasn't
  flagged before the dataset was enlarged). Likely cause: AdvBench/JBB
  examples using imperative, task-instruction phrasing pulled the decision
  boundary closer to ordinary "I'll do X and focus on Y" sentences. Flagged
  here rather than hidden; a targeted data-augmentation pass (more benign
  examples using "ignore"/"disregard" in a non-adversarial sense) is the
  natural next step, the same fix pattern that resolved the PII case above.
- **Fixed: borderline false positive on API keys.** *"Here is my API key:
  sk-ab12cd34ef56gh78ij90kl"* was classified PROMPT_INJECTION at 0.48
  confidence in the smaller dataset; with the larger, more diverse dataset
  it now correctly returns `label: null` (confidence 0.42, still a
  meaningfully elevated residual, appropriately — sharing a raw API key is
  genuinely somewhat risky, just not "injection").
- **`pii_detector.py` PERSON/LOCATION entities (spaCy NER) can false-positive
  on short/ambiguous strings** — e.g. "AI" was tagged LOCATION (severity 15,
  low weight by design) in one manual test case. PERSON/LOCATION severities
  are deliberately set low (20/15) relative to EMAIL/PHONE/CREDIT_CARD/API_KEY/
  GOVERNMENT_ID (40-90) specifically to limit the blast radius of this kind
  of NER noise on the aggregate `data_leakage_severity`.
- **Dataset scale.** 1,793 examples vs. the ~3,900-prompt target dataset
  described in the project synopsis — up from 1,048 (2 of 5 named sources)
  to 1,793 (4 of 5; HarmBench is deliberately deferred, see above). The
  remaining gap is mostly the synopsis's ~500 synthetic-PII prompts and
  ~300 extra hand-curated benign prompts, neither of which is needed for
  *this* classifier's 3-class task (PII is handled by `pii_detector.py`
  separately) — closing it further would mean more hand-written NORMAL
  examples in the style that's been shown to matter (task-framed, mentions
  everyday actions/objects) rather than just more raw volume.

## Running the tests

```bash
pip install -r ai_ml/requirements.txt
python -m spacy download en_core_web_sm
python -m pytest ai_ml/tests -v
```

`ai_ml/tests/test_detectors.py` and `ai_ml/tests/test_integration_cases.py`
exercise `detect_rules`, `predict_ml` and `detect_pii` — including the
normal/injection/jailbreak/PII/mixed/false-positive/false-negative cases
described above. They pass whether or not a trained model is present
(falling back to the heuristic), but exercise the real trained model when
`ai_ml/models/distilbert-promptguard/` exists.
