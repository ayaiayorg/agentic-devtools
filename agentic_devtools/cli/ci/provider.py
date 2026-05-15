"""CI platform provider abstract base class.

Defines the ``CIPlatformProvider`` ABC that all CI-platform-specific
implementations must satisfy. This is separate from ``IssueAdapter`` —
it covers CI-specific operations (event parsing, check status, comment
posting, merge gating) rather than issue CRUD.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agentic_devtools.cli.ci.models import (
    CheckRunStatus,
    EventPayload,
    PRMetadata,
    ReviewInfo,
)


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
    def approve_pr(self, pr_number: int, head_sha: str, body: str) -> None:
        """Approve a pull request.

        Args:
            pr_number: Pull request number.
            head_sha: Expected HEAD SHA (for safety check).
            body: Approval comment body.
        """

    @abstractmethod
    def merge_pr(self, pr_number: int, head_sha: str, method: str) -> None:
        """Merge a pull request.

        Args:
            pr_number: Pull request number.
            head_sha: Expected HEAD SHA (for safety check).
            method: Merge method (e.g., "squash", "merge", "rebase").
        """

    @abstractmethod
    def request_reviewer(self, pr_number: int, reviewer: str) -> None:
        """Request a reviewer for a pull request.

        Args:
            pr_number: Pull request number.
            reviewer: Username of the reviewer to request.
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
        review_comments: list[str],
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
            review_comments: List of Copilot review comment bodies to address.

        Returns:
            The ID of the posted comment.
        """

    @abstractmethod
    def list_review_comments(self, pr_number: int, review_id: int) -> list[str]:
        """List inline comments from a specific review.

        Args:
            pr_number: Pull request number.
            review_id: ID of the review to list comments for.

        Returns:
            List of comment body texts.
        """
