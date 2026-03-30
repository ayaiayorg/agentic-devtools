"""
Batch review resolution and validation helpers.

Provides importable pure functions for constructing, resolving, and
validating batch file-review payloads. These helpers are currently used by
``agdt-approve-files`` and ``agdt-request-changes-batch`` so that validation
and default-application logic is defined in exactly one place. They are also
intended to be reused by a future refactor of ``agdt-submit-reviews``.
"""

from __future__ import annotations

# Valid outcomes for batch reviews (compared case-insensitively)
_VALID_OUTCOMES = frozenset({"approve", "request-changes", "request-changes-with-suggestion"})

# Valid severity values for suggestions (compared case-insensitively)
_VALID_SEVERITIES = frozenset({"high", "medium", "low"})


def _is_empty_or_whitespace(value: object) -> bool:
    """Return True if *value* is None or a whitespace-only string.

    Non-string falsy values (e.g., ``False``, ``0``, ``[]``) are **not**
    treated as empty — they are left untouched so that
    :func:`validate_batch_reviews` can surface a type error instead of
    silently replacing them with a default.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def resolve_batch_reviews(payload: dict) -> list[object]:
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
    raw_items = payload.get("items")

    # Normalize items to a list so non-list / None values surface as
    # validation errors instead of crashing with TypeError.
    if raw_items is None:
        items: list[object] = []
    elif isinstance(raw_items, list):
        items = raw_items
    else:
        items = [raw_items]

    resolved: list[object] = []
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

        # Normalize file_path by stripping leading/trailing whitespace so that
        # downstream consumers (including review-state lookups) see a
        # consistent, normalized path.  Non-string values are left untouched so
        # that validate_batch_reviews() can surface a type error.
        raw_file_path = resolved_item.get("file_path")
        if isinstance(raw_file_path, str):
            stripped_path = raw_file_path.strip()
            if stripped_path != raw_file_path:
                resolved_item["file_path"] = stripped_path

        resolved.append(resolved_item)

    return resolved


def validate_batch_reviews(resolved_items: list[object]) -> list[str]:
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
        if not isinstance(summary, str):
            errors.append(
                f"Item {i} ({file_path}): 'summary' must be a string (got {type(summary).__name__})."
            )
            continue

        if not summary.strip():
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

                # Validate required suggestion fields: line, severity, content
                sg_errors = _validate_suggestion_fields(suggestion, i, j, file_path, outcome_lower)
                if sg_errors:
                    errors.extend(sg_errors)
                    break

    return errors


def _validate_suggestion_fields(
    suggestion: dict, item_idx: int, sg_idx: int, file_path: str, outcome: str
) -> list[str]:
    """Validate required fields on a single suggestion dict.

    Returns a list of error strings (empty if valid).
    """
    errors: list[str] = []
    prefix = f"Item {item_idx} ({file_path}), suggestion {sg_idx}"

    # line — required, must be int ≥ 1 (reject bool since bool is a subclass of int)
    line = suggestion.get("line")
    if isinstance(line, bool) or not isinstance(line, int):
        errors.append(f"{prefix}: 'line' must be an integer (got {type(line).__name__}).")
    elif line < 1:
        errors.append(f"{prefix}: 'line' must be ≥ 1 (got {line}).")

    # severity — required, must be one of high/medium/low
    severity = suggestion.get("severity")
    if not isinstance(severity, str):
        errors.append(f"{prefix}: 'severity' must be a string (got {type(severity).__name__}).")
    elif severity.strip().lower() not in _VALID_SEVERITIES:
        errors.append(f"{prefix}: unknown severity '{severity}' (must be high/medium/low).")

    # content — required, non-empty string
    content = suggestion.get("content")
    if not isinstance(content, str):
        errors.append(f"{prefix}: 'content' must be a string (got {type(content).__name__}).")
    elif not content.strip():
        errors.append(f"{prefix}: 'content' must not be empty.")

    # replacement_code — required for request-changes-with-suggestion, non-empty string
    if outcome == "request-changes-with-suggestion":
        replacement_code = suggestion.get("replacement_code")
        if not isinstance(replacement_code, str):
            errors.append(f"{prefix}: 'replacement_code' is required for '{outcome}'.")
        elif not replacement_code.strip():
            errors.append(f"{prefix}: 'replacement_code' must not be empty.")

    return errors
