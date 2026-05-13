"""CI workflow safety guards.

Extracted from ai-pr-loop.yml — these guards determine whether a PR
should be processed by the AI loop or requires human intervention.
"""

from __future__ import annotations

import re

from agentic_devtools.cli.ci.provider import CIPlatformProvider

# Privileged path prefixes that trigger the guard
PRIVILEGED_PREFIXES = (
    ".github/workflows/",
    ".github/actions/",
    ".github/scripts/",
)

# Docker files that trigger the guard
DOCKER_FILES = {"Dockerfile", "docker-compose.yml", "docker-compose.yaml"}
DOCKER_PATTERNS = (re.compile(r"^\.dockerignore$"), re.compile(r"^Dockerfile\..*$"))

# Labels that affect PR processing
LABEL_SKIP_ENTIRELY = "ai-pr-loop-ignore"
LABEL_NO_AUTO_MERGE = "do-not-auto-merge"

# Deduplication marker format
DEDUP_MARKER_PREFIX = "<!-- repair-dispatch:"
DEDUP_MARKER_PATTERN = re.compile(r"<!-- repair-dispatch:([a-f0-9]+):(\d+) -->")

# Default limits
DEFAULT_MAX_DISPATCHES_PER_SHA = 3
DEFAULT_MAX_CYCLES = 50

# Cycle tracker marker
CYCLE_TRACKER_MARKER = "<!-- ai-pr-loop-cycle-tracker -->"


def check_privileged_paths(files: list[str]) -> bool:
    """Check if any PR files touch privileged paths.

    Privileged paths are `.github/workflows/`, `.github/actions/`,
    `.github/scripts/` — excluding markdown files (*.md).

    Args:
        files: List of file paths changed in the PR.

    Returns:
        True if privileged paths are touched (guard triggered), False otherwise.
    """
    for f in files:
        if any(f.startswith(prefix) for prefix in PRIVILEGED_PREFIXES):
            if not f.endswith(".md"):
                return True
    return False


def check_docker_files(files: list[str]) -> bool:
    """Check if any PR files are Docker-related.

    Matches: Dockerfile, docker-compose.yml, docker-compose.yaml,
    .dockerignore, Dockerfile.* (e.g., Dockerfile.prod).

    Args:
        files: List of file paths changed in the PR.

    Returns:
        True if Docker files are touched (guard triggered), False otherwise.
    """
    for f in files:
        # Get the basename for matching
        basename = f.rsplit("/", 1)[-1] if "/" in f else f
        if basename in DOCKER_FILES:
            return True
        if any(pattern.match(basename) for pattern in DOCKER_PATTERNS):
            return True
    return False


def check_deduplication(
    provider: CIPlatformProvider,
    pr_number: int,
    head_sha: str,
    max_dispatches: int = DEFAULT_MAX_DISPATCHES_PER_SHA,
) -> tuple[bool, int]:
    """Check deduplication via marker comment on the PR.

    Reads/upserts a marker PR comment with format:
    ``<!-- repair-dispatch:<sha>:<count> -->``

    Args:
        provider: CI platform provider for API calls.
        pr_number: Pull request number.
        head_sha: Current HEAD SHA.
        max_dispatches: Maximum dispatches allowed per SHA.

    Returns:
        Tuple of (should_skip, current_count). should_skip is True if
        the dispatch count has been exceeded.
    """
    existing = provider.find_comment(pr_number, DEDUP_MARKER_PREFIX)

    if existing is not None:
        comment_id, comment_body = existing
        match = DEDUP_MARKER_PATTERN.search(comment_body)
        if match and match.group(1) == head_sha:
            count = int(match.group(2)) + 1
            # Always persist the incremented count so the marker stays accurate
            new_marker = f"<!-- repair-dispatch:{head_sha}:{count} -->"
            new_body = DEDUP_MARKER_PATTERN.sub(new_marker, comment_body)
            provider.update_comment(comment_id, new_body)
            if count > max_dispatches:
                return (True, count)
            return (False, count)

    # New SHA or no existing marker — create/update with count 1
    marker_body = f"<!-- repair-dispatch:{head_sha}:1 -->\nDispatch tracking for `{head_sha[:8]}`"
    if existing is not None:
        provider.update_comment(existing[0], marker_body)
    else:
        provider.post_comment(pr_number, marker_body)
    return (False, 1)


def check_exclusion_labels(labels: list[str]) -> tuple[bool, str | None]:
    """Check if PR labels trigger exclusion logic.

    Args:
        labels: List of label names on the PR.

    Returns:
        Tuple of (should_skip, flag_name).
        - should_skip=True, flag_name=None: skip entirely (ai-pr-loop-ignore)
        - should_skip=False, flag_name="do_not_merge": process but don't merge
        - should_skip=False, flag_name=None: no exclusion
    """
    if LABEL_SKIP_ENTIRELY in labels:
        return (True, None)
    if LABEL_NO_AUTO_MERGE in labels:
        return (False, "do_not_merge")
    return (False, None)


def check_fork_pr(head_repo: str, base_repo: str) -> bool:
    """Check if a PR is from a fork (different repository).

    Args:
        head_repo: Full name of the head (source) repository.
        base_repo: Full name of the base (target) repository.

    Returns:
        True if the PR is from a fork (guard triggered), False otherwise.
    """
    return head_repo != base_repo


def check_cycle_limit(
    provider: CIPlatformProvider,
    pr_number: int,
    max_cycles: int = DEFAULT_MAX_CYCLES,
) -> tuple[bool, int]:
    """Check if the AI loop cycle limit has been reached.

    Reads/updates a cycle tracker comment on the PR.

    Args:
        provider: CI platform provider for API calls.
        pr_number: Pull request number.
        max_cycles: Maximum allowed cycles.

    Returns:
        Tuple of (limit_reached, current_count).
    """
    existing = provider.find_comment(pr_number, CYCLE_TRACKER_MARKER)

    if existing is not None:
        comment_id, comment_body = existing
        # Extract current count from body
        count_match = re.search(r"cycle:(\d+)", comment_body)
        current_count = int(count_match.group(1)) + 1 if count_match else 1

        if current_count > max_cycles:
            return (True, current_count)

        # Update count
        if count_match:
            new_body = re.sub(r"cycle:\d+", f"cycle:{current_count}", comment_body)
        else:
            new_body = f"{CYCLE_TRACKER_MARKER} cycle:{current_count}"
        provider.update_comment(comment_id, new_body)
        return (False, current_count)

    # First cycle — create tracker
    body = f"{CYCLE_TRACKER_MARKER} cycle:1"
    provider.post_comment(pr_number, body)
    return (False, 1)
