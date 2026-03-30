"""
Batch request-changes for multiple files with per-file suggestions.

Provides ``request_changes_batch_cli()`` — a convenience wrapper that
pre-sets ``default_outcome="request-changes"`` and delegates to
``submit_reviews_async()`` for durable background execution.
"""

from __future__ import annotations

import argparse
import json
import sys

from ...state import get_pull_request_id, is_dry_run
from .batch_review_helpers import resolve_batch_reviews, validate_batch_reviews


def request_changes_batch_cli() -> None:
    """CLI entry point for agdt-request-changes-batch."""
    parser = argparse.ArgumentParser(
        prog="agdt-request-changes-batch",
        description="Batch request-changes for multiple files with per-file suggestions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agdt-request-changes-batch \\
    --pull-request-id 12345 \\
    --reviews '{
      "default_summary": "Needs fixes",
      "items": [
        {"file_path": "/src/a.ts",
         "suggestions": [{"line": 10, "severity": "high", "content": "Missing null check"}]},
        {"file_path": "/src/b.ts",
         "suggestions": [{"line": 5, "severity": "medium", "content": "Rename variable"}]}
      ]
    }'
        """,
    )
    parser.add_argument(
        "--reviews",
        type=str,
        required=True,
        help=(
            "A JSON object containing an 'items' array of per-file reviews, "
            "with optional 'default_summary' and 'default_outcome' fields. "
            'If default_outcome is omitted, it is pre-set to "request-changes".'
        ),
    )
    parser.add_argument(
        "--pull-request-id",
        "-p",
        type=int,
        default=None,
        help="Pull request ID (falls back to pull_request_id state)",
    )
    args = parser.parse_args()

    # Parse --reviews JSON
    try:
        payload = json.loads(args.reviews)
    except json.JSONDecodeError as e:
        print(f"Error: --reviews is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(payload, dict):
        print("Error: --reviews must be a JSON object.", file=sys.stderr)
        sys.exit(1)

    # Inject default_outcome if not already present
    payload.setdefault("default_outcome", "request-changes")

    # Resolve pull_request_id
    if args.pull_request_id is not None:
        pr_id = args.pull_request_id
    else:
        pr_id = get_pull_request_id(required=True)

    # Resolve + validate
    resolved = resolve_batch_reviews(payload)

    if not resolved:
        print("Error: --reviews must contain at least one item.", file=sys.stderr)
        sys.exit(1)

    errors = validate_batch_reviews(resolved)
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        sys.exit(1)

    # Dry-run check
    if is_dry_run():
        print(f"[DRY RUN] Would enqueue {len(resolved)} item(s):")
        for item in resolved:
            print(f"  {item['file_path']} — {item['outcome']}")
        return

    # Delegate to submit_reviews_async for durable background execution.
    # This stores the payload in state and spawns a background subprocess
    # via run_function_in_background, consistent with other agdt action commands.
    from .async_commands import submit_reviews_async

    submit_reviews_async(
        reviews=json.dumps(resolved),
        default_outcome=payload.get("default_outcome"),
        default_summary=payload.get("default_summary"),
        pull_request_id=pr_id,
    )
