"""Tests for agentic_devtools.cli.git.operations.BranchSafetyCheckResult."""

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
