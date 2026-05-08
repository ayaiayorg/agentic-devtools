"""Tests for resolve_pat_identity function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.finalization.identity import resolve_pat_identity


class TestResolvePatIdentity:
    """Tests for resolve_pat_identity."""

    def test_returns_user_id_on_success(self):
        """Should return the authenticated user's ID GUID."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"authenticatedUser": {"id": "user-guid-123"}}
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            result = resolve_pat_identity("https://dev.azure.com/org", {"Authorization": "Basic x"})

        assert result == "user-guid-123"

    def test_returns_none_on_network_failure(self):
        """Should return None when the API call fails."""
        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("connection error")

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            result = resolve_pat_identity("https://dev.azure.com/org", {})

        assert result is None

    def test_returns_none_when_no_user_id(self):
        """Should return None when authenticatedUser has no id field."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"authenticatedUser": {"displayName": "Test User"}}
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            result = resolve_pat_identity("https://dev.azure.com/org", {})

        assert result is None

    def test_returns_none_when_empty_response(self):
        """Should return None when response has no authenticatedUser."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            result = resolve_pat_identity("https://dev.azure.com/org", {})

        assert result is None
