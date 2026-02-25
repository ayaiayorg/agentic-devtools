"""Tests for switch_azure_account function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure.auth import switch_azure_account
from agentic_devtools.cli.azure.config import AzureAccount


class TestSwitchAzureAccount:
    """Tests for switch_azure_account function."""

    def test_returns_false_when_az_login_fails(self):
        """Should return False when az login returns non-zero exit code."""
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch(
            "agentic_devtools.cli.azure.auth.run_safe",
            return_value=mock_result,
        ):
            result = switch_azure_account(AzureAccount.AZA)

        assert result is False

    def test_returns_false_when_account_type_mismatch(self):
        """Should return False when logged-in account type does not match target."""
        login_result = MagicMock()
        login_result.returncode = 0

        # get_current_azure_account returns a NORMAL account after AZA login
        with patch(
            "agentic_devtools.cli.azure.auth.run_safe",
            return_value=login_result,
        ):
            with patch(
                "agentic_devtools.cli.azure.auth.get_current_azure_account",
                return_value=("normal.user@company.com", "My Sub"),
            ):
                result = switch_azure_account(AzureAccount.AZA)

        assert result is False

    def test_returns_true_when_correct_account_logged_in(self):
        """Should return True when the correct account type is active after login."""
        login_result = MagicMock()
        login_result.returncode = 0

        with patch(
            "agentic_devtools.cli.azure.auth.run_safe",
            return_value=login_result,
        ):
            with patch(
                "agentic_devtools.cli.azure.auth.get_current_azure_account",
                return_value=("user.aza@company.com", "My Sub"),
            ):
                result = switch_azure_account(AzureAccount.AZA)

        assert result is True
