"""Tests for context_mapper.map_run_context()."""

import pytest

from agentic_devtools.cli.ci.reconciliation.context_mapper import map_run_context
from agentic_devtools.cli.ci.reconciliation.exceptions import UnmappableContextError
from agentic_devtools.cli.ci.reconciliation.models import WorkflowRun


def _make_run(event: str, head_branch: str = "main", **kwargs) -> WorkflowRun:
    return WorkflowRun(
        id=kwargs.get("id", 1),
        name="test",
        conclusion="failure",
        run_attempt=1,
        created_at="2024-01-15T10:00:00Z",
        event=event,
        head_branch=head_branch,
        repository_full_name=kwargs.get("repository_full_name", "owner/repo"),
    )


class TestMapRunContextBranchEvents:
    """Tests for branch-targeted events."""

    def test_push_event_maps_to_branch(self) -> None:
        """Push event maps to branch context."""
        run = _make_run(event="push", head_branch="main")
        ctx = map_run_context(run)

        assert ctx.target_type == "branch"
        assert ctx.branch == "main"
        assert ctx.repository_full_name == "owner/repo"

    def test_workflow_dispatch_maps_to_branch(self) -> None:
        """workflow_dispatch maps to branch context."""
        run = _make_run(event="workflow_dispatch", head_branch="develop")
        ctx = map_run_context(run)

        assert ctx.target_type == "branch"
        assert ctx.branch == "develop"

    def test_schedule_maps_to_branch(self) -> None:
        """schedule event maps to branch context."""
        run = _make_run(event="schedule", head_branch="main")
        ctx = map_run_context(run)

        assert ctx.target_type == "branch"
        assert ctx.branch == "main"

    def test_push_without_branch_raises(self) -> None:
        """Push event with empty branch raises UnmappableContextError."""
        run = _make_run(event="push", head_branch="")
        with pytest.raises(UnmappableContextError):
            map_run_context(run)


class TestMapRunContextPREvents:
    """Tests for PR/issue-targeted events."""

    def test_pull_request_with_refs_branch(self) -> None:
        """PR event with refs/pull/N/merge branch resolves to PR."""
        run = _make_run(event="pull_request", head_branch="refs/pull/123/merge")
        ctx = map_run_context(run)

        assert ctx.target_type == "pull_request"
        assert ctx.target_id == 123

    def test_pull_request_with_explicit_pr_number(self) -> None:
        """PR event with explicit pr_number uses it instead of branch parsing."""
        run = WorkflowRun(
            id=1,
            name="test",
            conclusion="failure",
            run_attempt=1,
            created_at="2024-01-15T10:00:00Z",
            event="pull_request",
            head_branch="feature/my-branch",
            repository_full_name="owner/repo",
            pr_number=99,
        )
        ctx = map_run_context(run)

        assert ctx.target_type == "pull_request"
        assert ctx.target_id == 99

    def test_issue_event_with_explicit_pr_number(self) -> None:
        """issue_comment event with pr_number resolves to PR target type."""
        run = WorkflowRun(
            id=2,
            name="test",
            conclusion="failure",
            run_attempt=1,
            created_at="2024-01-15T10:00:00Z",
            event="issue_comment",
            head_branch="some-branch",
            repository_full_name="owner/repo",
            pr_number=42,
        )
        ctx = map_run_context(run)

        assert ctx.target_type == "pull_request"
        assert ctx.target_id == 42

    def test_issue_comment_with_numbered_branch(self) -> None:
        """issue_comment event with numbered branch resolves to issue."""
        run = _make_run(event="issue_comment", head_branch="fix-42")
        ctx = map_run_context(run)

        assert ctx.target_type == "issue"
        assert ctx.target_id == 42

    def test_issue_comment_with_namespaced_marker_branch(self) -> None:
        """issue_comment with pr marker in branch resolves to PR."""
        run = _make_run(event="issue_comment", head_branch="copilot/pr-42")
        ctx = map_run_context(run)

        assert ctx.target_type == "pull_request"
        assert ctx.target_id == 42

    def test_issue_comment_with_refs_pull_branch(self) -> None:
        """issue_comment with refs/pull/N/* branch resolves to PR."""
        run = _make_run(event="issue_comment", head_branch="refs/pull/77/merge")
        ctx = map_run_context(run)

        assert ctx.target_type == "pull_request"
        assert ctx.target_id == 77

    def test_pull_request_target_event(self) -> None:
        """pull_request_target event resolves to PR."""
        run = _make_run(event="pull_request_target", head_branch="refs/pull/99/head")
        ctx = map_run_context(run)

        assert ctx.target_type == "pull_request"
        assert ctx.target_id == 99

    def test_issue_comment_no_number_raises(self) -> None:
        """issue_comment with no extractable number raises."""
        run = _make_run(event="issue_comment", head_branch="feature-branch")
        with pytest.raises(UnmappableContextError):
            map_run_context(run)

    def test_issue_comment_with_unmarked_trailing_digits_raises(self) -> None:
        """Trailing digits without an explicit marker are not mapped."""
        run = _make_run(event="issue_comment", head_branch="feature/foo123")
        with pytest.raises(UnmappableContextError):
            map_run_context(run)


class TestMapRunContextUnsupportedEvents:
    """Tests for unsupported event types."""

    def test_unknown_event_raises(self) -> None:
        """Unknown event type raises UnmappableContextError."""
        run = _make_run(event="deployment")
        with pytest.raises(UnmappableContextError) as exc_info:
            map_run_context(run)
        assert exc_info.value.event == "deployment"

    def test_empty_event_raises(self) -> None:
        """Empty event type raises UnmappableContextError."""
        run = _make_run(event="")
        with pytest.raises(UnmappableContextError):
            map_run_context(run)
