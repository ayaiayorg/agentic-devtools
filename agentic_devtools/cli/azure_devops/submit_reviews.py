"""
Batch review resolution and validation helpers.

Provides importable pure functions for constructing, resolving, and
validating batch file-review payloads. These functions are shared by
``agdt-submit-reviews``, ``agdt-approve-files``, and
``agdt-request-changes-batch`` so that validation and default-application
logic is defined in exactly one place.
"""

from __future__ import annotations

# Valid outcomes for batch reviews (compared case-insensitively)
_VALID_OUTCOMES = frozenset({"approve", "request-changes", "request-changes-with-suggestion"})


def _is_empty_or_whitespace(value: object) -> bool:
    """Return True if *value* is falsy or a whitespace-only string."""
    if not value:
        return True
    return isinstance(value, str) and not value.strip()


def resolve_batch_reviews(payload: dict) -> list[dict]:
    """Resolve defaults into individual review items from a batch payload.

    Takes a payload dict with optional ``default_outcome``,
    ``default_summary``, and a required ``items`` list, and returns a
    resolved list where each item has its own ``outcome`` and ``summary``
    (applying defaults where the item omits them).

    Args:
        payload: Dict with keys ``default_outcome`` (str, optional,
            defaults to ``"approve"``), ``default_summary`` (str, optional),
            and ``items`` (list of dicts, each with at least ``file_path``).

    Returns:
        A new list of dicts — one per item — each containing at minimum
        ``file_path``, ``outcome``, ``summary``, and optionally
        ``suggestions``.
    """
    default_outcome = payload.get("default_outcome", "approve")
    default_summary = payload.get("default_summary")
    items = payload.get("items", [])

    resolved: list[dict] = []
    for item in items:
        # Non-dict items are passed through so validate_batch_reviews()
        # can surface a user-friendly error instead of an opaque TypeError.
        if not isinstance(item, dict):
            resolved.append(item)
            continue
        resolved_item = dict(item)  # shallow copy

        # Apply default outcome if missing/empty
        raw_outcome = resolved_item.get("outcome")
        if _is_empty_or_whitespace(raw_outcome):
            resolved_item["outcome"] = default_outcome
        elif isinstance(raw_outcome, str):
            resolved_item["outcome"] = raw_outcome.strip().lower()

        # Apply default summary if missing/empty
        raw_summary = resolved_item.get("summary")
        if _is_empty_or_whitespace(raw_summary):
            resolved_item["summary"] = default_summary
        elif isinstance(raw_summary, str):
            resolved_item["summary"] = raw_summary.strip()

        resolved.append(resolved_item)

    return resolved


def validate_batch_reviews(resolved_items: list[dict]) -> list[str]:
    """Validate a list of resolved batch review items.

    Checks that every item has a valid ``file_path``, a recognised
    ``outcome``, a non-empty ``summary``, and (for non-approve outcomes)
    a non-empty list of suggestion dicts.

    Args:
        resolved_items: List of dicts as returned by
            :func:`resolve_batch_reviews`.

    Returns:
        A list of human-readable error strings.  An empty list means all
        items are valid.
    """
    errors: list[str] = []

    for i, item in enumerate(resolved_items):
        if not isinstance(item, dict):
            errors.append(f"Item {i}: not a JSON object.")
            continue

        file_path = item.get("file_path")
        if not file_path or not isinstance(file_path, str) or not file_path.strip():
            errors.append(f"Item {i}: missing or empty 'file_path'.")
            continue

        outcome = item.get("outcome")
        if not isinstance(outcome, str):
            errors.append(f"Item {i} ({file_path}): 'outcome' must be a string (got {type(outcome).__name__}).")
            continue

        outcome_lower = outcome.strip().lower()
        if outcome_lower not in _VALID_OUTCOMES:
            errors.append(f"Item {i} ({file_path}): unknown outcome '{outcome}'.")
            continue

        summary = item.get("summary")
        if _is_empty_or_whitespace(summary):
            errors.append(f"Item {i} ({file_path}): summary is required.")
            continue

        if outcome_lower != "approve":
            suggestions = item.get("suggestions")
            if not isinstance(suggestions, list) or not suggestions:
                errors.append(f"Item {i} ({file_path}): suggestions must be a non-empty list for '{outcome}'.")
                continue

            for j, suggestion in enumerate(suggestions):
                if not isinstance(suggestion, dict):
                    errors.append(
                        f"Item {i} ({file_path}): suggestion at index {j} must be an object/dict"
                        f" (got {type(suggestion).__name__})."
                    )
                    break

    return errors
