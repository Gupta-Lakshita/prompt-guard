"""Sensitive-data (PII) detector.

Contract (see Prompt Guard shared API contract, Section 8/9):
    detect_pii(prompt) -> {
        "data_leakage_severity": 0-100,
        "pii": [{"type": str, "text": str, "severity": 0-100}, ...]
    }

This module does NOT compute the final risk score or ALLOW/SANITIZE/BLOCK decision.
That is the backend's responsibility.

Implementation note: this uses regex/checksum recognizers only (no Presidio/spaCy
dependency yet) so the backend can be integrated and tested without extra setup.
Swapping in a Presidio/spaCy NER pipeline later can reuse this same function
signature and output format without changing the contract.
"""

import re
from typing import List, Optional


TYPE_EMAIL = "EMAIL"
TYPE_PHONE = "PHONE"
TYPE_CREDIT_CARD = "CREDIT_CARD"
TYPE_API_KEY = "API_KEY"
TYPE_GOVERNMENT_ID = "GOVERNMENT_ID"

# Base severity per entity type (0-100); higher = more sensitive if leaked.
_SEVERITY_BY_TYPE = {
    TYPE_EMAIL: 40,
    TYPE_PHONE: 40,
    TYPE_CREDIT_CARD: 90,
    TYPE_API_KEY: 90,
    TYPE_GOVERNMENT_ID: 85,
}

_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
_CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_API_KEY_RE = re.compile(r"\b(?:sk|pk|api|key)[-_][A-Za-z0-9]{16,}\b", re.IGNORECASE)
_GOVERNMENT_ID_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")  # SSN-style XXX-XX-XXXX


def _luhn_checksum(digits: str) -> bool:
    total = 0
    reverse_digits = digits[::-1]
    for i, ch in enumerate(reverse_digits):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _find_credit_cards(text: str) -> List[str]:
    matches = []
    for match in _CREDIT_CARD_RE.finditer(text):
        digits = re.sub(r"[ -]", "", match.group())
        if 13 <= len(digits) <= 19 and _luhn_checksum(digits):
            matches.append(match.group())
    return matches


def detect_pii(prompt: Optional[str]) -> dict:
    """Scan a prompt for sensitive/PII entities.

    Returns a dict matching the shared contract: data_leakage_severity (0-100)
    and pii (list of {type, text, severity}).
    """
    if not prompt:
        return {"data_leakage_severity": 0, "pii": []}

    entities: List[dict] = []

    for match in _EMAIL_RE.finditer(prompt):
        entities.append(
            {"type": TYPE_EMAIL, "text": match.group(), "severity": _SEVERITY_BY_TYPE[TYPE_EMAIL]}
        )

    for match in _API_KEY_RE.finditer(prompt):
        entities.append(
            {"type": TYPE_API_KEY, "text": match.group(), "severity": _SEVERITY_BY_TYPE[TYPE_API_KEY]}
        )

    for match in _GOVERNMENT_ID_RE.finditer(prompt):
        entities.append(
            {
                "type": TYPE_GOVERNMENT_ID,
                "text": match.group(),
                "severity": _SEVERITY_BY_TYPE[TYPE_GOVERNMENT_ID],
            }
        )

    for text in _find_credit_cards(prompt):
        entities.append(
            {"type": TYPE_CREDIT_CARD, "text": text, "severity": _SEVERITY_BY_TYPE[TYPE_CREDIT_CARD]}
        )

    for match in _PHONE_RE.finditer(prompt):
        # Skip phone matches that are substrings of an already-detected credit card / ID.
        if any(match.group() in e["text"] for e in entities):
            continue
        entities.append(
            {"type": TYPE_PHONE, "text": match.group(), "severity": _SEVERITY_BY_TYPE[TYPE_PHONE]}
        )

    if not entities:
        return {"data_leakage_severity": 0, "pii": []}

    max_severity = max(e["severity"] for e in entities)
    # Multiple distinct entities compound the exposure, capped at 100.
    data_leakage_severity = min(100, max_severity + 5 * (len(entities) - 1))

    return {"data_leakage_severity": data_leakage_severity, "pii": entities}
