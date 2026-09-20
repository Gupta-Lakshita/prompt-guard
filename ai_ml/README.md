# Prompt Guard — AI/ML Detection Modules

This directory contains the AI/ML detection layer of Prompt Guard, owned by the AI/ML
role in the [shared API contract](../docs). The backend calls these three functions
directly; their names and output shapes must not change without updating the contract.

## Modules

| Module | Function | Purpose |
| --- | --- | --- |
| `rule_engine.py` | `detect_rules(prompt)` | Regex/heuristic detection of prompt-injection, jailbreak and social-engineering patterns |
| `classifier.py` | `predict_ml(prompt)` | ML-based injection/jailbreak intent detection. **Currently a temporary keyword-heuristic stand-in** — see the module docstring — until a fine-tuned transformer classifier is trained. |
| `pii_detector.py` | `detect_pii(prompt)` | Sensitive-data detection (email, phone, credit card via Luhn check, API keys, government IDs) |

## Output contracts

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

## Running the tests

```bash
python -m pytest ai_ml/tests -v
```

No external dependencies are required for the current implementation. Standard
library `re` and `dataclasses` only.

## Known limitations / next steps

- `classifier.py` is a temporary heuristic, clearly marked in its docstring. It must
  be replaced with a trained transformer (e.g. DistilBERT) before any evaluation
  numbers (accuracy, F1, detection rate) are reported — do not fabricate these.
- `pii_detector.py` uses regex/checksum recognizers only. Swapping in Presidio/spaCy
  NER later can reuse the same `detect_pii(prompt)` signature and output format.
