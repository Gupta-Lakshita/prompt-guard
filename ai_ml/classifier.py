"""ML detector for prompt-injection / jailbreak intent.

Contract (see Prompt Guard shared API contract, Section 8/9):
    predict_ml(prompt) -> {
        "label": "PROMPT_INJECTION" | "JAILBREAK" | None,
        "confidence": 0-1
    }

This module does NOT compute the final risk score or ALLOW/SANITIZE/BLOCK decision.
That is the backend's responsibility.

*** TEMPORARY IMPLEMENTATION ***
No trained transformer classifier exists yet. `predict_ml` currently falls back
to a lightweight keyword-scoring heuristic so the backend integration can be
built and tested end-to-end. This is NOT a trained model and its confidence
values are NOT calibrated evaluation results — do not report them as such.
Replace `_predict_ml_temporary` with a real DistilBERT (or similar) classifier
before any benchmark/evaluation numbers are produced.
"""

import re
from typing import Optional


LABEL_PROMPT_INJECTION = "PROMPT_INJECTION"
LABEL_JAILBREAK = "JAILBREAK"

_INJECTION_KEYWORDS = [
    "ignore previous instructions",
    "ignore all previous",
    "disregard the above",
    "disregard your instructions",
    "reveal the system prompt",
    "show me the system prompt",
    "override your instructions",
    "new instructions",
]

_JAILBREAK_KEYWORDS = [
    "dan mode",
    "do anything now",
    "no safety restrictions",
    "act as an unrestricted",
    "pretend you have no",
    "jailbroken",
    "bypass your guidelines",
    "roleplay as someone with no rules",
]


def _normalize(prompt: str) -> str:
    return " ".join(prompt.strip().lower().split())


def _keyword_hits(text: str, keywords) -> int:
    return sum(1 for kw in keywords if kw in text)


def _predict_ml_temporary(prompt: str) -> dict:
    """Temporary heuristic stand-in for the real ML classifier. See module docstring."""
    text = _normalize(prompt)

    injection_hits = _keyword_hits(text, _INJECTION_KEYWORDS)
    jailbreak_hits = _keyword_hits(text, _JAILBREAK_KEYWORDS)

    if injection_hits == 0 and jailbreak_hits == 0:
        return {"label": None, "confidence": 0.0}

    if injection_hits >= jailbreak_hits:
        label = LABEL_PROMPT_INJECTION
        hits = injection_hits
    else:
        label = LABEL_JAILBREAK
        hits = jailbreak_hits

    # Diminishing-returns confidence curve capped below 1.0; not a calibrated probability.
    confidence = min(0.5 + 0.2 * hits, 0.95)
    return {"label": label, "confidence": round(confidence, 2)}


def predict_ml(prompt: Optional[str]) -> dict:
    """Predict prompt-injection/jailbreak intent for a prompt.

    Returns a dict matching the shared contract: label (PROMPT_INJECTION,
    JAILBREAK, or None) and confidence (0-1).
    """
    if not prompt:
        return {"label": None, "confidence": 0.0}

    return _predict_ml_temporary(prompt)
