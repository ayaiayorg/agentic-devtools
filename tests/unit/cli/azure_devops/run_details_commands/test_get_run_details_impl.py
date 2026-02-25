"""Tests for get_run_details_impl function."""

from agentic_devtools.cli.azure_devops.run_details_commands import get_run_details_impl


class TestGetRunDetailsImpl:
    """Tests for get_run_details_impl function."""

    def test_function_exists(self):
        """Verify get_run_details_impl is importable and callable."""
        assert callable(get_run_details_impl)
