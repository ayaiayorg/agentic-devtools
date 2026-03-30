"""
Batch approve multiple files with a shared summary.

Provides ``approve_files_cli()`` — a convenience wrapper that constructs an
``agdt-submit-reviews``-compatible payload with ``default_outcome="approve"``
and delegates to ``submit_reviews_async()`` for durable background execution.
"""

from __future__ import annotations

import argparse
import json
import sys

from ...state import get_pull_request_id, is_dry_run
from .batch_review_helpers import resolve_batch_reviews, validate_batch_reviews


def approve_files_cli() -> None:
    """CLI entry point for agdt-approve-files."""
    parser = argparse.ArgumentParser(
        prog="agdt-approve-files",
        description="Batch approve multiple files with a shared summary",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Approve two files with the same summary
  agdt-approve-files \\
    --summary "Mechanical refactor only. LGTM." \\
    --file-paths '["/src/a.ts","/src/b.ts"]'

  # With explicit PR ID
  agdt-approve-files \\
    --pull-request-id 12345 \\
    --summary "LGTM." \\
    --file-paths '["/src/a.ts"]'
        """,
    )
    parser.add_argument(
        "--summary",
        type=str,
        required=True,
        help="The approval summary applied to all files.",
    )
    parser.add_argument(
        "--file-paths",
        type=str,
        required=True,
        help='A JSON array string of file paths (e.g., \'["/src/a.ts","/src/b.ts"]\')',
    )
    parser.add_argument(
        "--pull-request-id",
        "-p",
        type=int,
        default=None,
        help="Pull request ID (falls back to pull_request_id state)",
    )
    args = parser.parse_args()

    # Parse --file-paths JSON
    try:
        file_paths = json.loads(args.file_paths)
    except json.JSONDecodeError as e:
        print(f"Error: --file-paths is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(file_paths, list):
        print("Error: --file-paths must be a JSON array.", file=sys.stderr)
        sys.exit(1)

    if not file_paths:
        print("Error: --file-paths must contain at least one file path.", file=sys.stderr)
        sys.exit(1)

    for i, entry in enumerate(file_paths):
        if not isinstance(entry, str) or not entry.strip():
            print(f"Error: --file-paths item {i}: must be a non-empty string.", file=sys.stderr)
            sys.exit(1)
        file_paths[i] = entry.strip()

    # Resolve pull_request_id
    if args.pull_request_id is not None:
        pr_id = args.pull_request_id
    else:
        pr_id = get_pull_request_id(required=False)
        if pr_id is None:
            print(
                "Error: pull request ID is required. Provide --pull-request-id or set pull_request_id in state.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Build payload
    payload = {
        "default_outcome": "approve",
        "default_summary": args.summary,
        "items": [{"file_path": p} for p in file_paths],
    }

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

    # Delegate to submit_reviews_async for durable background execution.
    # This stores the payload in state and spawns a background subprocess
    # via run_function_in_background, consistent with other agdt action commands.
    from .async_commands import submit_reviews_async

    submit_reviews_async(
        reviews=json.dumps(resolved),
        default_outcome="approve",
        default_summary=args.summary,
        pull_request_id=pr_id,
    )
