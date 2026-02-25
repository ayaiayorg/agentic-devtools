"""Tests for run_with_context function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_context.config import AzureContext
from agentic_devtools.cli.azure_context.management import run_with_context


class TestRunWithContext:
    """Tests for run_with_context function."""

    def test_runs_command_with_azure_config_dir_env(self):
        """Should run the command with AZURE_CONFIG_DIR set in the environment."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_with_context(AzureContext.DEVOPS, ["az", "account", "show"])

        call_kwargs = mock_run.call_args[1]
        assert "env" in call_kwargs
        assert "AZURE_CONFIG_DIR" in call_kwargs["env"]

    def test_returns_completed_process(self):
        """Should return the CompletedProcess result from subprocess.run."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = run_with_context(AzureContext.DEVOPS, ["az", "account", "show"])

        assert result is mock_result

    def test_env_contains_devops_config_dir(self):
        """AZURE_CONFIG_DIR should reference the devops config directory."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_with_context(AzureContext.DEVOPS, ["az", "version"])

        call_kwargs = mock_run.call_args[1]
        assert "devops" in call_kwargs["env"]["AZURE_CONFIG_DIR"]
