"""ML detector for prompt-injection / jailbreak intent.

Contract (see Prompt Guard shared API contract, Section 8/9):
    predict_ml(prompt) -> {
        "label": "PROMPT_INJECTION" | "JAILBREAK" | None,
        "confidence": 0-1
    }

This module does NOT compute the final risk score or ALLOW/SANITIZE/BLOCK decision.
That is the backend's responsibility.

Primary implementation: a DistilBERT sequence classifier fine-tuned on a
3-class (NORMAL / PROMPT_INJECTION / JAILBREAK) dataset built from
deepset/prompt-injections and the TrustAIRLab in-the-wild jailbreak corpus
(see ai_ml/training/). The trained checkpoint lives at
ai_ml/models/distilbert-promptguard/ once produced by
`python ai_ml/training/train_classifier.py`; it is NOT committed to git
(checkpoints are ~260MB, over GitHub's 100MB push limit, and are
reproducible from the training scripts + a fixed seed).

Fallback: if the trained checkpoint isn't present (e.g. a fresh clone before
training has been run) or torch/transformers aren't installed, predict_ml()
falls back to the original lightweight keyword-heuristic so the backend
integration never breaks. A warning is logged (once) when this happens —
that fallback's confidence values are NOT calibrated model output and must
not be reported as evaluation results.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

LABEL_PROMPT_INJECTION = "PROMPT_INJECTION"
LABEL_JAILBREAK = "JAILBREAK"
LABEL_NORMAL = "NORMAL"  # internal only — the contract's label for this case is None

_DEFAULT_MODEL_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "models", "distilbert-promptguard"
)
MODEL_DIR = os.environ.get("PROMPT_GUARD_ML_MODEL_DIR", _DEFAULT_MODEL_DIR)
_MAX_LENGTH = 256

_model = None
_tokenizer = None
_model_unavailable = False


def _try_load_model() -> None:
    """Lazily load the fine-tuned classifier on first use. Cheap no-op after that."""
    global _model, _tokenizer, _model_unavailable

    if _model_unavailable or _model is not None:
        return

    if not os.path.isdir(MODEL_DIR):
        _model_unavailable = True
        logger.warning(
            "predict_ml(): no trained model found at %s. Using the temporary "
            "keyword-heuristic fallback instead. Run "
            "`python ai_ml/training/train_classifier.py` to produce a trained model.",
            MODEL_DIR,
        )
        return

    try:
        import torch  # noqa: F401
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        _tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
        _model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
        _model.eval()
    except Exception:
        logger.warning(
            "predict_ml(): failed to load trained model from %s; using the "
            "temporary keyword-heuristic fallback instead.",
            MODEL_DIR,
            exc_info=True,
        )
        _model_unavailable = True


def _id2label(pred_id: int) -> str:
    id2label = _model.config.id2label
    return id2label.get(pred_id, id2label.get(str(pred_id)))


def _predict_ml_model(prompt: str) -> dict:
    import torch

    inputs = _tokenizer(prompt, truncation=True, max_length=_MAX_LENGTH, return_tensors="pt")
    with torch.no_grad():
        logits = _model(**inputs).logits[0]
    probs = torch.softmax(logits, dim=-1)

    pred_id = int(torch.argmax(probs).item())
    pred_label = _id2label(pred_id)
    pred_prob = float(probs[pred_id].item())

    if pred_label == LABEL_NORMAL:
        # Residual risk signal: probability mass the model still assigned to a
        # malicious class even though NORMAL won the argmax. This keeps a
        # partial signal available to the backend's risk formula instead of a
        # hard 0, while still reporting label=None per the contract.
        malicious_mass = 1.0 - pred_prob
        return {"label": None, "confidence": round(malicious_mass, 2)}

    return {"label": pred_label, "confidence": round(pred_prob, 2)}


# --------------------------------------------------------------------------
# Temporary keyword-heuristic fallback (used when no trained model is present).
# --------------------------------------------------------------------------

_INJECTION_KEYWORDS = [
    "ignore previous instructions",
    "ignore all previous",
    "disregard the above",
    "disregard your instructions",
    "forget all previous",
    "forget previous instructions",
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


def _predict_ml_fallback(prompt: str) -> dict:
    """Temporary heuristic stand-in for the trained classifier. See module docstring."""
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
    JAILBREAK, or None) and confidence (0-1). Uses the trained DistilBERT
    classifier when available, otherwise the temporary keyword heuristic.
    """
    if not prompt:
        return {"label": None, "confidence": 0.0}

    _try_load_model()
    if _model is not None:
        try:
            return _predict_ml_model(prompt)
        except Exception:
            logger.warning("predict_ml(): trained model inference failed; falling back.", exc_info=True)

    return _predict_ml_fallback(prompt)
