"""
GitHub PR creation using ``gh pr create``.

Provides ``create_pull_request()`` which resolves the PR body from the shared
template module and invokes the GitHub CLI.
"""

import argparse
import os
import re
import sys
import tempfile

from ...state import get_value, is_dry_run, set_value
from ..pr_template import resolve_pr_body
from ..subprocess_utils import run_safe


def create_pull_request(
    title: str | None = None,
    body: str | None = None,
    base: str | None = None,
    draft: bool | None = None,
) -> None:
    """Create a GitHub pull request using ``gh pr create``.

    Args:
        title: PR title. Falls back to state key ``title``.
        body: PR body. Falls back to ``resolve_pr_body()``.
        base: Target branch. Falls back to state key ``target_branch`` or ``main``.
        draft: Whether to create as draft. When ``None`` (default), the state key
            ``draft`` is consulted; if absent, defaults to ``True``.  An explicit
            ``True``/``False`` value is always honoured and state is not consulted,
            so ``--no-draft`` on the CLI cannot be silently overridden.
    """
    if title is None:
        title = get_value("title")
    if not title:
        print(
            'Error: No title found. Use: agdt-set title "PR title"',
            file=sys.stderr,
        )
        sys.exit(1)

    if body is None:
        body = resolve_pr_body()

    if base is None:
        base = get_value("target_branch") or "main"

    # Draft mode: only consult state when the caller did not supply an explicit value.
    if draft is None:
        draft_raw = get_value("draft")
        if draft_raw is None:
            draft = True
        elif isinstance(draft_raw, bool):
            draft = draft_raw
        else:
            draft = str(draft_raw).lower() not in ("0", "false", "no")

    dry_run = is_dry_run()

    if dry_run:
        print("[DRY RUN] Would create GitHub PR:")
        print(f"  Title: {title}")
        print(f"  Base: {base}")
        print(f"  Draft: {draft}")
        if body:
            truncated = body[:200] + "..." if len(body) > 200 else body
            print(f"  Body: {truncated}")
        return

    # Write body to a temp file and use --body-file to avoid OS arg-length
    # limits (large commit messages or templates can exceed the limit).
    # NamedTemporaryFile(delete=False) ensures the fd is always closed when
    # the with-block exits, preventing fd leaks on any error path.
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as tf:
        tf.write(body or "")
        tmp_body_path = tf.name

    try:
        cmd = [
            "gh",
            "pr",
            "create",
            "--title",
            title,
            "--body-file",
            tmp_body_path,
            "--base",
            base,
        ]

        if draft:
            cmd.append("--draft")

        result = run_safe(cmd, capture_output=True, text=True, shell=False)
    finally:
        # Best-effort cleanup — PR was already submitted; ignore any OS error
        # (e.g. PermissionError on Windows, FileNotFoundError on race).
        try:
            os.unlink(tmp_body_path)
        except OSError:
            pass

    if result.returncode != 0:
        print(f"Error creating GitHub PR: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # gh pr create outputs the PR URL on success
    pr_url = result.stdout.strip()
    print(f"Pull request created: {pr_url}")

    # Extract and persist the PR number so follow-up agdt-gh-* commands can
    # default to the newly created PR without requiring --pr.
    pr_number_match = re.search(r"/pull/(\d+)$", pr_url)
    if pr_number_match:
        pr_number = int(pr_number_match.group(1))
        set_value("github.pull_request_number", pr_number)


def create_pull_request_command() -> None:
    """CLI entry point for ``agdt-gh-create-pull-request``."""
    parser = argparse.ArgumentParser(description="Create a GitHub pull request")
    parser.add_argument("--title", "-t", type=str, help="PR title")
    parser.add_argument("--body", "-b", type=str, help="PR body")
    parser.add_argument("--base", type=str, help="Target branch (default: main)")
    parser.add_argument(
        "--no-draft",
        action="store_true",
        help="Create as non-draft PR",
    )
    args, _ = parser.parse_known_args()

    create_pull_request(
        title=args.title,
        body=args.body,
        base=args.base,
        # Pass False explicitly when --no-draft is given so state cannot override it.
        # Pass None otherwise so the state key / default (True) can take effect.
        draft=False if args.no_draft else None,
    )
