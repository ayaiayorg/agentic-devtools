"""Tests for PreflightResult."""

from agentic_devtools.cli.workflows.preflight import (
    PreflightResult,
)


class TestPreflightResult:
    """Tests for PreflightResult dataclass."""

    def test_passed_when_both_valid(self):
        """Test that passed is True when both checks pass."""
        result = PreflightResult(
            folder_valid=True,
            branch_valid=True,
            folder_name="DFLY-1850",
            branch_name="feature/DFLY-1850/test",
            issue_key="DFLY-1850",
        )
        assert result.passed is True

    def test_passed_when_folder_invalid(self):
        """Test that passed is False when folder check fails."""
        result = PreflightResult(
            folder_valid=False,
            branch_valid=True,
            folder_name="some-folder",
            branch_name="feature/DFLY-1850/test",
            issue_key="DFLY-1850",
        )
        assert result.passed is False

    def test_passed_when_branch_invalid(self):
        """Test that passed is False when branch check fails."""
        result = PreflightResult(
            folder_valid=True,
            branch_valid=False,
            folder_name="DFLY-1850",
            branch_name="main",
            issue_key="DFLY-1850",
        )
        assert result.passed is False

    def test_failure_reasons_both_invalid(self):
        """Test failure reasons when both checks fail."""
        result = PreflightResult(
            folder_valid=False,
            branch_valid=False,
            folder_name="some-folder",
            branch_name="main",
            issue_key="DFLY-1850",
        )
        reasons = result.failure_reasons
        assert len(reasons) == 2
        assert "Folder" in reasons[0]
        assert "Branch" in reasons[1]

    def test_failure_reasons_no_branch(self):
        """Test failure reasons when no branch is checked out."""
        result = PreflightResult(
            folder_valid=False,
            branch_valid=False,
            folder_name="some-folder",
            branch_name="",
            issue_key="DFLY-1850",
        )
        reasons = result.failure_reasons
        assert "Not in a git repository" in reasons[1]
