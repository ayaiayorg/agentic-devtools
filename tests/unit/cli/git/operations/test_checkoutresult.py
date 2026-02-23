"""Tests for agentic_devtools.cli.git.operations.CheckoutResult."""

from agentic_devtools.cli.git import operations


class TestCheckoutResult:
    """Tests for CheckoutResult class."""

    def test_success_result(self):
        """Test SUCCESS result properties."""
        result = operations.CheckoutResult(operations.CheckoutResult.SUCCESS)
        assert result.status == operations.CheckoutResult.SUCCESS
        assert result.is_success
        assert not result.needs_user_action
        assert result.message == ""

    def test_uncommitted_changes_result(self):
        """Test UNCOMMITTED_CHANGES result properties."""
        result = operations.CheckoutResult(operations.CheckoutResult.UNCOMMITTED_CHANGES, "uncommitted changes message")
        assert result.status == operations.CheckoutResult.UNCOMMITTED_CHANGES
        assert not result.is_success
        assert result.needs_user_action
        assert "uncommitted" in result.message.lower()

    def test_branch_not_found_result(self):
        """Test BRANCH_NOT_FOUND result properties."""
        result = operations.CheckoutResult(operations.CheckoutResult.BRANCH_NOT_FOUND, "Branch feature/test not found")
        assert result.status == operations.CheckoutResult.BRANCH_NOT_FOUND
        assert not result.is_success
        assert result.needs_user_action
        assert "feature/test" in result.message

    def test_error_result(self):
        """Test ERROR result properties."""
        result = operations.CheckoutResult(operations.CheckoutResult.ERROR, "Something went wrong")
        assert result.status == operations.CheckoutResult.ERROR
        assert not result.is_success
        assert not result.needs_user_action
        assert "Something went wrong" in result.message
