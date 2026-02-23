"""Tests for PlaceholderIssueResult."""

from agentic_devtools.cli.workflows.worktree_setup import (
    PlaceholderIssueResult,
)


class TestPlaceholderIssueResult:
    """Tests for PlaceholderIssueResult dataclass."""

    def test_default_values(self):
        """Test default values for PlaceholderIssueResult."""
        result = PlaceholderIssueResult(success=False)
        assert result.success is False
        assert result.issue_key is None
        assert result.error_message is None

    def test_success_state(self):
        """Test success state with issue key."""
        result = PlaceholderIssueResult(
            success=True,
            issue_key="DFLY-1234",
        )
        assert result.success is True
        assert result.issue_key == "DFLY-1234"
        assert result.error_message is None

    def test_error_state(self):
        """Test error state with message."""
        result = PlaceholderIssueResult(
            success=False,
            error_message="API returned 401",
        )
        assert result.success is False
        assert result.issue_key is None
        assert result.error_message == "API returned 401"
