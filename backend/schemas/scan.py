"""
Pydantic schemas for the Prompt Guard API.

These define the exact shared API contract field names.
Do NOT rename any field — the React frontend and this backend
must agree on the same names.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class ScanRequest(BaseModel):
    """Request body for POST /scan."""
    prompt: str


class SignalItem(BaseModel):
    """A single detection signal (RULE, ML, or PII)."""
    type: str                    # "RULE" | "ML" | "PII"
    message: str
    severity: int                # 0–100
    confidence: Optional[float]  # None for RULE/PII signals, 0.0–1.0 for ML


class PiiItem(BaseModel):
    """A single PII entity detected in the prompt."""
    type: str     # EMAIL | PHONE | CREDIT_CARD | API_KEY | GOVERNMENT_ID
    text: str     # The matched text
    severity: int # 0–100


class ScanResponse(BaseModel):
    """
    Response body for POST /scan.
    Field names are contractually fixed — do not rename.
    """
    scan_id: str
    original_prompt: str
    sanitized_prompt: Optional[str]   # null for ALLOW and BLOCK
    risk_score: int                   # 0–100
    decision: str                     # ALLOW | SANITIZE | BLOCK
    threats: List[str]                # PROMPT_INJECTION | JAILBREAK | SENSITIVE_DATA | SOCIAL_ENGINEERING
    signals: List[SignalItem]
    pii: List[PiiItem]                # field name is "pii", not "pii_detected"
    timestamp: str                    # ISO-8601 UTC string


class EventRecord(BaseModel):
    """A scan event as stored in and returned from SQLite."""
    scan_id: str
    original_prompt: str
    sanitized_prompt: Optional[str]
    risk_score: int
    decision: str
    threats: List[str]
    signals: List[SignalItem]
    pii: List[PiiItem]
    timestamp: str
