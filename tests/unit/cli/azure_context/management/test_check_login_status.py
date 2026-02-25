"""Tests for check_login_status function."""

import json
import subprocess
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_context.config import AzureContext
from agentic_devtools.cli.azure_context.management import check_login_status


class TestCheckLoginStatus:
    """Tests for check_login_status function."""

    def test_returns_logged_in_true_on_success(self, tmp_path):
        """Should return (True, account_name, None) when az account show succeeds."""
        account_data = {"user": {"name": "user@company.com"}}
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(account_data)

        with patch("agentic_devtools.cli.azure_context.config.Path.home", return_value=tmp_path):
            with patch("subprocess.run", return_value=mock_result):
                is_logged_in, account_name, error = check_login_status(AzureContext.DEVOPS)

        assert is_logged_in is True
        assert account_name == "user@company.com"
        assert error is None

    def test_returns_logged_in_false_on_failure(self, tmp_path):
        """Should return (False, None, error_msg) when az account show fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Not logged in"

        with patch("agentic_devtools.cli.azure_context.config.Path.home", return_value=tmp_path):
            with patch("subprocess.run", return_value=mock_result):
                is_logged_in, account_name, error = check_login_status(AzureContext.DEVOPS)

        assert is_logged_in is False
        assert account_name is None
        assert error is not None

    def test_returns_false_on_subprocess_error(self, tmp_path):
        """Should return (False, None, error) when subprocess raises an exception."""
        with patch("agentic_devtools.cli.azure_context.config.Path.home", return_value=tmp_path):
            with patch("subprocess.run", side_effect=subprocess.SubprocessError("err")):
                is_logged_in, account_name, error = check_login_status(AzureContext.DEVOPS)

        assert is_logged_in is False
        assert account_name is None
