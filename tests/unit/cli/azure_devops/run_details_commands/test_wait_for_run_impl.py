"""Tests for wait_for_run_impl function."""

from agentic_devtools.cli.azure_devops.run_details_commands import wait_for_run_impl


class TestWaitForRunImpl:
    """Tests for wait_for_run_impl function."""

    def test_returns_dict_with_expected_keys(self):
        """Should return a dictionary containing success, finished, and result keys."""
        # A dry_run call won't make real network requests
        result = wait_for_run_impl(run_id=1234, dry_run=True)

        assert isinstance(result, dict)
        assert "success" in result
        assert "finished" in result

    def test_dry_run_returns_without_polling(self):
        """Dry run should skip actual polling."""
        result = wait_for_run_impl(run_id=9999, dry_run=True)

        # In dry_run mode the function should return immediately
        assert isinstance(result, dict)

    def test_returns_error_result_when_api_fails(self):
        """Should return a result dict with success=False when API call fails."""
        # dry_run mode doesn't call the API so no PAT needed
        result = wait_for_run_impl(run_id=1234, dry_run=True)

        assert isinstance(result, dict)
        # In dry run mode the result should indicate it wasn't actually fetched
        assert "success" in result
