"""Sensitive-data (PII) detector.

Contract (see Prompt Guard shared API contract, Section 8/9):
    detect_pii(prompt) -> {
        "data_leakage_severity": 0-100,
        "pii": [{"type": str, "text": str, "severity": 0-100}, ...]
    }

This module does NOT compute the final risk score or ALLOW/SANITIZE/BLOCK decision.
That is the backend's responsibility.

Primary implementation: Microsoft Presidio (AnalyzerEngine) + spaCy NER
(en_core_web_sm), per the project methodology (Section 5.1 of the synopsis).
Presidio's built-in recognizers cover EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD
(regex + Luhn check) and US_SSN; a custom PatternRecognizer is registered
alongside them for API keys/credentials, which Presidio has no built-in
recognizer for. spaCy NER additionally surfaces PERSON and LOCATION entities.

Fallback: if presidio/spacy are not installed, or the spaCy model isn't
downloaded, this module falls back to the original regex/Luhn-checksum-only
implementation (see `_detect_pii_regex`) so `detect_pii(prompt)` never raises
and the backend integration keeps working either way.
"""

import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

TYPE_EMAIL = "EMAIL"
TYPE_PHONE = "PHONE"
TYPE_CREDIT_CARD = "CREDIT_CARD"
TYPE_API_KEY = "API_KEY"
TYPE_GOVERNMENT_ID = "GOVERNMENT_ID"
TYPE_PERSON = "PERSON"
TYPE_LOCATION = "LOCATION"

# Base severity per entity type (0-100); higher = more sensitive if leaked.
_SEVERITY_BY_TYPE = {
    TYPE_EMAIL: 40,
    TYPE_PHONE: 40,
    TYPE_CREDIT_CARD: 90,
    TYPE_API_KEY: 90,
    TYPE_GOVERNMENT_ID: 85,
    TYPE_PERSON: 20,
    TYPE_LOCATION: 15,
}

_PRESIDIO_SCORE_THRESHOLD = 0.4
_PRESIDIO_ENTITIES = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "US_SSN",
    "PERSON",
    "LOCATION",
    "API_KEY",
]
_PRESIDIO_TO_CONTRACT_TYPE = {
    "EMAIL_ADDRESS": TYPE_EMAIL,
    "PHONE_NUMBER": TYPE_PHONE,
    "CREDIT_CARD": TYPE_CREDIT_CARD,
    "US_SSN": TYPE_GOVERNMENT_ID,
    "PERSON": TYPE_PERSON,
    "LOCATION": TYPE_LOCATION,
    "API_KEY": TYPE_API_KEY,
}

_analyzer_engine = None
_presidio_init_failed = False


def _build_analyzer_engine():
    from presidio_analyzer import Pattern, PatternRecognizer, RecognizerRegistry
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    nlp_configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
    }
    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_configuration).create_engine()

    registry = RecognizerRegistry()
    registry.load_predefined_recognizers(nlp_engine=nlp_engine, languages=["en"])

    api_key_recognizer = PatternRecognizer(
        supported_entity="API_KEY",
        patterns=[
            Pattern(
                name="api_key_pattern",
                regex=r"\b(?:sk|pk|api|key)[-_][A-Za-z0-9]{16,}\b",
                score=0.85,
            )
        ],
    )
    registry.add_recognizer(api_key_recognizer)

    from presidio_analyzer import AnalyzerEngine

    return AnalyzerEngine(registry=registry, nlp_engine=nlp_engine, supported_languages=["en"])


def _get_analyzer_engine():
    """Lazily build and cache the Presidio AnalyzerEngine (expensive to construct)."""
    global _analyzer_engine, _presidio_init_failed

    if _presidio_init_failed:
        return None
    if _analyzer_engine is not None:
        return _analyzer_engine

    try:
        _analyzer_engine = _build_analyzer_engine()
        return _analyzer_engine
    except Exception:
        logger.warning(
            "Presidio/spaCy PII engine unavailable; falling back to regex-only PII "
            "detection. Install presidio-analyzer, spacy and the en_core_web_sm "
            "model to enable NER-based detection.",
            exc_info=True,
        )
        _presidio_init_failed = True
        return None


def _detect_pii_presidio(prompt: str) -> dict:
    engine = _get_analyzer_engine()
    if engine is None:
        return _detect_pii_regex(prompt)

    results = engine.analyze(
        text=prompt,
        language="en",
        entities=_PRESIDIO_ENTITIES,
        score_threshold=_PRESIDIO_SCORE_THRESHOLD,
    )

    entities: List[dict] = []
    for result in sorted(results, key=lambda r: r.start):
        contract_type = _PRESIDIO_TO_CONTRACT_TYPE.get(result.entity_type)
        if contract_type is None:
            continue
        entities.append(
            {
                "type": contract_type,
                "text": prompt[result.start : result.end],
                "severity": _SEVERITY_BY_TYPE[contract_type],
            }
        )

    return _aggregate(entities)


def _aggregate(entities: List[dict]) -> dict:
    if not entities:
        return {"data_leakage_severity": 0, "pii": []}
    max_severity = max(e["severity"] for e in entities)
    # Multiple distinct entities compound the exposure, capped at 100.
    data_leakage_severity = min(100, max_severity + 5 * (len(entities) - 1))
    return {"data_leakage_severity": data_leakage_severity, "pii": entities}


# --------------------------------------------------------------------------
# Regex/Luhn-checksum fallback (used when Presidio/spaCy are unavailable).
# --------------------------------------------------------------------------

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


def _detect_pii_regex(prompt: str) -> dict:
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

    return _aggregate(entities)


def detect_pii(prompt: Optional[str]) -> dict:
    """Scan a prompt for sensitive/PII entities.

    Returns a dict matching the shared contract: data_leakage_severity (0-100)
    and pii (list of {type, text, severity}). Uses Presidio + spaCy NER when
    available, otherwise falls back to regex/Luhn-checksum detection.
    """
    if not prompt:
        return {"data_leakage_severity": 0, "pii": []}

    try:
        import presidio_analyzer  # noqa: F401
    except ImportError:
        return _detect_pii_regex(prompt)

    return _detect_pii_presidio(prompt)
