"""Tests for agentic_devtools.adapters.base.IssueAdapter."""

from __future__ import annotations

import pytest

from agentic_devtools.adapters.base import (
    CommentResult,
    IssueAdapter,
    IssueDetail,
    IssueFilters,
    IssueResult,
    IssueSummary,
)


class TestIssueAdapter:
    """Tests for the IssueAdapter abstract base class."""

    def test_cannot_instantiate_directly(self) -> None:
        """IssueAdapter is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            IssueAdapter()  # type: ignore[abstract]

    def test_incomplete_subclass_raises_type_error(self) -> None:
        """A subclass missing an abstract method cannot be instantiated."""

        class Incomplete(IssueAdapter):
            def create_issue(self, title: str, description: str, labels: list[str] | None = None) -> IssueResult:
                return IssueResult(issue_id="1", url="")

            # Missing get_issue, add_comment, list_issues

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_complete_subclass_can_be_instantiated(self) -> None:
        """A subclass implementing all abstract methods can be instantiated."""

        class Complete(IssueAdapter):
            def create_issue(self, title: str, description: str, labels: list[str] | None = None) -> IssueResult:
                return IssueResult(issue_id="1", url="")

            def get_issue(self, issue_id: str) -> IssueDetail:
                return IssueDetail(
                    issue_id=issue_id, title="", description="", status="", labels=[], url="", comments=[]
                )

            def add_comment(self, issue_id: str, comment: str) -> CommentResult:
                return CommentResult(comment_id="c1")

            def list_issues(self, filters: IssueFilters | None = None) -> list[IssueSummary]:
                return []

        adapter = Complete()
        assert isinstance(adapter, IssueAdapter)
