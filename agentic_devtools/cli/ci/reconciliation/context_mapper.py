"""Event context mapper for workflow runs.

Maps a ``WorkflowRun`` to a ``RunEventContext`` by parsing the event type
and extracting the target entity (issue, PR, or branch).
"""

from __future__ import annotations

import logging
import re

from agentic_devtools.cli.ci.reconciliation.exceptions import UnmappableContextError
from agentic_devtools.cli.ci.reconciliation.models import RunEventContext, WorkflowRun

logger = logging.getLogger(__name__)

#: Events that target an issue or PR by number.
_ISSUE_PR_EVENTS = frozenset({"issue_comment", "issues", "pull_request", "pull_request_target"})

#: Events that target a branch.
_BRANCH_EVENTS = frozenset({"push", "workflow_dispatch", "schedule"})

# Only these explicit branch markers are treated as PR/issue references.
_BRANCH_TARGET_MARKERS = ("fix", "issue", "pr")
_BRANCH_TARGET_MARKER_PATTERN = re.compile(
    r"(?:^|/)(?P<marker>" + "|".join(re.escape(marker) for marker in _BRANCH_TARGET_MARKERS) + r")-(?P<number>\d+)$"
)


def map_run_context(run: WorkflowRun) -> RunEventContext:
    """Map a workflow run to its event context for status reporting.

    Determines the target entity (issue/PR/branch) from the run's event type
    and metadata.

    Args:
        run: The workflow run to map.

    Returns:
        RunEventContext with the resolved target.

    Raises:
        UnmappableContextError: When the run cannot be mapped to a target.
    """
    event = run.event

    if event in _BRANCH_EVENTS:
        if not run.head_branch:
            raise UnmappableContextError(run.id, event, "no head_branch available")
        return RunEventContext(
            target_type="branch",
            branch=run.head_branch,
            repository_full_name=run.repository_full_name,
        )

    if event in _ISSUE_PR_EVENTS:
        # Prefer an explicit PR number carried by the run object (populated from
        # the GitHub API ``pull_requests[].number`` field) so that the correct
        # target is resolved even when ``head_branch`` is just the source branch
        # name (e.g. ``feature/foo``) rather than a ``refs/pull/N/…`` ref.
        if run.pr_number:
            target_type = (
                "pull_request" if event in ("pull_request", "pull_request_target", "issue_comment") else "issue"
            )
            return RunEventContext(
                target_type=target_type,
                target_id=run.pr_number,
                repository_full_name=run.repository_full_name,
            )

        # Fall back to branch-name parsing for providers that don't populate
        # pr_number (or older API responses).
        target_number, branch_points_to_pr = _extract_target_from_branch(run.head_branch)
        if target_number:
            target_type = (
                "pull_request"
                if event in ("pull_request", "pull_request_target")
                or (event == "issue_comment" and branch_points_to_pr)
                else "issue"
            )
            return RunEventContext(
                target_type=target_type,
                target_id=target_number,
                repository_full_name=run.repository_full_name,
            )
        raise UnmappableContextError(run.id, event, "could not extract target number from branch")

    raise UnmappableContextError(run.id, event, f"unsupported event type: {event!r}")


def _extract_target_from_branch(branch: str) -> tuple[int, bool]:
    """Extract a target number and PR hint from a branch name if possible.

    Common patterns: ``refs/pull/123/merge``, ``copilot/fix-123``, etc.

    Returns:
        A tuple of (target_number, points_to_pr), or (0, False) if none found.
    """
    # refs/pull/N/merge or refs/pull/N/head
    match = re.search(r"refs/pull/(\d+)/", branch)
    if match:
        return int(match.group(1)), True

    # Try explicit marker + trailing number using marker-N format only,
    # with optional namespace prefixes (e.g., "fix-123", "issue-42",
    # "pr-7", "copilot/fix-123"). Unmarked trailing digits (such as
    # "feature/foo123") are intentionally rejected to avoid false mappings.
    match = _BRANCH_TARGET_MARKER_PATTERN.search(branch)
    if match:
        marker = match.group("marker")
        number = int(match.group("number"))
        return number, marker == "pr"

    return 0, False
