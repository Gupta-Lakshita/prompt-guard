"""
Prompt normalizer.

Cleans the raw user prompt before passing it to the AI/ML detection modules.
The ORIGINAL prompt is always preserved in the API response; this normalised
copy is used only internally for detection.
"""

import re
import unicodedata


def normalize_prompt(prompt: str) -> str:
    """
    Return a normalised copy of *prompt* suitable for AI/ML detection.

    Steps applied (in order):
    1. Unicode NFKC — converts full-width characters, ligatures, etc. to
       their canonical ASCII equivalents.
    2. Strip leading/trailing whitespace.
    3. Collapse any run of internal whitespace (spaces, tabs, newlines) to a
       single space.

    The original prompt is NOT modified; only the return value is normalised.
    """
    if not prompt:
        return prompt

    # Step 1: Unicode normalisation
    text = unicodedata.normalize("NFKC", prompt)

    # Step 2: Strip
    text = text.strip()

    # Step 3: Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    return text
