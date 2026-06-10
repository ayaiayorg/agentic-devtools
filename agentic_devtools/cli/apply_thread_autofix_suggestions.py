"""Unified command to apply PR thread autofix suggestions across platforms.

Dispatches to the appropriate platform-specific implementation based on
``platform.code_hosting`` in ``.github/agdt-config.json``.

Supported platforms:
- ``github``: Scrapes embedded React partial JSON from PR page HTML
- ``azure_devops``: (future) Extracts from ADO review threads

Usage:
    agdt-apply-pr-thread-autofix-suggestions --pr 2008
    agdt-apply-pr-thread-autofix-suggestions --pr 2008 --comment-ids 123,456
    agdt-apply-pr-thread-autofix-suggestions --pr 2008 --no-resolve
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys

from ..config import load_platform_config
from ..state import get_value, set_value


def _log(msg: str, *, tag: str = "INFO") -> None:
    """Log a structured message to stderr for diagnostics."""
    print(f"[agdt-apply-pr-thread-autofix-suggestions][{tag}] {msg}", file=sys.stderr)


def _detect_platform() -> str:
    """Detect the code hosting platform from agdt-config.json.

    Returns 'github' or 'azure_devops'. Defaults to 'github' if
    not configured.
    """
    try:
        from ..state import _get_git_repo_root

        git_root = _get_git_repo_root()
        if git_root is None:
            _log("Not in a git repository, defaulting to github", tag="WARN")
            return "github"
        config = load_platform_config(str(git_root))
    except Exception as exc:
        _log(f"Failed to load platform config: {exc}, defaulting to github", tag="WARN")
        return "github"

    code_hosting = config.get("code_hosting", "github")
    _KNOWN_PLATFORMS = {"github", "azure_devops"}
    if code_hosting not in _KNOWN_PLATFORMS:
        _log(
            f"Unknown platform '{code_hosting}' in agdt-config.json, defaulting to github",
            tag="WARN",
        )
        return "github"
    _log(f"Detected platform: {code_hosting}")
    return code_hosting


def _apply_github(
    pr_number: int,
    repo: str | None,
    comment_ids: list[int] | None,
    message: str,
    resolve: bool,
) -> dict:
    """Dispatch to GitHub implementation."""
    from .github.apply_thread_autofix import apply_pr_suggestions
    from .github.repo_resolution import resolve_github_repo

    resolved_repo = resolve_github_repo(repo)
    return apply_pr_suggestions(
        pr_number=pr_number,
        repo=resolved_repo,
        comment_ids=comment_ids,
        message=message,
        resolve=resolve,
    )


def _apply_azure_devops(
    pr_number: int,
    repo: str | None,
    comment_ids: list[int] | None,
    message: str,
    resolve: bool,
) -> dict:
    """Dispatch to Azure DevOps implementation (not yet implemented)."""
    _log(
        "Azure DevOps autofix suggestion application is not yet implemented. Contributions welcome!",
        tag="ERROR",
    )
    return {
        "applied": 0,
        "skipped": 0,
        "conflict_comment_ids": [],
        "commit": None,
        "files_changed": [],
        "resolution": None,
        "error": "Azure DevOps implementation not yet available",
    }


def apply_pr_autofix_suggestions_command() -> None:
    """CLI entry point for agdt-apply-pr-thread-autofix-suggestions."""
    parser = argparse.ArgumentParser(
        description=(
            "Apply PR review autofix suggestions. "
            "Dispatches to the correct platform (GitHub / Azure DevOps) "
            "based on .github/agdt-config.json"
        )
    )
    parser.add_argument("--pr", type=int, default=None, help="PR number")
    parser.add_argument("--repo", type=str, default=None, help="owner/repo (GitHub) or project/repo (ADO)")
    parser.add_argument(
        "--comment-ids",
        type=str,
        default=None,
        help="Comma-separated comment database IDs to apply",
    )
    parser.add_argument(
        "--message",
        type=str,
        default="Apply suggestions from code review",
        help="Commit message",
    )
    parser.add_argument(
        "--no-resolve",
        action="store_true",
        default=False,
        help="Skip posting replies and resolving threads",
    )
    parser.add_argument(
        "--platform",
        type=str,
        default=None,
        choices=["github", "azure_devops"],
        help="Override platform detection (default: read from .github/agdt-config.json)",
    )
    args = parser.parse_args()

    # Detect platform before checking for tool availability so that
    # platform-specific tool requirements (gh for GitHub, az for Azure DevOps)
    # are only enforced for the selected platform.
    platform = args.platform or _detect_platform()

    if platform == "github" and not shutil.which("gh"):
        _log("gh CLI not found in PATH", tag="ERROR")
        sys.exit(1)

    # Resolve PR number
    pr_number = args.pr
    if pr_number is None:
        state_val = get_value("github.pull_request_number")
        if state_val is not None:
            try:
                pr_number = int(state_val)
            except (TypeError, ValueError):
                _log(
                    "github.pull_request_number in state is not a valid integer",
                    tag="ERROR",
                )
                sys.exit(1)
    if pr_number is None:
        _log("--pr or github.pull_request_number required", tag="ERROR")
        sys.exit(1)

    # Resolve comment IDs
    comment_ids = None
    if args.comment_ids:
        try:
            parts = [c.strip() for c in args.comment_ids.split(",") if c.strip()]
            if not parts:
                raise ValueError("empty list")
            comment_ids = [int(c) for c in parts]
        except ValueError:
            _log(
                "--comment-ids must be a comma-separated list of integers (e.g. 123,456)",
                tag="ERROR",
            )
            sys.exit(1)

    # Dispatch
    if platform == "github":
        result = _apply_github(
            pr_number=pr_number,
            repo=args.repo,
            comment_ids=comment_ids,
            message=args.message,
            resolve=not args.no_resolve,
        )
    elif platform == "azure_devops":
        result = _apply_azure_devops(
            pr_number=pr_number,
            repo=args.repo,
            comment_ids=comment_ids,
            message=args.message,
            resolve=not args.no_resolve,
        )
    else:  # pragma: no cover — argparse choices= prevents this
        _log(f"Unsupported platform: {platform!r}", tag="ERROR")
        sys.exit(1)

    # Write state
    if result.get("commit"):
        set_value("github.applied_suggestions_commit", result["commit"])

    print(json.dumps(result, indent=2))
