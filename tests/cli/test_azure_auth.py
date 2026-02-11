"""Tests for azure/auth.py module."""

import json
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure.auth import (
    detect_account_type,
    ensure_azure_account,
    get_current_azure_account,
    is_aza_account,
    switch_azure_account,
    verify_azure_cli,
)
from agentic_devtools.cli.azure.config import AzureAccount


class TestGetCurrentAzureAccount:
    """Tests for get_current_azure_account function."""

    @patch("agentic_devtools.cli.azure.auth.run_safe")
    def test_returns_tuple(self, mock_run):
        """Test parsing account name from az account show returns (user_name, subscription_name)."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                {"user": {"name": "user@domain.com"}, "name": "my-subscription"}
            ),
        )
        result = get_current_azure_account()
        assert result == ("user@domain.com", "my-subscription")

    @patch("agentic_devtools.cli.azure.auth.run_safe")
    def test_returns_none_on_failure(self, mock_run):
        """Test returns None when az account show fails."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = get_current_azure_account()
        assert result is None

    @patch("agentic_devtools.cli.azure.auth.run_safe")
    def test_returns_none_on_invalid_json(self, mock_run):
        """Test returns None on invalid JSON output."""
        mock_run.return_value = MagicMock(returncode=0, stdout="not json")
        result = get_current_azure_account()
        assert result is None


class TestIsAzaAccount:
    """Tests for is_aza_account function."""

    def test_aza_in_username_detected(self):
        """Test that .aza in username before @ is detected."""
        assert is_aza_account("user.aza@domain.com") is True

    def test_aza_at_boundary(self):
        """Test that aza at end of local part is detected."""
        assert is_aza_account("firstname.lastname.aza@company.com") is True

    def test_non_aza_account(self):
        """Test that normal accounts are not AZA."""
        assert is_aza_account("user@domain.com") is False

    def test_none_input(self):
        """Test that None input returns False."""
        assert is_aza_account(None) is False

    def test_empty_string(self):
        """Test that empty string returns False."""
        assert is_aza_account("") is False


class TestDetectAccountType:
    """Tests for detect_account_type function."""

    def test_detects_aza(self):
        """Test AZA account detection."""
        assert detect_account_type("user.aza@domain.com") == AzureAccount.AZA

    def test_detects_normal(self):
        """Test normal account detection."""
        assert detect_account_type("user@domain.com") == AzureAccount.NORMAL

    def test_empty_returns_normal(self):
        """Test returns NORMAL when empty string (is_aza_account returns False)."""
        assert detect_account_type("") == AzureAccount.NORMAL


class TestSwitchAzureAccount:
    """Tests for switch_azure_account function."""

    @patch("agentic_devtools.cli.azure.auth.get_current_azure_account")
    @patch("agentic_devtools.cli.azure.auth.run_safe")
    def test_switch_to_aza(self, mock_run, mock_get_account):
        """Test switching to AZA account."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_get_account.return_value = ("user.aza@domain.com", "sub")
        result = switch_azure_account(AzureAccount.AZA)
        assert result is True

    @patch("agentic_devtools.cli.azure.auth.run_safe")
    def test_switch_failure(self, mock_run):
        """Test switch returns False on failure."""
        mock_run.return_value = MagicMock(returncode=1)
        result = switch_azure_account(AzureAccount.AZA)
        assert result is False

    @patch("agentic_devtools.cli.azure.auth.get_current_azure_account")
    @patch("agentic_devtools.cli.azure.auth.run_safe")
    def test_switch_wrong_type_after_login(self, mock_run, mock_get_account):
        """Test switch returns False when login succeeds but wrong account type."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_get_account.return_value = ("normal.user@domain.com", "sub")
        result = switch_azure_account(AzureAccount.AZA)
        assert result is False


class TestEnsureAzureAccount:
    """Tests for ensure_azure_account function."""

    @patch("agentic_devtools.cli.azure.auth.get_current_azure_account")
    def test_already_correct_account(self, mock_get_account):
        """Test no switch when account is already correct."""
        mock_get_account.return_value = ("user.aza@domain.com", "sub")
        result = ensure_azure_account(AzureAccount.AZA)
        assert result is True

    @patch("agentic_devtools.cli.azure.auth.switch_azure_account")
    @patch("agentic_devtools.cli.azure.auth.get_current_azure_account")
    def test_switches_when_wrong_account(self, mock_get_account, mock_switch):
        """Test switches when wrong account type is active."""
        mock_get_account.return_value = ("user@domain.com", "sub")
        mock_switch.return_value = True
        result = ensure_azure_account(AzureAccount.AZA, auto_switch=True)
        assert result is True
        mock_switch.assert_called_once_with(AzureAccount.AZA)

    @patch("agentic_devtools.cli.azure.auth.get_current_azure_account")
    def test_fails_when_no_auto_switch(self, mock_get_account):
        """Test fails when wrong account and no auto-switch."""
        mock_get_account.return_value = ("user@domain.com", "sub")
        result = ensure_azure_account(AzureAccount.AZA, auto_switch=False)
        assert result is False

    @patch("agentic_devtools.cli.azure.auth.switch_azure_account")
    @patch("agentic_devtools.cli.azure.auth.get_current_azure_account")
    def test_not_logged_in_with_auto_switch(self, mock_get_account, mock_switch):
        """Test that not being logged in with auto_switch triggers switch_azure_account."""
        mock_get_account.return_value = None
        mock_switch.return_value = True
        result = ensure_azure_account(AzureAccount.AZA, auto_switch=True)
        assert result is True
        mock_switch.assert_called_once_with(AzureAccount.AZA)

    @patch("agentic_devtools.cli.azure.auth.get_current_azure_account")
    def test_not_logged_in_without_auto_switch(self, mock_get_account):
        """Test that not being logged in without auto_switch returns False."""
        mock_get_account.return_value = None
        result = ensure_azure_account(AzureAccount.AZA, auto_switch=False)
        assert result is False


class TestVerifyAzureCli:
    """Tests for verify_azure_cli function."""

    @patch("agentic_devtools.cli.azure.auth.run_safe")
    def test_cli_available(self, mock_run):
        """Test returns True when az CLI is available."""
        mock_run.return_value = MagicMock(returncode=0, stdout="2.60.0")
        assert verify_azure_cli() is True

    @patch("agentic_devtools.cli.azure.auth.run_safe")
    def test_cli_not_available(self, mock_run):
        """Test returns False when az CLI is not available."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert verify_azure_cli() is False
