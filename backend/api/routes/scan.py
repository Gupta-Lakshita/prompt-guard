"""
POST /scan — primary prompt scanning endpoint.

Flow:
    1.  Receive ScanRequest { prompt }
    2.  Preserve original_prompt (never modified)
    3.  Normalise prompt for AI/ML detection
    4.  Call detect_rules(), predict_ml(), detect_pii()   ← Lakshita's modules
    5.  Compute risk_score via the weighted formula
    6.  Determine ALLOW / SANITIZE / BLOCK via thresholds
    7.  Sanitise only if decision == SANITIZE
    8.  Assemble signals list (RULE + ML + PII signals)
    9.  Assemble threats list (deduplicated)
    10. Log event to SQLite
    11. Return exact ScanResponse
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

# AI/ML modules (Lakshita's — do not modify their calls or output handling)
from ai_ml.rule_engine import detect_rules
from ai_ml.classifier import predict_ml
from ai_ml.pii_detector import detect_pii

from backend.schemas.scan import ScanRequest, ScanResponse, SignalItem, PiiItem
from backend.core.normalizer import normalize_prompt
from backend.core.risk_scorer import compute_risk_score
from backend.core.decision_engine import make_decision, DECISION_SANITIZE
from backend.sanitizer.sanitizer import sanitize_prompt
from backend.db.event_logger import insert_event

router = APIRouter()


@router.post("/scan", response_model=ScanResponse)
def scan_prompt(request: ScanRequest) -> ScanResponse:
    """
    Scan a user prompt for injection, jailbreak, and PII threats.

    Returns a structured response with risk score, decision, signals,
    and (if SANITIZE) a redacted version of the prompt.
    """
    # ── Step 1 & 2: Preserve original, normalise for detection ──────────────
    original_prompt = request.prompt
    normalized = normalize_prompt(original_prompt)

    # ── Step 3: AI/ML Detection (Lakshita's modules, contracts are fixed) ───
    rule_result = detect_rules(normalized)   # rule_score, threats, signals
    ml_result   = predict_ml(normalized)     # label, confidence
    pii_result  = detect_pii(normalized)     # data_leakage_severity, pii

    # ── Step 4: Risk Score ───────────────────────────────────────────────────
    risk_score = compute_risk_score(
        ml_confidence=ml_result["confidence"],
        data_leakage_severity=pii_result["data_leakage_severity"],
        rule_score=rule_result["rule_score"],
    )

    # ── Step 5: Decision (score only — PII alone does NOT force SANITIZE) ───
    decision = make_decision(risk_score)

    # ── Step 6: Sanitise if required ────────────────────────────────────────
    sanitized_prompt = None
    if decision == DECISION_SANITIZE and pii_result["pii"]:
        sanitized_prompt = sanitize_prompt(original_prompt, pii_result["pii"])

    # ── Step 7: Build signals list ───────────────────────────────────────────
    # Start with rule signals from detect_rules()
    signals = [
        SignalItem(
            type=sig["type"],
            message=sig["message"],
            severity=sig["severity"],
            confidence=sig["confidence"],  # always None for RULE signals
        )
        for sig in rule_result["signals"]
    ]

    # Append ML signal if the classifier detected a label
    if ml_result["label"] is not None:
        signals.append(
            SignalItem(
                type="ML",
                message=f"ML classifier detected {ml_result['label']}",
                severity=int(ml_result["confidence"] * 100),
                confidence=ml_result["confidence"],
            )
        )

    # Append PII signal if any PII was found
    if pii_result["pii"]:
        signals.append(
            SignalItem(
                type="PII",
                message=f"{len(pii_result['pii'])} PII entity/entities detected",
                severity=pii_result["data_leakage_severity"],
                confidence=None,
            )
        )

    # ── Step 8: Build threats list (deduplicated) ────────────────────────────
    threats = list(rule_result["threats"])  # PROMPT_INJECTION, JAILBREAK, SOCIAL_ENGINEERING

    if ml_result["label"] and ml_result["label"] not in threats:
        threats.append(ml_result["label"])

    if pii_result["pii"] and "SENSITIVE_DATA" not in threats:
        threats.append("SENSITIVE_DATA")

    # ── Step 9: Metadata ────────────────────────────────────────────────────
    scan_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    # ── Step 10: Log to SQLite ───────────────────────────────────────────────
    insert_event(
        scan_id=scan_id,
        original_prompt=original_prompt,
        sanitized_prompt=sanitized_prompt,
        risk_score=risk_score,
        decision=decision,
        threats=threats,
        signals=[s.model_dump() for s in signals],
        pii=pii_result["pii"],
        timestamp=timestamp,
    )

    # ── Step 11: Return exact contract response ──────────────────────────────
    return ScanResponse(
        scan_id=scan_id,
        original_prompt=original_prompt,
        sanitized_prompt=sanitized_prompt,
        risk_score=risk_score,
        decision=decision,
        threats=threats,
        signals=signals,
        pii=[PiiItem(**p) for p in pii_result["pii"]],
        timestamp=timestamp,
    )
