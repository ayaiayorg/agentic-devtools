"""Tests for RunEventContext dataclass."""

from agentic_devtools.cli.ci.reconciliation.models import RunEventContext


class TestRunEventContext:
    """Tests for RunEventContext dataclass."""

    def test_branch_context(self) -> None:
        """RunEventContext for a branch target."""
        ctx = RunEventContext(
            target_type="branch",
            branch="main",
            repository_full_name="owner/repo",
        )
        assert ctx.target_type == "branch"
        assert ctx.target_id == 0
        assert ctx.branch == "main"
        assert ctx.repository_full_name == "owner/repo"

    def test_pr_context(self) -> None:
        """RunEventContext for a pull_request target."""
        ctx = RunEventContext(
            target_type="pull_request",
            target_id=42,
            repository_full_name="owner/repo",
        )
        assert ctx.target_type == "pull_request"
        assert ctx.target_id == 42
        assert ctx.branch == ""

    def test_issue_context(self) -> None:
        """RunEventContext for an issue target."""
        ctx = RunEventContext(
            target_type="issue",
            target_id=99,
        )
        assert ctx.target_type == "issue"
        assert ctx.target_id == 99

    def test_defaults(self) -> None:
        """RunEventContext defaults."""
        ctx = RunEventContext(target_type="branch")
        assert ctx.target_id == 0
        assert ctx.branch == ""
        assert ctx.repository_full_name == ""
