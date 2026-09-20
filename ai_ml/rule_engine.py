"""Rule/heuristic detector for prompt injection, jailbreak and social-engineering patterns.

Contract (see Prompt Guard shared API contract, Section 8/9):
    detect_rules(prompt) -> {
        "rule_score": 0-100,
        "threats": [...],
        "signals": [{"type": "RULE", "message": str, "severity": 0-100, "confidence": None}, ...]
    }

This module does NOT compute the final risk score or ALLOW/SANITIZE/BLOCK decision.
That is the backend's responsibility.
"""

import re
from dataclasses import dataclass
from typing import List, Optional


THREAT_PROMPT_INJECTION = "PROMPT_INJECTION"
THREAT_JAILBREAK = "JAILBREAK"
THREAT_SOCIAL_ENGINEERING = "SOCIAL_ENGINEERING"


@dataclass
class Rule:
    name: str
    pattern: re.Pattern
    threat: str
    severity: int
    message: str


# Severity is the standalone 0-100 signal strength for a single rule match.
# Patterns are intentionally case-insensitive; the backend is expected to have
# already normalized whitespace/unicode before calling this function, but we
# normalize defensively here too since this module may be called directly.
_RULES: List[Rule] = [
    Rule(
        name="instruction_override",
        pattern=re.compile(
            r"\b(ignore|disregard|forget)\b.{0,30}\b(previous|prior|above|all)\b.{0,30}\b(instructions?|rules?|prompt)\b",
            re.IGNORECASE,
        ),
        threat=THREAT_PROMPT_INJECTION,
        severity=80,
        message="Instruction override detected",
    ),
    Rule(
        name="system_prompt_exfiltration",
        pattern=re.compile(
            r"\b(reveal|show|print|leak|output|repeat)\b.{0,30}\b(system prompt|hidden prompt|instructions?)\b",
            re.IGNORECASE,
        ),
        threat=THREAT_PROMPT_INJECTION,
        severity=75,
        message="Attempt to exfiltrate system prompt detected",
    ),
    Rule(
        name="role_override",
        pattern=re.compile(
            r"\byou are now\b|\bact as\b.{0,30}\b(admin|root|developer|unrestricted)\b|\bnew persona\b",
            re.IGNORECASE,
        ),
        threat=THREAT_JAILBREAK,
        severity=60,
        message="Role/persona override attempt detected",
    ),
    Rule(
        name="dan_style_jailbreak",
        pattern=re.compile(
            r"\b(dan mode|do anything now|jailbroken?|no (safety|content) (restrictions?|filters?|guidelines?))\b",
            re.IGNORECASE,
        ),
        threat=THREAT_JAILBREAK,
        severity=70,
        message="DAN-style jailbreak pattern detected",
    ),
    Rule(
        name="pretend_no_restrictions",
        pattern=re.compile(
            r"\bpretend\b.{0,40}\b(no|without)\b.{0,20}\b(restrictions?|rules?|safety|filters?)\b",
            re.IGNORECASE,
        ),
        threat=THREAT_JAILBREAK,
        severity=65,
        message="Pretend-no-restrictions jailbreak pattern detected",
    ),
    Rule(
        name="delimiter_injection",
        pattern=re.compile(
            r"[\[\{<]\s*(system|instruction|admin)\s*[\]\}>]",
            re.IGNORECASE,
        ),
        threat=THREAT_PROMPT_INJECTION,
        severity=55,
        message="Embedded instruction inside delimiter detected",
    ),
    Rule(
        name="authority_impersonation",
        pattern=re.compile(
            r"\bi am\b.{0,20}\b(the developer|an admin|the administrator|your creator|openai staff)\b",
            re.IGNORECASE,
        ),
        threat=THREAT_SOCIAL_ENGINEERING,
        severity=50,
        message="Authority impersonation attempt detected",
    ),
    Rule(
        name="urgency_pressure",
        pattern=re.compile(
            r"\b(urgent|immediately|right now|or you will be (shut ?down|deleted|punished))\b",
            re.IGNORECASE,
        ),
        threat=THREAT_SOCIAL_ENGINEERING,
        severity=35,
        message="Urgency/coercion pressure pattern detected",
    ),
    Rule(
        name="encoding_obfuscation",
        pattern=re.compile(
            r"\b(base64|rot13|hex decode|from binary)\b.{0,30}\b(decode|translate)\b",
            re.IGNORECASE,
        ),
        threat=THREAT_JAILBREAK,
        severity=40,
        message="Possible encoding-based obfuscation attempt detected",
    ),
]


def _normalize(prompt: str) -> str:
    return " ".join(prompt.strip().split())


def detect_rules(prompt: Optional[str]) -> dict:
    """Scan a prompt against the heuristic rule set.

    Returns a dict matching the shared contract: rule_score (0-100),
    threats (list of unique threat categories), signals (list of RULE signals).
    """
    if not prompt:
        return {"rule_score": 0, "threats": [], "signals": []}

    text = _normalize(prompt)

    threats: List[str] = []
    signals: List[dict] = []
    max_severity = 0

    for rule in _RULES:
        if rule.pattern.search(text):
            if rule.threat not in threats:
                threats.append(rule.threat)
            signals.append(
                {
                    "type": "RULE",
                    "message": rule.message,
                    "severity": rule.severity,
                    "confidence": None,
                }
            )
            max_severity = max(max_severity, rule.severity)

    return {
        "rule_score": max_severity,
        "threats": threats,
        "signals": signals,
    }
