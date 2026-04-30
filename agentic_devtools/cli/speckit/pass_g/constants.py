"""Named constants for Pass G — Code Reference Cross-Referencing."""

from __future__ import annotations

# Minimum similarity score to surface a candidate suggestion (FR-008).
SUGGESTION_THRESHOLD: float = 0.75

# Score at or above which a single candidate is classified high-confidence (FR-009).
HIGH_CONFIDENCE_THRESHOLD: float = 0.90

# Maximum gap between top candidates before ambiguity is declared (FR-009, FR-010).
DISAMBIGUATION_MARGIN: float = 0.05

# Elapsed seconds before a performance warning is emitted (NFR-002).
PERFORMANCE_WARNING_SECONDS: int = 30

# Case-insensitive verb markers indicating new-symbol creation intent (FR-006).
NEW_SYMBOL_VERB_MARKERS: tuple[str, ...] = (
    "create",
    "add",
    "introduce",
    "implement",
    "define",
    "scaffold",
    "generate",
    "write",
    "build",
    "set up",
    "register",
    "wire up",
)

# Case-insensitive noun markers indicating new-symbol creation intent (FR-006).
NEW_SYMBOL_NOUN_MARKERS: tuple[str, ...] = (
    "new file",
    "new class",
    "new function",
    "new module",
    "new command",
)

# File patterns excluded from the inventory and suggestions (FR-011).
PROTECTED_FILE_PATTERNS: tuple[str, ...] = (
    "_version.py",
    "__pycache__",
    ".git/",
)

# Maximum number of candidate suggestions returned per reference.
MAX_CANDIDATES_PER_REFERENCE: int = 5
