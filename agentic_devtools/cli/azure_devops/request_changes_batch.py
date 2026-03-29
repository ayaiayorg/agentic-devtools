"""
Batch request-changes for multiple files with per-file suggestions.

Provides ``request_changes_batch_cli()`` — a convenience wrapper that
pre-sets ``default_outcome="request-changes"`` and delegates all resolution,
validation, and enqueue logic to the shared helpers in :mod:`submit_reviews`.
"""

from __future__ import annotations

import argparse
import json
import sys

from ...state import get_pull_request_id, is_dry_run
from .submit_reviews import resolve_batch_reviews, validate_batch_reviews


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
            "A JSON string with the same schema as agdt-submit-reviews. "
            'default_outcome is pre-set to "request-changes" if not provided.'
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
        print(f"--reviews is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(payload, dict):
        print("--reviews must be a JSON object.", file=sys.stderr)
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

    # Enqueue
    from agentic_devtools.submission_manager_instance import get_submission_manager

    manager = get_submission_manager()
    for item in resolved:
        manager.enqueue(
            pr_id=pr_id,
            file_path=item["file_path"],
            outcome=item["outcome"],
            summary=item["summary"],
            suggestions=item.get("suggestions"),
        )

    print(f"✅ {len(resolved)} file(s) enqueued with request-changes.")
    for item in resolved:
        print(f"  {item['file_path']}")
