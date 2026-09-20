"""
Risk scorer.

Owns the final risk score calculation on behalf of the backend.
Neither the frontend nor the AI/ML modules should compute this value.

Formula (from shared project contract):
    Risk Score = 0.45 × (ml_confidence × 100)
               + 0.30 × data_leakage_severity
               + 0.25 × rule_score

ml_confidence  — 0.0–1.0 (from predict_ml); scaled to 0–100 inside here.
data_leakage_severity — 0–100 (from detect_pii).
rule_score     — 0–100 (from detect_rules).

Result is clamped to [0, 100] and returned as an integer.
"""

import math

def compute_risk_score(
    ml_confidence: float,
    data_leakage_severity: int,
    rule_score: int,
) -> int:
    """
    Apply the weighted formula and return an integer risk score in [0, 100].

    Args:
        ml_confidence:          ML classifier confidence, 0.0–1.0.
        data_leakage_severity:  PII severity from detect_pii(), 0–100.
        rule_score:             Highest severity from detect_rules(), 0–100.

    Returns:
        Integer risk score clamped to [0, 100].
    """
    raw_score = (
        0.45 * (ml_confidence * 100)   # scale confidence to 0–100 first
        + 0.30 * data_leakage_severity
        + 0.25 * rule_score
    )
    # Use standard arithmetic rounding (round-half-up) instead of Python's
    # built-in round() which uses banker's rounding (round-half-to-even).
    # This keeps the formula predictable and easy to verify manually.
    return int(max(0, min(100, math.floor(raw_score + 0.5))))
