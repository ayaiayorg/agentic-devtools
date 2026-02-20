"""Tests for agentic_devtools.cli.git.operations.check_branch_safe_to_recreate."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git import operations


class TestBranchSafetyCheckResult:
    """Tests for BranchSafetyCheckResult enum values."""

    def test_result_values_exist(self):
        """Test that all expected result values are defined."""
        assert operations.BranchSafetyCheckResult.SAFE == "safe"
        assert operations.BranchSafetyCheckResult.UNCOMMITTED_CHANGES == "uncommitted_changes"
        assert operations.BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN == "diverged_from_origin"
        assert operations.BranchSafetyCheckResult.BRANCH_NOT_ON_ORIGIN == "branch_not_on_origin"
        assert operations.BranchSafetyCheckResult.NOT_ON_BRANCH == "not_on_branch"

    def test_result_is_safe_property(self):
        """Test is_safe property for different result states."""
        safe_result = operations.BranchSafetyCheckResult(operations.BranchSafetyCheckResult.SAFE, "Safe", "test")
        uncommitted_result = operations.BranchSafetyCheckResult(
            operations.BranchSafetyCheckResult.UNCOMMITTED_CHANGES, "Uncommitted", "test"
        )
        assert safe_result.is_safe is True
        assert uncommitted_result.is_safe is False

    def test_has_local_work_at_risk_property(self):
        """Test has_local_work_at_risk property for different result states."""
        uncommitted_result = operations.BranchSafetyCheckResult(
            operations.BranchSafetyCheckResult.UNCOMMITTED_CHANGES, "Uncommitted", "test"
        )
        diverged_result = operations.BranchSafetyCheckResult(
            operations.BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN, "Diverged", "test"
        )
        safe_result = operations.BranchSafetyCheckResult(operations.BranchSafetyCheckResult.SAFE, "Safe", "test")
        assert uncommitted_result.has_local_work_at_risk is True
        assert diverged_result.has_local_work_at_risk is True
        assert safe_result.has_local_work_at_risk is False


class TestCheckBranchSafeToRecreate:
    """Tests for check_branch_safe_to_recreate function."""

    def test_returns_safe_when_branch_does_not_exist_but_on_origin(self, mock_run_safe):
        """Test returns SAFE when branch doesn't exist locally but exists on origin."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.side_effect = [
                MagicMock(returncode=1, stdout="", stderr=""),
                MagicMock(returncode=0, stdout="abc123", stderr=""),
            ]
            result = operations.check_branch_safe_to_recreate("feature/test")
            assert result.status == operations.BranchSafetyCheckResult.SAFE
            assert result.is_safe

    def test_returns_branch_not_on_origin_when_neither_exists(self, mock_run_safe):
        """Test returns BRANCH_NOT_ON_ORIGIN when branch doesn't exist anywhere."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.side_effect = [
                MagicMock(returncode=1, stdout="", stderr=""),
                MagicMock(returncode=1, stdout="", stderr=""),
            ]
            result = operations.check_branch_safe_to_recreate("feature/test")
            assert result.status == operations.BranchSafetyCheckResult.BRANCH_NOT_ON_ORIGIN
            assert not result.is_safe

    def test_returns_uncommitted_changes_when_on_target_branch_dirty(self, mock_run_safe):
        """Test returns UNCOMMITTED_CHANGES when on the target branch with local changes."""
        with patch.object(operations, "run_git") as mock_run_git:
            with patch.object(operations, "get_current_branch", return_value="feature/test"):
                with patch.object(operations, "has_local_changes", return_value=True):
                    mock_run_git.side_effect = [
                        MagicMock(returncode=0, stdout="abc123", stderr=""),
                        MagicMock(returncode=0, stdout="abc123", stderr=""),
                    ]
                    result = operations.check_branch_safe_to_recreate("feature/test")
                    assert result.status == operations.BranchSafetyCheckResult.UNCOMMITTED_CHANGES
                    assert result.has_local_work_at_risk

    def test_returns_safe_when_on_target_branch_clean_matching_origin(self, mock_run_safe):
        """Test returns SAFE when on target branch, clean, and matching origin."""
        with patch.object(operations, "run_git") as mock_run_git:
            with patch.object(operations, "get_current_branch", return_value="feature/test"):
                with patch.object(operations, "has_local_changes", return_value=False):
                    mock_run_git.side_effect = [
                        MagicMock(returncode=0, stdout="abc123", stderr=""),
                        MagicMock(returncode=0, stdout="abc123", stderr=""),
                        MagicMock(returncode=0, stdout="abc123\n", stderr=""),
                        MagicMock(returncode=0, stdout="abc123\n", stderr=""),
                    ]
                    result = operations.check_branch_safe_to_recreate("feature/test")
                    assert result.status == operations.BranchSafetyCheckResult.SAFE
                    assert result.is_safe

    def test_returns_diverged_when_on_target_branch_clean_different_from_origin(self, mock_run_safe):
        """Test returns DIVERGED_FROM_ORIGIN when on target branch but different from origin."""
        with patch.object(operations, "run_git") as mock_run_git:
            with patch.object(operations, "get_current_branch", return_value="feature/test"):
                with patch.object(operations, "has_local_changes", return_value=False):
                    mock_run_git.side_effect = [
                        MagicMock(returncode=0, stdout="abc123", stderr=""),
                        MagicMock(returncode=0, stdout="def456", stderr=""),
                        MagicMock(returncode=0, stdout="abc123\n", stderr=""),
                        MagicMock(returncode=0, stdout="def456\n", stderr=""),
                    ]
                    result = operations.check_branch_safe_to_recreate("feature/test")
                    assert result.status == operations.BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN
                    assert result.has_local_work_at_risk
