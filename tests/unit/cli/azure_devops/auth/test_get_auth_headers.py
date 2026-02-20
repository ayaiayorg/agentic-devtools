"""Tests for get_auth_headers function."""

from agentic_devtools.cli import azure_devops


class TestGetAuthHeaders:
    """Tests for get_auth_headers function."""

    def test_get_auth_headers(self):
        """Test auth headers contain required fields."""
        headers = azure_devops.get_auth_headers("test-pat")
        assert "Authorization" in headers
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"

    def test_get_auth_headers_base64_encoding(self):
        """Test auth header uses base64 encoded PAT."""
        headers = azure_devops.get_auth_headers("test-pat")
        # Base64 of ":test-pat" is "OnRlc3QtcGF0"
        assert "OnRlc3QtcGF0" in headers["Authorization"]
        assert headers["Authorization"].startswith("Basic ")
