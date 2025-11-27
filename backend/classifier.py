"""
Simple, extensible intent classifier.
Currently uses a keyword-based approach for legal question detection.
This makes it easy to swap in a model-based classifier later.
"""
from typing import List

LEGAL_KEYWORDS = [
    "law",
    "case",
    "court",
    "act",
    "section",
    "judgment",
    "verdict",
    "appeal",
    "sentence",
    "advocate",
    "bail",
    "petition",
    "hearing",
    "order",
    "statute",
    "liable",
    "liable",
]


def is_legal_question(text: str) -> bool:
    """Return True if the text looks like a legal question.

    This is a simple keyword matcher, and is intended to be replaced by a more
    robust classifier (ML model, LLM, etc.) in the future.
    """
    if not text:
        return False
    t = text.lower()
    for kw in LEGAL_KEYWORDS:
        if kw in t:
            return True
    return False
