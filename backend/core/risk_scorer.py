"""
Risk scorer.

Owns the final risk score calculation on behalf of the backend.
Neither the frontend nor the AI/ML modules should compute this value.

Formula (Micro Project MVP):
    Base Risk = 0.50 × rule_score
              + 0.30 × (ml_confidence × 100)
              + 0.20 × data_leakage_severity

Safety floor:
    If rule_score >= 70:
        final risk score must be at least 70

ml_confidence          — 0.0–1.0 (from predict_ml); scaled to 0–100.
data_leakage_severity  — 0–100 (from detect_pii).
rule_score             — 0–100 (from detect_rules).

Result is clamped to [0, 100] and returned as an integer.
"""

import math


def compute_risk_score(
    ml_confidence: float,
    data_leakage_severity: int,
    rule_score: int,
) -> int:
    """
    Apply the weighted formula with safety floor and return an integer risk score in [0, 100].

    Args:
        ml_confidence:          ML classifier confidence, 0.0–1.0.
        data_leakage_severity:  PII severity from detect_pii(), 0–100.
        rule_score:             Highest severity from detect_rules(), 0–100.

    Returns:
        Integer risk score clamped to [0, 100].
    """
    ml_confidence_percent = ml_confidence * 100.0

    # Base Risk = 0.50 * rule_score + 0.30 * ML_confidence_percent + 0.20 * PII_severity
    base_risk = (
        0.50 * rule_score
        + 0.30 * ml_confidence_percent
        + 0.20 * data_leakage_severity
    )

    # Standard arithmetic rounding (round-half-up)
    score = int(max(0, min(100, math.floor(base_risk + 0.5))))

    # Safety floor: strong rule match (>= 70) ensures a final risk score of at least 70
    if rule_score >= 70:
        score = max(score, 70)

    return score

