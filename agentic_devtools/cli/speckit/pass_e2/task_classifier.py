"""Task classifier for E.2 — test-task identification and type classification.

Implements FR-002 keyword matching semantics and FR-006 test-type classification.
"""

from __future__ import annotations

import re

from .constants import TEST_TASK_KEYWORDS, TEST_TYPE_KEYWORDS

# ---------------------------------------------------------------------------
# FR-002 word-boundary definition:
# A word boundary is any position adjacent to a character that is NOT a letter,
# digit, or hyphen. Hyphens are NOT boundaries.
# ---------------------------------------------------------------------------

# Characters that are NOT part of a "word" (i.e., boundaries)
_NON_WORD_CHAR_PATTERN = r"[^a-zA-Z0-9\-]"


def _build_single_word_pattern(keyword: str) -> re.Pattern[str]:
    """Build a regex for single-word keyword with FR-002 word boundaries.

    Single-word keywords match only at word boundaries where hyphens
    are NOT boundaries (they connect compound words).
    Also allows optional trailing s/es for pluralization.
    """
    escaped = re.escape(keyword)
    # Word boundary: start of string or preceded by non-word char
    # End boundary: end of string or followed by non-word char
    # Allow optional trailing s or es
    return re.compile(
        rf"(?:(?<=^)|(?<={_NON_WORD_CHAR_PATTERN}))"
        rf"{escaped}(?:es|s)?"
        rf"(?:(?=$)|(?={_NON_WORD_CHAR_PATTERN}))",
        re.IGNORECASE | re.MULTILINE,
    )


def _normalize_for_phrase_match(text: str) -> str:
    """Normalize text for multi-word phrase matching.

    FR-002: hyphens and spaces between word tokens are treated as equivalent.
    """
    return re.sub(r"[-\s]+", " ", text.lower())


def _build_multi_word_pattern(keyword: str) -> re.Pattern[str]:
    """Build a regex for multi-word keyword matching with normalization.

    Multi-word keywords are matched as literal phrases with hyphen/space
    normalization and optional trailing s/es on the last token.
    """
    # Normalize keyword: split on hyphens/spaces, rejoin with flexible separator
    tokens = re.split(r"[-\s]+", keyword.strip())
    # Build pattern: tokens joined by [-\s]+ with optional trailing s/es on last token
    parts = [re.escape(t) for t in tokens[:-1]]
    last = re.escape(tokens[-1])
    sep = r"[-\s]+"
    if parts:
        pattern_str = sep.join(parts) + sep + last + r"(?:es|s)?"
    else:
        pattern_str = last + r"(?:es|s)?"
    return re.compile(pattern_str, re.IGNORECASE)


def _is_multi_word(keyword: str) -> bool:
    """Check if keyword is multi-word (contains space or hyphen between tokens)."""
    return bool(re.search(r"[-\s]", keyword.strip()))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_FR_REF_RE = re.compile(r"\bFR-\d+\b", re.IGNORECASE)
_US_LABEL_RE = re.compile(r"\[US(\d+)\]", re.IGNORECASE)

# Compiled patterns for test-task keywords (cached at module level)
_SINGLE_WORD_PATTERNS: list[re.Pattern[str]] = []
_MULTI_WORD_PATTERNS: list[re.Pattern[str]] = []

for _kw in TEST_TASK_KEYWORDS:
    if _is_multi_word(_kw):
        _MULTI_WORD_PATTERNS.append(_build_multi_word_pattern(_kw))
    else:
        _SINGLE_WORD_PATTERNS.append(_build_single_word_pattern(_kw))

# Compiled patterns for test-type keywords (cached at module level)
# Avoids recompiling regex patterns on every call to classify_test_types()
_TEST_TYPE_PATTERNS: dict[str, list[tuple[bool, re.Pattern[str]]]] = {}
for _type, _keywords in TEST_TYPE_KEYWORDS.items():
    _patterns: list[tuple[bool, re.Pattern[str]]] = []
    for _kw in _keywords:
        if _is_multi_word(_kw):
            _patterns.append((True, _build_multi_word_pattern(_kw)))
        else:
            _patterns.append((False, _build_single_word_pattern(_kw)))
    _TEST_TYPE_PATTERNS[_type] = _patterns

# Compiled patterns for implementation keywords used by detect_ambiguous_task()
# Avoids recompiling regex patterns on every call
_IMPL_KEYWORDS = [
    "implement",
    "build",
    "develop",
    "design",
    "refactor",
    "configure",
    "setup",
]
_IMPL_KEYWORD_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        rf"(?:^|(?<=[^a-zA-Z0-9\-])){re.escape(kw)}(?:$|(?=[^a-zA-Z0-9\-]))",
        re.IGNORECASE,
    )
    for kw in _IMPL_KEYWORDS
]


def is_test_task(description: str) -> bool:
    """Determine if a task description indicates a test task (FR-002).

    Uses FR-002 matching semantics:
    - Single-word keywords: word-boundary matching (hyphens not boundaries)
    - Multi-word keywords: phrase matching with hyphen/space normalization
    - Both: case-insensitive, optional trailing s/es
    """
    # Check single-word patterns against original text
    for pattern in _SINGLE_WORD_PATTERNS:
        if pattern.search(description):
            return True

    # Check multi-word patterns against normalized text
    normalized = _normalize_for_phrase_match(description)
    for pattern in _MULTI_WORD_PATTERNS:
        if pattern.search(normalized):
            return True

    return False


def classify_test_types(description: str) -> list[str]:
    """Classify a task's test types based on FR-006 keyword sets.

    Returns a list of matched test types (may be multiple).
    Uses the same matching semantics as FR-002 (hyphen/space normalization,
    case-insensitive).
    """
    matched_types: list[str] = []
    normalized = _normalize_for_phrase_match(description)

    for test_type, patterns in _TEST_TYPE_PATTERNS.items():
        for is_multi, pattern in patterns:
            text = normalized if is_multi else description
            if pattern.search(text):
                matched_types.append(test_type)
                break

    return matched_types


def extract_task_fr_refs(description: str) -> tuple[list[str], list[int]]:
    """Extract explicit FR references and [USn] labels from a task description.

    Returns:
        Tuple of (fr_refs, us_labels) where:
        - fr_refs: list of FR identifiers (e.g., ["FR-001", "FR-003"])
        - us_labels: list of user story numbers (e.g., [1, 2])
    """
    fr_refs = list(dict.fromkeys(m.group(0) for m in _FR_REF_RE.finditer(description)))
    us_labels = list(dict.fromkeys(int(m.group(1)) for m in _US_LABEL_RE.finditer(description)))
    return fr_refs, us_labels


def detect_ambiguous_task(description: str) -> bool:
    """Detect if a task is ambiguously both implementation and test.

    A task is ambiguous if it contains test-related keywords AND
    implementation-related keywords (e.g., "Implement and verify").
    """
    if not is_test_task(description):
        return False

    # Check for implementation keywords (narrowed to avoid false positives
    # with common test-task verbs like "write tests", "create test fixtures",
    # "add test coverage")
    desc_lower = description.lower()
    for pattern in _IMPL_KEYWORD_PATTERNS:
        if pattern.search(desc_lower):
            return True

    return False
