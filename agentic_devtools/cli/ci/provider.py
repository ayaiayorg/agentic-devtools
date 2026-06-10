"""CI platform provider abstract base class.

Defines the ``CIPlatformProvider`` ABC that all CI-platform-specific
implementations must satisfy. This is separate from ``IssueAdapter`` —
it covers CI-specific operations (event parsing, check status, comment
posting, merge gating) rather than issue CRUD.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from agentic_devtools.cli.ci.models import (
    CheckRunStatus,
    EventPayload,
    FinalizationResult,
    IssueCommentInfo,
    IssueEvent,
    PRMetadata,
    ReviewCommentInfo,
    ReviewInfo,
)

if TYPE_CHECKING:
    from agentic_devtools.cli.ci.reconciliation.models import WorkflowRun


class CIPlatformProvider(ABC):
    """Abstract base class for CI platform providers.

    Concrete implementations translate platform-specific APIs into a
    unified interface consumed by the orchestrator and guard modules.
    """

    @abstractmethod
    def parse_event(self, raw_payload: dict, event_name: str) -> EventPayload:
        """Parse a raw CI event payload into a normalized EventPayload.

        Args:
            raw_payload: Raw JSON payload from the CI platform.
            event_name: Event type name (e.g., "pull_request", "issues").

        Returns:
            Normalized EventPayload dataclass.

        Raises:
            MalformedEventError: If the payload cannot be parsed.
        """

    @abstractmethod
    def get_pr_metadata(self, pr_number: int) -> PRMetadata:
        """Retrieve pull request metadata from the CI platform.

        Args:
            pr_number: Pull request number.

        Returns:
            PRMetadata with full PR details.
        """

    @abstractmethod
    def list_check_runs(self, head_sha: str) -> list[CheckRunStatus]:
        """List check runs for a given commit SHA.

        Args:
            head_sha: Commit SHA to query check runs for.

        Returns:
            List of CheckRunStatus for all check runs.
        """

    @abstractmethod
    def list_reviews(self, pr_number: int) -> list[ReviewInfo]:
        """List reviews for a pull request.

        Args:
            pr_number: Pull request number.

        Returns:
            List of ReviewInfo for all reviews.
        """

    @abstractmethod
    def post_comment(self, pr_number: int, body: str) -> int:
        """Post a comment on a pull request.

        Args:
            pr_number: Pull request number.
            body: Comment body text.

        Returns:
            The ID of the created comment.
        """

    @abstractmethod
    def update_comment(self, comment_id: int, body: str) -> None:
        """Update an existing comment.

        Args:
            comment_id: ID of the comment to update.
            body: New comment body text.
        """

    @abstractmethod
    def find_comment(self, pr_number: int, marker: str) -> tuple[int, str] | None:
        """Find a comment containing a specific marker string.

        Args:
            pr_number: Pull request number.
            marker: Marker string to search for in comment bodies.

        Returns:
            Tuple of (comment_id, comment_body) if found, None otherwise.
        """

    @abstractmethod
    def approve_pr(self, pr_number: int, head_sha: str, body: str) -> bool:
        """Approve a pull request.

        Args:
            pr_number: Pull request number.
            head_sha: Expected HEAD SHA (for safety check).
            body: Approval comment body.

        Returns:
            ``True`` when approval was posted, ``False`` when intentionally skipped.
        """

    @abstractmethod
    def merge_pr(self, pr_number: int, head_sha: str, method: str, *, commit_title: str | None = None) -> None:
        """Merge a pull request.

        Args:
            pr_number: Pull request number.
            head_sha: Expected HEAD SHA (for safety check).
            method: Merge method (e.g., "squash", "merge", "rebase").
            commit_title: Optional squash commit title (subject line only).
        """

    @abstractmethod
    def delete_branch(self, branch: str) -> None:
        """Delete a remote branch.

        Args:
            branch: Branch name to delete (e.g., "feature/my-branch").

        Raises:
            RuntimeError: If the branch could not be deleted.
        """

    @abstractmethod
    def publish_pr(self, pr_number: int) -> None:
        """Mark a draft pull request as ready for review.

        Args:
            pr_number: Pull request number.
        """

    @abstractmethod
    def squash_before_publish(
        self,
        *,
        pr_number: int,
        base_branch: str,
        head_branch: str,
        head_sha: str,
    ) -> None:
        """Squash branch commits and force-push before draft publish.

        Implementations should treat single-commit branches as a safe no-op
        for the squash phase while still ensuring the branch is pushed.
        """

    @abstractmethod
    def request_reviewer(self, pr_number: int, reviewer: str) -> None:
        """Request a reviewer for a pull request.

        Args:
            pr_number: Pull request number.
            reviewer: Username of the reviewer to request.
        """

    @abstractmethod
    def count_unresolved_review_threads(self, pr_number: int) -> int:
        """Count unresolved review comment threads on a pull request.

        Args:
            pr_number: Pull request number.

        Returns:
            Number of unresolved review threads.
        """

    @abstractmethod
    def list_pr_files(self, pr_number: int) -> list[str]:
        """List files changed in a pull request.

        Args:
            pr_number: Pull request number.

        Returns:
            List of file paths changed in the PR.
        """

    @abstractmethod
    def get_check_annotations(self, check_run_id: int, limit: int) -> list[str]:
        """Get annotations from a check run.

        Args:
            check_run_id: ID of the check run.
            limit: Maximum number of annotations to return.

        Returns:
            List of annotation messages.
        """

    @abstractmethod
    def dispatch_repair(
        self,
        pr_number: int,
        head_sha: str,
        repair_type: str,
        failed_checks: list[CheckRunStatus],
        review_comments: list[ReviewCommentInfo],
        review_id: int = 0,
    ) -> int:
        """Dispatch a repair by posting a @copilot comment on the PR.

        Posts an authenticated comment tagging ``@copilot`` that begins
        with ``@copilot`` (required for reliable AI agent session triggering).
        The comment body includes failing CI details and/or review feedback
        depending on the repair type.

        Args:
            pr_number: Pull request number.
            head_sha: Current HEAD SHA for the PR.
            repair_type: Type of repair (``"review"``, ``"ci"``, or ``"both"``).
            failed_checks: List of failed check runs with details.
            review_comments: Rich review comment metadata to include in the
                trigger comment.
            review_id: ID of the Copilot review that triggered the repair
                (used for the dedup marker and review URL in the comment body).

        Returns:
            The ID of the posted comment.
        """

    @abstractmethod
    def list_review_comments(self, pr_number: int, review_id: int) -> list[ReviewCommentInfo]:
        """List inline comments from a specific review.

        Args:
            pr_number: Pull request number.
            review_id: ID of the review to list comments for.

        Returns:
            List of rich review comment metadata.
        """

    @abstractmethod
    def list_issue_comments(self, pr_number: int) -> list[IssueCommentInfo]:
        """List issue/PR-level comments on a pull request.

        Args:
            pr_number: Pull request number.

        Returns:
            List of IssueCommentInfo for all PR comments, in API response order.
        """

    @abstractmethod
    def finalize_post_repair(
        self,
        *,
        pr_number: int,
        base_branch: str,
        head_branch: str,
        head_sha: str,
        review_id: int,
    ) -> FinalizationResult:
        """Finalize a Copilot-repaired PR cycle after a synchronize commit.

        Performs provider-specific post-repair actions such as replying to
        review comments and resolving review threads. Squash is handled
        separately via ``squash_post_repair()``.

        Returns:
            FinalizationResult with details about what was resolved/skipped.
        """

    @abstractmethod
    def squash_post_repair(
        self,
        *,
        pr_number: int,
        base_branch: str,
        head_branch: str,
        head_sha: str,
    ) -> None:
        """Squash post-repair commits into a single clean commit.

        Responsible strictly for commit hygiene. Review requests are handled
        explicitly by RequestReviewAction in the pipeline after squash completes.
        """

    @abstractmethod
    def list_pr_issue_events(self, pr_number: int) -> list[IssueEvent]:
        """List issue/PR timeline events for a pull request.

        Fetches Copilot session events (copilot_work_finished,
        copilot_work_finished_failure, copilot_work_started) from the
        GitHub Issues Events API. Returns events in chronological order
        (ascending by id).

        Args:
            pr_number: Pull request number.

        Returns:
            List of IssueEvent dataclasses, filtered to Copilot session events.
            Returns an empty list when the platform does not support this concept
            (e.g., Azure DevOps).
        """

    def get_pr_diff(self, pr_number: int) -> str:
        """Get the unified diff for a pull request.

        Args:
            pr_number: Pull request number.

        Returns:
            Unified diff text as a string.

        Raises:
            NotImplementedError: If the provider does not support this operation.
        """
        raise NotImplementedError(f"{type(self).__name__} does not implement get_pr_diff")

    def get_commit_range_diff(self, base_sha: str, head_sha: str) -> str:
        """Get unified diff text between two commit SHAs.

        Args:
            base_sha: Base commit SHA.
            head_sha: Head commit SHA.

        Returns:
            Unified diff text as a string.

        Raises:
            NotImplementedError: If the provider does not support this operation.
        """
        raise NotImplementedError(f"{type(self).__name__} does not implement get_commit_range_diff")

    def count_commits_behind(self, *, pr_number: int, base_branch: str, head_branch: str) -> int:
        """Return how many commits the head branch is behind the base branch.

        Args:
            pr_number: Pull request number (for logging).
            base_branch: Target branch name.
            head_branch: Source branch name.

        Returns:
            Number of commits the head branch is behind. Returns 0 when the
            provider does not support this operation.
        """
        return 0

    def rebase_onto_base(
        self,
        *,
        pr_number: int,
        base_branch: str,
        head_branch: str,
        head_sha: str,
    ) -> None:
        """Rebase the head branch onto the base branch and force-push.

        Performs: fetch → checkout → rebase → conflict resolution → force-push-with-lease.

        Args:
            pr_number: Pull request number (for logging).
            base_branch: Target branch to rebase onto.
            head_branch: Source branch to rebase.
            head_sha: Current HEAD SHA (for safety).

        Raises:
            RebaseConflictError: When rebase conflicts cannot be auto-resolved.
            ForceWithLeaseError: When force-push-with-lease fails.
            NotImplementedError: When the provider does not support this operation.
        """
        raise NotImplementedError(f"{type(self).__name__} does not implement rebase_onto_base")

    def graphql(self, *, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL query or mutation against the GitHub API.

        Args:
            query: The GraphQL query or mutation string.
            variables: Optional dictionary of query variables.

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            NotImplementedError: If the provider does not support GraphQL.
            RetryableError: On rate limit or transient failures.
            RuntimeError: On non-retryable API errors.
        """
        raise NotImplementedError(f"{type(self).__name__} does not implement graphql")

    def list_workflow_runs(
        self,
        workflow_id: str,
        *,
        window_hours: int = 24,
    ) -> list[WorkflowRun]:
        """List recent completed workflow runs for the specified workflow.

        Implementations should query the CI platform for completed runs within
        the given time window.

        Args:
            workflow_id: Workflow file name or numeric ID.
            window_hours: How far back to look for runs (in hours).

        Returns:
            List of WorkflowRun instances.

        Raises:
            NotImplementedError: If the provider does not support this operation.
        """
        raise NotImplementedError(f"{type(self).__name__} does not implement list_workflow_runs")

    def rerun_workflow(self, run_id: int) -> None:
        """Trigger a re-run of all jobs for the given workflow run.

        Args:
            run_id: The workflow run ID to re-run.

        Raises:
            NotImplementedError: If the provider does not support this operation.
            RuntimeError: If the re-run API call fails.
        """
        raise NotImplementedError(f"{type(self).__name__} does not implement rerun_workflow")
