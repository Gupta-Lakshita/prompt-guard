"""
Decision engine.

Maps a computed risk score to one of three decisions:
    ALLOW    — 0–34
    SANITIZE — 35–69
    BLOCK    — 70–100

The decision is based SOLELY on the risk score.
PII detection does NOT automatically force SANITIZE — the risk score
formula (in risk_scorer.py) already incorporates PII severity, so if
the resulting score stays below 35 the prompt is still ALLOW.

This module does NOT modify the prompt or compute the risk score.
Those concerns belong to sanitizer.py and risk_scorer.py respectively.
"""

from backend.core.config import THRESHOLD_ALLOW_MAX, THRESHOLD_SANITIZE_MAX

# Allowed decision values (contractually fixed)
DECISION_ALLOW = "ALLOW"
DECISION_SANITIZE = "SANITIZE"
DECISION_BLOCK = "BLOCK"


def make_decision(risk_score: int) -> str:
    """
    Return the appropriate decision string for a given risk score.

    Args:
        risk_score: Integer in [0, 100] produced by compute_risk_score().

    Returns:
        "ALLOW"    if risk_score is 0–34
        "SANITIZE" if risk_score is 35–69
        "BLOCK"    if risk_score is 70–100
    """
    if risk_score <= THRESHOLD_ALLOW_MAX:
        return DECISION_ALLOW
    elif risk_score <= THRESHOLD_SANITIZE_MAX:
        return DECISION_SANITIZE
    else:
        return DECISION_BLOCK
