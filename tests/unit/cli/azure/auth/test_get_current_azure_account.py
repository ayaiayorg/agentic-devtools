"""Tests for get_current_azure_account function."""

import json
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure.auth import get_current_azure_account


class TestGetCurrentAzureAccount:
    """Tests for get_current_azure_account function."""

    def test_returns_none_when_az_fails(self):
        """Should return None when the az command returns a non-zero exit code."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch(
            "agentic_devtools.cli.azure.auth.run_safe",
            return_value=mock_result,
        ):
            result = get_current_azure_account()

        assert result is None

    def test_returns_account_tuple_on_success(self):
        """Should return (account_name, subscription_name) when az succeeds."""
        account_data = {
            "user": {"name": "user.aza@company.com"},
            "name": "My Subscription",
        }
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(account_data)

        with patch(
            "agentic_devtools.cli.azure.auth.run_safe",
            return_value=mock_result,
        ):
            result = get_current_azure_account()

        assert result is not None
        assert result[0] == "user.aza@company.com"
        assert result[1] == "My Subscription"

    def test_returns_none_on_invalid_json(self):
        """Should return None when az output is not valid JSON."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not-json"

        with patch(
            "agentic_devtools.cli.azure.auth.run_safe",
            return_value=mock_result,
        ):
            result = get_current_azure_account()

        assert result is None
