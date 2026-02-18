"""
Tests for Azure context management functions.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.azure_context.config import AzureContext
from agentic_devtools.cli.azure_context.management import (
    check_login_status,
    ensure_logged_in,
    get_context_env,
    get_current_context,
    run_with_context,
    show_all_contexts,
    switch_context,
)


class TestGetCurrentContext:
    """Tests for get_current_context function."""

    @patch("agentic_devtools.cli.azure_context.management.get_value")
    def test_returns_context_when_set(self, mock_get_value):
        """Test returns AzureContext when set in state."""
        mock_get_value.return_value = "devops"
        result = get_current_context()
        assert result == AzureContext.DEVOPS

    @patch("agentic_devtools.cli.azure_context.management.get_value")
    def test_returns_none_when_not_set(self, mock_get_value):
        """Test returns None when no context in state."""
        mock_get_value.return_value = None
        result = get_current_context()
        assert result is None

    @patch("agentic_devtools.cli.azure_context.management.get_value")
    def test_returns_none_for_invalid_context(self, mock_get_value):
        """Test returns None for invalid context value."""
        mock_get_value.return_value = "invalid"
        result = get_current_context()
        assert result is None


class TestSwitchContext:
    """Tests for switch_context function."""

    @patch("agentic_devtools.cli.azure_context.management.set_value")
    def test_sets_context_in_state(self, mock_set_value):
        """Test that switch_context updates state."""
        switch_context(AzureContext.DEVOPS)
        mock_set_value.assert_called_once_with("azure.context", "devops")

    @patch("agentic_devtools.cli.azure_context.management.set_value")
    def test_switches_to_resources(self, mock_set_value):
        """Test switching to resources context."""
        switch_context(AzureContext.AZURE_RESOURCES)
        mock_set_value.assert_called_once_with("azure.context", "resources")


class TestGetContextEnv:
    """Tests for get_context_env function."""

    def test_returns_azure_config_dir(self):
        """Test that get_context_env returns AZURE_CONFIG_DIR."""
        env = get_context_env(AzureContext.DEVOPS)
        assert "AZURE_CONFIG_DIR" in env
        assert "devops" in env["AZURE_CONFIG_DIR"]

    def test_creates_config_dir(self, tmp_path):
        """Test that config directory is created if it doesn't exist."""
        with patch("agentic_devtools.cli.azure_context.config.Path.home") as mock_home:
            mock_home.return_value = tmp_path
            env = get_context_env(AzureContext.DEVOPS)

            config_dir = Path(env["AZURE_CONFIG_DIR"])
            assert config_dir.exists()
            assert config_dir.is_dir()

    def test_different_contexts_have_different_dirs(self):
        """Test that different contexts have different config directories."""
        devops_env = get_context_env(AzureContext.DEVOPS)
        resources_env = get_context_env(AzureContext.AZURE_RESOURCES)

        assert devops_env["AZURE_CONFIG_DIR"] != resources_env["AZURE_CONFIG_DIR"]


