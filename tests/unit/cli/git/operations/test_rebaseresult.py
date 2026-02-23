"""Tests for agentic_devtools.cli.git.operations.RebaseResult."""

from agentic_devtools.cli.git import operations


class TestRebaseResult:
    """Tests for RebaseResult class."""

    def test_success_result(self):
        """Test SUCCESS result properties."""
        result = operations.RebaseResult(operations.RebaseResult.SUCCESS)
        assert result.status == operations.RebaseResult.SUCCESS
        assert result.is_success
        assert result.was_rebased
        assert not result.needs_manual_resolution

    def test_no_rebase_needed_result(self):
        """Test NO_REBASE_NEEDED result properties."""
        result = operations.RebaseResult(operations.RebaseResult.NO_REBASE_NEEDED)
        assert result.status == operations.RebaseResult.NO_REBASE_NEEDED
        assert result.is_success
        assert not result.was_rebased
        assert not result.needs_manual_resolution

    def test_conflict_result(self):
        """Test CONFLICT result properties."""
        result = operations.RebaseResult(operations.RebaseResult.CONFLICT, "conflicts found")
        assert result.status == operations.RebaseResult.CONFLICT
        assert not result.is_success
        assert not result.was_rebased
        assert result.needs_manual_resolution
        assert "conflicts" in result.message

    def test_error_result(self):
        """Test ERROR result properties."""
        result = operations.RebaseResult(operations.RebaseResult.ERROR, "something broke")
        assert result.status == operations.RebaseResult.ERROR
        assert not result.is_success
        assert not result.was_rebased
        assert not result.needs_manual_resolution
