"""Tests for WorktreeSetupResult."""

from agentic_devtools.cli.workflows.worktree_setup import (
    WorktreeSetupResult,
)


class TestWorktreeSetupResult:
    """Tests for WorktreeSetupResult dataclass."""

    def test_required_fields(self):
        """Test required fields for WorktreeSetupResult."""
        result = WorktreeSetupResult(
            success=True,
            worktree_path="/path/to/worktree",
            branch_name="feature/DFLY-1234/test",
        )
        assert result.success is True
        assert result.worktree_path == "/path/to/worktree"
        assert result.branch_name == "feature/DFLY-1234/test"
        # Default values for optional fields
        assert result.error_message is None
        assert result.vscode_opened is False

    def test_custom_values(self):
        """Test custom values for WorktreeSetupResult."""
        result = WorktreeSetupResult(
            success=True,
            worktree_path="/path/to/worktree",
            branch_name="feature/DFLY-1234/test",
            vscode_opened=True,
            error_message=None,
        )
        assert result.success is True
        assert result.worktree_path == "/path/to/worktree"
        assert result.branch_name == "feature/DFLY-1234/test"
        assert result.vscode_opened is True
        assert result.error_message is None

    def test_error_state(self):
        """Test error state with message."""
        result = WorktreeSetupResult(
            success=False,
            worktree_path="",
            branch_name="",
            error_message="Failed to create worktree",
        )
        assert result.success is False
        assert result.error_message == "Failed to create worktree"
