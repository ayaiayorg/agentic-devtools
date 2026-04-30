"""Pass G — Code Reference Cross-Referencing.

Public API for cross-referencing plan code references against the actual
codebase.
"""

from .classifier import classify_references
from .constants import (
    DISAMBIGUATION_MARGIN,
    HIGH_CONFIDENCE_THRESHOLD,
    MAX_CANDIDATES_PER_REFERENCE,
    NEW_SYMBOL_NOUN_MARKERS,
    NEW_SYMBOL_VERB_MARKERS,
    PERFORMANCE_WARNING_SECONDS,
    PROTECTED_FILE_PATTERNS,
    SUGGESTION_THRESHOLD,
)
from .intent_detector import detect_new_symbol_intent
from .inventory import SymbolInventory, build_inventory
from .models import (
    Candidate,
    Finding,
    MatchStatus,
    Reference,
    ReferenceKind,
)
from .reference_extractor import classify_reference_kind, extract_references
from .reporter import render_json, render_markdown

__all__ = [
    "DISAMBIGUATION_MARGIN",
    "HIGH_CONFIDENCE_THRESHOLD",
    "MAX_CANDIDATES_PER_REFERENCE",
    "NEW_SYMBOL_NOUN_MARKERS",
    "NEW_SYMBOL_VERB_MARKERS",
    "PERFORMANCE_WARNING_SECONDS",
    "PROTECTED_FILE_PATTERNS",
    "SUGGESTION_THRESHOLD",
    "Candidate",
    "Finding",
    "MatchStatus",
    "Reference",
    "ReferenceKind",
    "SymbolInventory",
    "build_inventory",
    "classify_reference_kind",
    "classify_references",
    "detect_new_symbol_intent",
    "extract_references",
    "render_json",
    "render_markdown",
]
