"""
Prompt sanitizer.

Redacts PII entities detected by detect_pii() from the original prompt.
This is called ONLY when the decision engine returns SANITIZE.
For ALLOW and BLOCK, sanitized_prompt stays null.
"""

from typing import List


def sanitize_prompt(original_prompt: str, pii_entities: List[dict]) -> str:
    """
    Replace each detected PII entity's text with a [TYPE REDACTED] placeholder.

    Example:
        original : "My email is abc@gmail.com and card 4539578763621486"
        pii      : [{"type": "EMAIL", "text": "abc@gmail.com", ...},
                    {"type": "CREDIT_CARD", "text": "4539578763621486", ...}]
        result   : "My email is [EMAIL REDACTED] and card [CREDIT_CARD REDACTED]"

    Entities are sorted by length (longest first) before replacement to avoid
    partial-match issues where a shorter entity text is a substring of a longer one.

    Args:
        original_prompt: The unmodified prompt from the user's request.
        pii_entities:    List of PII dicts from detect_pii()["pii"].

    Returns:
        Sanitised string with PII values replaced by placeholders.
        If pii_entities is empty, returns the original prompt unchanged.
    """
    if not pii_entities:
        return original_prompt

    sanitized = original_prompt

    # Sort longest match first to prevent partial replacements
    sorted_entities = sorted(pii_entities, key=lambda e: len(e["text"]), reverse=True)

    for entity in sorted_entities:
        placeholder = f"[{entity['type']} REDACTED]"
        sanitized = sanitized.replace(entity["text"], placeholder)

    return sanitized