class TestCheckLoginStatus:
    """Tests for check_login_status function."""

    @patch("agentic_devtools.cli.azure_context.management.subprocess.run")
    def test_logged_in_successfully(self, mock_run):
        """Test check_login_status when logged in."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "user": {"name": "user@company.com"}
        })
        mock_run.return_value = mock_result

        is_logged_in, account_name, error = check_login_status(AzureContext.DEVOPS)

        assert is_logged_in is True
        assert account_name == "user@company.com"
        assert error is None

    @patch("agentic_devtools.cli.azure_context.management.subprocess.run")
    def test_not_logged_in(self, mock_run):
        """Test check_login_status when not logged in."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Please run 'az login'"
        mock_run.return_value = mock_result

        is_logged_in, account_name, error = check_login_status(AzureContext.DEVOPS)

        assert is_logged_in is False
        assert account_name is None
        assert "Please run 'az login'" in error

    @patch("agentic_devtools.cli.azure_context.management.subprocess.run")
    def test_subprocess_error(self, mock_run):
        """Test check_login_status handles subprocess errors."""
        mock_run.side_effect = subprocess.SubprocessError("Command failed")

        is_logged_in, account_name, error = check_login_status(AzureContext.DEVOPS)

        assert is_logged_in is False
        assert account_name is None
        assert "Command failed" in error

    @patch("agentic_devtools.cli.azure_context.management.subprocess.run")
    def test_uses_correct_context_env(self, mock_run):
        """Test that check_login_status uses the correct context's config dir."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"user": {"name": "test"}})
        mock_run.return_value = mock_result

        check_login_status(AzureContext.DEVOPS)

        # Verify the environment was passed correctly
        call_env = mock_run.call_args[1]["env"]
        assert "AZURE_CONFIG_DIR" in call_env
        assert "devops" in call_env["AZURE_CONFIG_DIR"]


class TestEnsureLoggedIn:
    """Tests for ensure_logged_in function."""

    @patch("agentic_devtools.cli.azure_context.management.check_login_status")
    @patch("builtins.print")
    def test_already_logged_in(self, mock_print, mock_check):
        """Test ensure_logged_in when already logged in."""
        mock_check.return_value = (True, "user@company.com", None)

        result = ensure_logged_in(AzureContext.DEVOPS)

        assert result is True
        # Should print confirmation
        assert any("logged in" in str(call).lower() for call in mock_print.call_args_list)

    @patch("agentic_devtools.cli.azure_context.management.check_login_status")
    @patch("agentic_devtools.cli.azure_context.management.subprocess.run")
    @patch("builtins.print")
    def test_login_successful(self, mock_print, mock_run, mock_check):
        """Test ensure_logged_in performs login successfully."""
        # First check: not logged in, second check: logged in
        mock_check.side_effect = [
            (False, None, "Not logged in"),
            (True, "user@company.com", None),
        ]
        mock_run.return_value = MagicMock(returncode=0)

        result = ensure_logged_in(AzureContext.DEVOPS)

        assert result is True
        mock_run.assert_called_once()
        # Should have called az login
        assert mock_run.call_args[0][0] == ["az", "login"]

    @patch("agentic_devtools.cli.azure_context.management.check_login_status")
    @patch("agentic_devtools.cli.azure_context.management.subprocess.run")
    @patch("builtins.print")
    def test_login_failed(self, mock_print, mock_run, mock_check):
        """Test ensure_logged_in when login fails."""
        mock_check.return_value = (False, None, "Not logged in")
        mock_run.return_value = MagicMock(returncode=1)

        result = ensure_logged_in(AzureContext.DEVOPS)

        assert result is False


class TestShowAllContexts:
    """Tests for show_all_contexts function."""

    @patch("agentic_devtools.cli.azure_context.management.get_current_context")
    @patch("agentic_devtools.cli.azure_context.management.check_login_status")
    @patch("builtins.print")
    def test_displays_all_contexts(self, mock_print, mock_check, mock_current):
        """Test that show_all_contexts displays all available contexts."""
        mock_current.return_value = AzureContext.DEVOPS
        mock_check.return_value = (True, "user@company.com", None)

        show_all_contexts()

        # Should print info for both contexts
        printed_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "devops" in printed_output.lower()
        assert "resources" in printed_output.lower()

    @patch("agentic_devtools.cli.azure_context.management.get_current_context")
    @patch("agentic_devtools.cli.azure_context.management.check_login_status")
    @patch("builtins.print")
    def test_marks_active_context(self, mock_print, mock_check, mock_current):
        """Test that active context is marked."""
        mock_current.return_value = AzureContext.DEVOPS
        mock_check.return_value = (True, "user@company.com", None)

        show_all_contexts()

        printed_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "ACTIVE" in printed_output


class TestRunWithContext:
    """Tests for run_with_context function."""

    @patch("agentic_devtools.cli.azure_context.management.subprocess.run")
    def test_executes_command_with_context_env(self, mock_run):
        """Test that run_with_context sets correct environment."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        run_with_context(AzureContext.DEVOPS, ["az", "account", "show"])

        # Verify subprocess.run was called with correct args
        mock_run.assert_called_once()
        call_args = mock_run.call_args

        # Check command
        assert call_args[0][0] == ["az", "account", "show"]

        # Check environment contains AZURE_CONFIG_DIR
        call_env = call_args[1]["env"]
        assert "AZURE_CONFIG_DIR" in call_env
        assert "devops" in call_env["AZURE_CONFIG_DIR"]

    @patch("agentic_devtools.cli.azure_context.management.subprocess.run")
    def test_returns_completed_process(self, mock_run):
        """Test that run_with_context returns subprocess result."""
        expected_result = MagicMock(returncode=0, stdout="output", stderr="")
        mock_run.return_value = expected_result

        result = run_with_context(AzureContext.DEVOPS, ["echo", "test"])

        assert result == expected_result
