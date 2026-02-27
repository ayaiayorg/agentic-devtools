"""Tests for _get_current_user_id function."""

from unittest.mock import patch

from agdt_ai_helpers.cli.azure_devops.pull_request_details_commands import (
    _get_current_user_id,
)


class TestGetCurrentUserId:
    """Tests for _get_current_user_id function."""

    def test_returns_user_id_from_connection_data(self):
        """Should return the authenticated user's ID from connectionData."""
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value={
                "authenticatedUser": {
                    "id": "user-id-abc123",
                    "displayName": "Test User",
                }
            },
        ):
            result = _get_current_user_id("https://dev.azure.com/org", {})

        assert result == "user-id-abc123"

    def test_returns_none_when_api_fails(self):
        """Should return None when the connectionData API call fails."""
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value=None,
        ):
            result = _get_current_user_id("https://dev.azure.com/org", {})

        assert result is None

    def test_returns_none_when_no_authenticated_user(self):
        """Should return None when authenticatedUser is missing."""
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value={"someOtherKey": {}},
        ):
            result = _get_current_user_id("https://dev.azure.com/org", {})

        assert result is None

    def test_returns_none_when_id_missing_from_authenticated_user(self):
        """Should return None when id field is missing from authenticatedUser."""
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value={"authenticatedUser": {"displayName": "Test User"}},
        ):
            result = _get_current_user_id("https://dev.azure.com/org", {})

        assert result is None

    def test_calls_correct_endpoint(self):
        """Should call the connectionData endpoint."""
        with patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._invoke_ado_rest",
            return_value=None,
        ) as mock_rest:
            _get_current_user_id("https://dev.azure.com/myorg", {"Authorization": "Basic abc"})

        mock_rest.assert_called_once_with(
            "https://dev.azure.com/myorg/_apis/connectionData",
            {"Authorization": "Basic abc"},
        )
