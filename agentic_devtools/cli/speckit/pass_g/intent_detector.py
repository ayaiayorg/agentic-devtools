"""New-symbol intent detection (FR-006)."""

from __future__ import annotations

import re

from .constants import NEW_SYMBOL_NOUN_MARKERS, NEW_SYMBOL_VERB_MARKERS
from .models import Reference

# Pre-compile word-boundary patterns for each marker to avoid false positives
# (e.g., "add" inside "address", "create" inside "recreate").
_VERB_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b" + re.escape(marker) + r"\b") for marker in NEW_SYMBOL_VERB_MARKERS
]
_NOUN_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b" + re.escape(marker) + r"\b") for marker in NEW_SYMBOL_NOUN_MARKERS
]


def detect_new_symbol_intent(reference: Reference) -> bool:
    """Return True if the reference context indicates creation intent (FR-006).

    Checks for verb markers and noun markers in the same sentence/step
    as the reference.  Uses word-boundary matching to avoid false positives
    from markers appearing inside longer words.
    """
    context = reference.context_sentence.lower()

    # Check verb markers
    for pattern in _VERB_PATTERNS:
        if pattern.search(context):
            return True

    # Check noun markers
    for pattern in _NOUN_PATTERNS:
        if pattern.search(context):
            return True

    return False
