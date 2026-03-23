"""Abstract issue adapter interface and shared result types.

Defines the ``IssueAdapter`` ABC that all platform-specific adapters must
implement, plus the shared ``TypedDict`` result types used across adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from typing_extensions import TypedDict

# ---------------------------------------------------------------------------
# Shared result TypedDicts
# ---------------------------------------------------------------------------


class Comment(TypedDict):
    """A single comment on an issue."""

    comment_id: str
    body: str
    created_at: str


class IssueResult(TypedDict):
    """Result of creating an issue."""

    issue_id: str
    url: str


class IssueDetail(TypedDict):
    """Full detail of a single issue."""

    issue_id: str
    title: str
    description: str
    status: str
    labels: list[str]
    url: str
    comments: list[Comment]


class CommentResult(TypedDict):
    """Result of adding a comment."""

    comment_id: str


class IssueSummary(TypedDict):
    """Summary of an issue for list results."""

    issue_id: str
    title: str
    status: str
    labels: list[str]
    url: str


class IssueFilters(TypedDict, total=False):
    """Optional filters for listing issues."""

    labels: list[str]
    state: str
    assignee: str


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------


class IssueAdapter(ABC):
    """Abstract base class for issue-tracking platform adapters.

    Concrete subclasses must implement all four abstract methods.
    """

    @abstractmethod
    def create_issue(self, title: str, description: str, labels: list[str] | None = None) -> IssueResult:
        """Create a new issue.

        Args:
            title: Issue title / summary.
            description: Issue description body.
            labels: Optional list of labels to apply.

        Returns:
            An :class:`IssueResult` with the new issue ID and URL.
        """

    @abstractmethod
    def get_issue(self, issue_id: str) -> IssueDetail:
        """Retrieve full details of an issue.

        Args:
            issue_id: Platform-specific issue identifier.

        Returns:
            An :class:`IssueDetail` with the issue's metadata and comments.
        """

    @abstractmethod
    def add_comment(self, issue_id: str, comment: str) -> CommentResult:
        """Add a comment to an existing issue.

        Args:
            issue_id: Platform-specific issue identifier.
            comment: Comment body text.

        Returns:
            A :class:`CommentResult` with the new comment ID.
        """

    @abstractmethod
    def list_issues(self, filters: IssueFilters | None = None) -> list[IssueSummary]:
        """List issues, optionally filtered.

        Args:
            filters: Optional :class:`IssueFilters` to narrow results.

        Returns:
            A list of :class:`IssueSummary` items.
        """
