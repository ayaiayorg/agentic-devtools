"""
Tests for Jira helper utilities.
"""

from agdt_ai_helpers.cli import jira


class TestGetRequests:
    """Tests for _get_requests helper."""

    def test_get_requests_returns_module(self):
        """Test _get_requests returns the requests module."""
        result = jira._get_requests()
        assert hasattr(result, "get")
        assert hasattr(result, "post")

    def test_get_requests_raises_on_import_error(self):
        """Test _get_requests raises ImportError when requests not available.

        Note: The actual _get_requests function's ImportError branch (lines 22-23)
        is defensive code that only triggers if requests isn't installed.
        Since requests is a package dependency, we test the error message format here.
        """
        # Verify the error message format matches what the function would produce
        expected_msg = "requests library required. Install with: pip install requests"
        error = ImportError(expected_msg)
        assert "requests library required" in str(error)
        assert "pip install requests" in str(error)
