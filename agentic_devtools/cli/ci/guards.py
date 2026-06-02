"""CI workflow safety guards.

Extracted from ai-pr-loop.yml — these guards determine whether a PR
should be processed by the AI loop or requires human intervention.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import datetime, timezone

from agentic_devtools.cli.ci.models import EventPayload
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)

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
LABEL_AUTO_MERGE_ALLOWED = "ai-auto-merge-allowed"

# Deduplication marker format
DEDUP_MARKER_PREFIX = "<!-- repair-dispatch:"
DEDUP_MARKER_PATTERN = re.compile(r"<!-- repair-dispatch:([a-f0-9]+):(\d+)(?::([A-Za-z0-9._-]+))? -->")

# Squash-wait marker constants
SQUASH_WAIT_MARKER_PREFIX = "<!-- squash-wait\n"
SQUASH_WAIT_MAX_ATTEMPTS = 24  # 24 × 5 min cron = ~120 minutes

# Default limits
DEFAULT_MAX_DISPATCHES_PER_SHA = 3
DEFAULT_MAX_CYCLES = 50

# Cycle tracker marker
CYCLE_TRACKER_MARKER = "<!-- ai-pr-loop-cycle-tracker -->"

_DEDUP_WRITER_TOKEN: str | None = None


def get_dedup_writer_token() -> str:
    """Return a per-process token stamped into dedup markers."""
    global _DEDUP_WRITER_TOKEN
    if _DEDUP_WRITER_TOKEN is not None:
        return _DEDUP_WRITER_TOKEN

    run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "").strip()
    job = os.environ.get("GITHUB_JOB", "").strip().replace(" ", "-")
    if run_id:
        parts = [run_id]
        if attempt:
            parts.append(attempt)
        if job:
            parts.append(job)
        _DEDUP_WRITER_TOKEN = ".".join(parts)
    else:
        _DEDUP_WRITER_TOKEN = f"local.{uuid.uuid4().hex[:12]}"

    return _DEDUP_WRITER_TOKEN


def check_privileged_paths(files: list[str]) -> bool:
    """Check if any PR files touch privileged paths.

    Privileged paths are `.github/workflows/`, `.github/actions/`,
    `.github/scripts/` — excluding markdown files (*.md).

    This guard can be disabled by setting the environment variable
    ``AGDT_ALLOW_PRIVILEGED_PATHS=1`` (also accepts ``true`` / ``yes``).
    Use this only when you intentionally want the AI loop to process PRs
    that modify workflow or action files.

    Args:
        files: List of file paths changed in the PR.

    Returns:
        True if privileged paths are touched (guard triggered), False otherwise.
    """
    if os.environ.get("AGDT_ALLOW_PRIVILEGED_PATHS", "").strip().lower() in {"1", "true", "yes"}:
        logger.warning(
            "Privileged paths guard bypassed via AGDT_ALLOW_PRIVILEGED_PATHS; "
            "PR may include workflow/action/script changes"
        )
        return False

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


def is_duplicate_trigger(
    provider: CIPlatformProvider,
    pr_number: int,
    review_id: int,
) -> bool:
    """Check if a trigger comment already exists for a given Copilot review ID.

    Searches PR comments for the ``<!-- copilot-trigger:REVIEW_ID -->`` marker.
    This provides best-effort review-cycle-level deduplication by skipping when
    a prior trigger marker is already present for the same Copilot review.

    Args:
        provider: CI platform provider for API calls.
        pr_number: Pull request number.
        review_id: Copilot review ID to check for.

    Returns:
        True if a trigger comment for this review_id already exists, False otherwise.
    """
    if review_id <= 0:
        return False
    marker = f"<!-- copilot-trigger:{review_id} -->"
    existing = provider.find_comment(pr_number, marker)
    return existing is not None


def check_deduplication(
    provider: CIPlatformProvider,
    pr_number: int,
    head_sha: str,
    max_dispatches: int = DEFAULT_MAX_DISPATCHES_PER_SHA,
) -> tuple[bool, int]:
    """Check deduplication via marker comment on the PR.

    Reads/upserts a marker PR comment with format:
    ``<!-- repair-dispatch:<sha>:<count>:<writer_token> -->``
    (tokenless legacy markers are also accepted).

    Args:
        provider: CI platform provider for API calls.
        pr_number: Pull request number.
        head_sha: Current HEAD SHA.
        max_dispatches: Maximum dispatches allowed per SHA.

    Returns:
        Tuple of (should_skip, current_count). should_skip is True if
        the dispatch count has been exceeded.
    """
    writer_token = get_dedup_writer_token()
    existing = provider.find_comment(pr_number, DEDUP_MARKER_PREFIX)

    if existing is not None:
        comment_id, comment_body = existing
        match = DEDUP_MARKER_PATTERN.search(comment_body)
        if match and match.group(1) == head_sha:
            count = int(match.group(2)) + 1
            # Always persist the incremented count so the marker stays accurate
            new_marker = f"<!-- repair-dispatch:{head_sha}:{count}:{writer_token} -->"
            new_body = DEDUP_MARKER_PATTERN.sub(new_marker, comment_body)
            provider.update_comment(comment_id, new_body)
            if count > max_dispatches:
                return (True, count)
            return (False, count)

    # New SHA or no existing marker — create/update with count 1
    marker_body = f"<!-- repair-dispatch:{head_sha}:1:{writer_token} -->\nDispatch tracking for `{head_sha[:8]}`"
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
          (ai-auto-merge-allowed label missing)
        - should_skip=False, flag_name=None: no exclusion
    """
    if LABEL_SKIP_ENTIRELY in labels:
        return (True, None)
    if LABEL_AUTO_MERGE_ALLOWED not in labels:
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

    Reads a cycle tracker comment on the PR without mutating it.

    Args:
        provider: CI platform provider for API calls.
        pr_number: Pull request number.
        max_cycles: Maximum allowed cycles.

    Returns:
        Tuple of (limit_reached, current_count).
    """
    existing = provider.find_comment(pr_number, CYCLE_TRACKER_MARKER)

    current_count = 0
    if existing is not None:
        _, comment_body = existing
        count_match = re.search(r"cycle:(\d+)", comment_body)
        current_count = int(count_match.group(1)) if count_match else 0

    return (current_count >= max_cycles, current_count)


def increment_cycle_count(provider: CIPlatformProvider, pr_number: int) -> int:
    """Increment and persist the AI loop cycle count tracker comment.

    Args:
        provider: CI platform provider for API calls.
        pr_number: Pull request number.

    Returns:
        The updated cycle count after incrementing.
    """
    existing = provider.find_comment(pr_number, CYCLE_TRACKER_MARKER)

    if existing is not None:
        comment_id, comment_body = existing
        count_match = re.search(r"cycle:(\d+)", comment_body)
        next_count = int(count_match.group(1)) + 1 if count_match else 1
        if count_match:
            new_body = re.sub(r"cycle:\d+", f"cycle:{next_count}", comment_body)
        else:
            new_body = f"{comment_body} cycle:{next_count}"
        provider.update_comment(comment_id, new_body)
        return next_count

    body = f"{CYCLE_TRACKER_MARKER} cycle:1"
    provider.post_comment(pr_number, body)
    return 1


# ---------------------------------------------------------------------------
# Squash-wait marker helpers
# ---------------------------------------------------------------------------

_SQUASH_WAIT_FIELD_RE = re.compile(r"^(\w+)=(.*)$", re.MULTILINE)


def _build_squash_wait_body(
    *,
    pr_number: int,
    sha: str,
    attempt: int,
    head_pushed_at: str,
    ci_passed: bool,
    copilot_session_terminal: bool,
    copilot_session_outcome: str,
    squash_done: bool,
) -> str:
    """Build the full comment body for a squash-wait marker."""
    now = datetime.now(timezone.utc).isoformat()
    return (
        f"{SQUASH_WAIT_MARKER_PREFIX}"
        f"sha={sha}\n"
        f"attempt={attempt}\n"
        f"head_pushed_at={head_pushed_at}\n"
        f"ci_passed={'true' if ci_passed else 'false'}\n"
        f"copilot_session_terminal={'true' if copilot_session_terminal else 'false'}\n"
        f"copilot_session_outcome={copilot_session_outcome}\n"
        f"squash_done={'true' if squash_done else 'false'}\n"
        f"-->\n"
        f"Squash wait in progress for PR #{pr_number} — last checked {now}"
    )


def read_squash_wait_marker(
    provider: CIPlatformProvider,
    pr_number: int,
    head_sha: str,
) -> dict | None:
    """Read and parse the squash-wait marker comment for this PR.

    Returns a dict of parsed field values if the marker exists and the
    ``sha`` field matches ``head_sha``.  Returns ``None`` if the marker
    is absent or the SHA does not match the current head (indicating the
    marker is stale and belongs to a previous commit).

    Args:
        provider: CI platform provider for API calls.
        pr_number: Pull request number.
        head_sha: Current HEAD SHA to validate against the marker's sha field.

    Returns:
        Dict with keys sha, attempt (int), head_pushed_at, ci_passed (bool),
        copilot_session_terminal (bool), copilot_session_outcome, squash_done (bool),
        and comment_id (int).  Returns None when not found or SHA mismatch.
    """
    existing = provider.find_comment(pr_number, SQUASH_WAIT_MARKER_PREFIX)
    if existing is None:
        return None

    comment_id, comment_body = existing
    fields: dict[str, str] = {}
    for match in _SQUASH_WAIT_FIELD_RE.finditer(comment_body):
        fields[match.group(1)] = match.group(2).strip()

    marker_sha = fields.get("sha", "")
    if marker_sha != head_sha:
        logger.info(
            "PR #%d squash-wait marker SHA mismatch (marker=%s, head=%s) — treating as absent",
            pr_number,
            marker_sha[:8] if marker_sha else "",
            head_sha[:8] if head_sha else "",
        )
        return None

    def _bool(val: str) -> bool:
        return val.strip().lower() == "true"

    try:
        attempt = int(fields.get("attempt", "0"))
    except ValueError:
        logger.warning(
            "PR #%d squash-wait marker has non-integer attempt value (%r) — treating marker as absent",
            pr_number,
            fields.get("attempt"),
        )
        return None

    copilot_session_terminal = _bool(fields.get("copilot_session_terminal", "false"))
    copilot_session_outcome = fields.get("copilot_session_outcome", "pending").strip().lower()
    valid_outcomes = {"pending", "success", "failure"}
    if copilot_session_outcome not in valid_outcomes:
        logger.warning(
            "PR #%d squash-wait marker has invalid copilot_session_outcome value (%r) — treating marker as absent",
            pr_number,
            fields.get("copilot_session_outcome"),
        )
        return None
    if copilot_session_terminal and copilot_session_outcome == "pending":
        logger.warning(
            "PR #%d squash-wait marker has inconsistent terminal/outcome values (terminal=true, outcome=pending) "
            "— treating marker as absent",
            pr_number,
        )
        return None
    if not copilot_session_terminal and copilot_session_outcome in {"success", "failure"}:
        logger.warning(
            "PR #%d squash-wait marker has inconsistent terminal/outcome values (terminal=false, outcome=%s) "
            "— treating marker as absent",
            pr_number,
            copilot_session_outcome,
        )
        return None

    return {
        "comment_id": comment_id,
        "sha": marker_sha,
        "attempt": attempt,
        "head_pushed_at": fields.get("head_pushed_at", ""),
        "ci_passed": _bool(fields.get("ci_passed", "false")),
        "copilot_session_terminal": copilot_session_terminal,
        "copilot_session_outcome": copilot_session_outcome,
        "squash_done": _bool(fields.get("squash_done", "false")),
    }


def write_squash_wait_marker(
    provider: CIPlatformProvider,
    pr_number: int,
    *,
    sha: str,
    attempt: int,
    head_pushed_at: str,
    ci_passed: bool,
    copilot_session_terminal: bool,
    copilot_session_outcome: str,
    squash_done: bool,
) -> None:
    """Upsert the squash-wait marker comment on the PR.

    Creates the marker comment if it does not exist; updates it in-place
    if it already exists (identified by ``SQUASH_WAIT_MARKER_PREFIX``).

    Args:
        provider: CI platform provider for API calls.
        pr_number: Pull request number.
        sha: Full head SHA this marker tracks.
        attempt: Current attempt number (1-based).
        head_pushed_at: ISO 8601 UTC reference timestamp used to scope
            Copilot session events for the tracked head SHA.
        ci_passed: Whether CI has passed for this SHA (always True when first written).
        copilot_session_terminal: Whether a terminal session event was found.
        copilot_session_outcome: One of ``"pending"``, ``"success"``, ``"failure"``.
        squash_done: Whether the squash has been executed.
    """
    body = _build_squash_wait_body(
        pr_number=pr_number,
        sha=sha,
        attempt=attempt,
        head_pushed_at=head_pushed_at,
        ci_passed=ci_passed,
        copilot_session_terminal=copilot_session_terminal,
        copilot_session_outcome=copilot_session_outcome,
        squash_done=squash_done,
    )
    existing = provider.find_comment(pr_number, SQUASH_WAIT_MARKER_PREFIX)
    if existing is not None:
        provider.update_comment(existing[0], body)
    else:
        provider.post_comment(pr_number, body)


def delete_squash_wait_marker(
    provider: CIPlatformProvider,
    pr_number: int,
) -> None:
    """Finalise the squash-wait marker after squash completes.

    Updates the marker comment to a completion note so that the
    agent-session-monitor no longer re-triggers for this PR.

    Args:
        provider: CI platform provider for API calls.
        pr_number: Pull request number.
    """
    existing = provider.find_comment(pr_number, SQUASH_WAIT_MARKER_PREFIX)
    if existing is None:
        return
    now = datetime.now(timezone.utc).isoformat()
    completed_body = f"<!-- squash-wait-completed -->\nSquash-wait completed for PR #{pr_number} at {now}"
    provider.update_comment(existing[0], completed_body)


def check_edit_relevance(event: EventPayload) -> tuple[bool, str]:
    """Check whether an edited PR event is relevant for pipeline processing.

    This guard implements the edit-relevance preflight: for ``edited`` events
    where the provider reliably reports which fields changed, the pipeline
    should only proceed if the title or base branch was modified.  Body-only
    edits (or edits to other non-title/non-base fields) are irrelevant and
    should be skipped.

    The guard fails open: if the event is not ``edited``, or if the provider
    could not determine what changed (``edit_changes_known=False``), the
    pipeline proceeds normally.

    Args:
        event: Normalized event payload from a CI provider.

    Returns:
        Tuple of ``(should_skip, reason)``.  When ``should_skip`` is True,
        the caller should exit early with an INFO log containing the reason.
        When False, ``reason`` is an empty string and the pipeline continues.
    """
    if event.action != "edited":
        return (False, "")

    if not event.edit_changes_known:
        return (False, "")

    if event.title_changed or event.base_changed:
        return (False, "")

    return (True, "edited event with no title or base change")
