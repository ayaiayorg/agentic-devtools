"""Tests for ensure_azure_account function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure.auth import ensure_azure_account
from agentic_devtools.cli.azure.config import AzureAccount


class TestEnsureAzureAccount:
    """Tests for ensure_azure_account function."""

    def test_returns_true_when_correct_account_already_active(self):
        """Should return True immediately when the correct account is already active."""
        with patch(
            "agentic_devtools.cli.azure.auth.get_current_azure_account",
            return_value=("user.aza@company.com", "My Sub"),
        ):
            result = ensure_azure_account(AzureAccount.AZA, auto_switch=False)

        assert result is True

    def test_returns_false_when_not_logged_in_and_no_auto_switch(self):
        """Should return False when not logged in and auto_switch is disabled."""
        with patch(
            "agentic_devtools.cli.azure.auth.get_current_azure_account",
            return_value=None,
        ):
            result = ensure_azure_account(AzureAccount.AZA, auto_switch=False)

        assert result is False

    def test_returns_false_when_wrong_account_and_no_auto_switch(self):
        """Should return False when a wrong account type is active and auto_switch=False."""
        with patch(
            "agentic_devtools.cli.azure.auth.get_current_azure_account",
            return_value=("normal.user@company.com", "My Sub"),
        ):
            result = ensure_azure_account(AzureAccount.AZA, auto_switch=False)

        assert result is False
