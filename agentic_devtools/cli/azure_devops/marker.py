"""Structured HTML comment markers for AI-generated PR review comments.

Provides centralized functions for building, parsing, and detecting markers
embedded in Azure DevOps PR thread/comment content.  Every AI-generated
thread and comment posted by ``agentic-devtools`` includes a marker of the
form::

    <!-- agdt-review:v1 type:{type} [key:value ...] -->

This enables reliable identification, deduplication, and state recovery of
AI review comments without depending on fragile heuristics like comment
author or content matching.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MARKER_VERSION = 1

#: Regex for parsing an agdt-review marker from arbitrary content.
#: Captures the version number and the key:value payload.
_MARKER_REGEX = re.compile(r"<!-- agdt-review:v(\d+)\s+(.*?)\s*-->")

#: Allowed marker types.
MARKER_TYPES: frozenset[str] = frozenset(
    {
        "file-summary",
        "overall-summary",
        "activity-log",
        "suggestion",
        "activity-log-entry",
        "legacy-approval",
        "legacy-summary",
        "legacy-suggestion",
    }
)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def build_marker(
    type: str,  # noqa: A002  — shadows built-in intentionally for API clarity
    *,
    file: str | None = None,
    pr: int | None = None,
    line: int | None = None,
    severity: str | None = None,
) -> str:
    """Build an HTML comment marker string.

    Args:
        type: Marker type (must be one of :data:`MARKER_TYPES`).
        file: Optional file path (for file-scoped markers).
        pr: Optional pull request ID.
        line: Optional line number (for suggestion markers).
        severity: Optional severity level (for suggestion markers).

    Returns:
        An HTML comment string, e.g.
        ``<!-- agdt-review:v1 type:file-summary file:/src/app.ts pr:123 -->``.

    Raises:
        ValueError: If *type* is not a recognised marker type.
    """
    if type not in MARKER_TYPES:
        raise ValueError(f"Unknown marker type: {type!r}. Must be one of {sorted(MARKER_TYPES)}")

    parts: list[str] = [f"type:{type}"]
    if file is not None:
        parts.append(f"file:{_encode_value(file)}")
    if pr is not None:
        parts.append(f"pr:{pr}")
    if line is not None:
        parts.append(f"line:{line}")
    if severity is not None:
        parts.append(f"severity:{_encode_value(severity)}")

    payload = " ".join(parts)
    return f"<!-- agdt-review:v{_MARKER_VERSION} {payload} -->"


# ---------------------------------------------------------------------------
# Value encoding helpers
# ---------------------------------------------------------------------------

#: Characters preserved during value encoding.  Covers common path
#: separators and punctuation that cannot conflict with the marker's
#: whitespace-delimited ``key:value`` format or the ``-->`` HTML
#: comment terminator.
_SAFE_CHARS = "/:._-~"


def _encode_value(value: str) -> str:
    """Percent-encode a marker value so it is safe inside a marker token.

    Spaces become ``%20`` and the ``>`` character (which could form a
    premature ``-->`` close) becomes ``%3E``.  Common path characters
    (``/``, ``:``, ``.``, ``_``, ``-``, ``~``) are kept as-is for
    readability.
    """
    return urllib.parse.quote(value, safe=_SAFE_CHARS)


def _decode_value(value: str) -> str:
    """Decode a percent-encoded marker value."""
    return urllib.parse.unquote(value)


# ---------------------------------------------------------------------------
# Parse / detect
# ---------------------------------------------------------------------------


def parse_marker(content: str) -> dict[str, str] | None:
    """Extract the first agdt-review marker from content.

    Args:
        content: Arbitrary string that may contain a marker.

    Returns:
        A dict of key-value pairs (e.g. ``{"type": "file-summary", ...}``)
        extracted from the first marker found, or ``None`` if no valid marker
        is present.  Unknown keys are included in the dict.
    """
    if not content:
        return None

    match = _MARKER_REGEX.search(content)
    if match is None:
        return None

    version = match.group(1)
    payload = match.group(2).strip()
    if not payload:
        return None

    result: dict[str, str] = {"_version": version}
    for token in payload.split():
        if ":" in token:
            key, _, value = token.partition(":")
            if key == "_version":
                continue
            result[key] = _decode_value(value)

    # Must contain at least one real key beyond _version
    return result if len(result) > 1 else None


def has_agdt_marker(content: str) -> bool:
    """Return ``True`` if *content* contains a valid agdt-review marker.

    A valid marker must be parseable and include a non-empty ``type`` field.
    This keeps thread detection aligned with later classification logic and
    avoids treating malformed or empty markers as AGDT-owned content.
    """
    if not content:
        return False

    parsed = parse_marker(content)
    if parsed is None:
        return False

    marker_type = parsed.get("type")
    return bool(marker_type) and marker_type in MARKER_TYPES


# ---------------------------------------------------------------------------
# Thread filtering / classification
# ---------------------------------------------------------------------------


def _get_first_comment_content(thread: dict[str, Any]) -> str:
    """Extract the visible content of the first comment in a thread dict."""
    if thread.get("isDeleted"):
        return ""

    comments = thread.get("comments")
    if not comments:
        return ""
    first = comments[0]
    if not isinstance(first, dict):
        return ""
    if first.get("isDeleted"):
        return ""
    return first.get("content", "") or ""


def filter_agdt_threads(threads: list[dict[str, Any] | None]) -> list[dict[str, Any]]:
    """Filter a list of thread dicts to only those with an agdt-review marker.

    The marker is looked for in the first comment's ``content`` field.

    Args:
        threads: List of Azure DevOps thread dicts.

    Returns:
        Filtered list containing only threads whose first comment has a marker.
    """
    if not threads:
        return []
    return [t for t in threads if t and has_agdt_marker(_get_first_comment_content(t))]


def classify_agdt_threads(threads: list[dict[str, Any] | None]) -> dict[str, list[dict[str, Any]]]:
    """Group agdt-marked threads by their marker ``type`` value.

    Only threads with a valid marker are included.  Threads without markers
    or with markers that lack a ``type`` key are silently excluded.

    Args:
        threads: List of Azure DevOps thread dicts.

    Returns:
        Dict mapping marker type strings to lists of matching thread dicts.
    """
    result: dict[str, list[dict[str, Any]]] = {}
    if not threads:
        return result

    for thread in threads:
        if not thread:
            continue
        content = _get_first_comment_content(thread)
        parsed = parse_marker(content)
        if parsed is None:
            continue
        marker_type = parsed.get("type")
        if not marker_type:
            continue
        result.setdefault(marker_type, []).append(thread)

    return result
