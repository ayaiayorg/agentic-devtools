"""Tests for GitHubActionsProvider.rerun_workflow()."""

import subprocess
from unittest.mock import patch

import pytest

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


def _mock_run_safe_response(returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class TestRerunWorkflow:
    """Tests for GitHubActionsProvider.rerun_workflow()."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_successful_rerun(self, mock_run_safe) -> None:
        """Successful rerun calls the correct endpoint."""
        mock_run_safe.return_value = _mock_run_safe_response(stdout="{}")

        provider = GitHubActionsProvider(repo="owner/repo")
        provider.rerun_workflow(12345)

        mock_run_safe.assert_called_once()
        cmd = mock_run_safe.call_args[0][0]
        assert "/actions/runs/12345/rerun" in cmd[2]
        assert "--method" in cmd
        assert "POST" in cmd

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_api_error_raises_runtime_error(self, mock_run_safe) -> None:
        """API error surfaces as RuntimeError."""
        mock_run_safe.return_value = _mock_run_safe_response(returncode=1, stderr="422 Unprocessable Entity")

        provider = GitHubActionsProvider(repo="owner/repo")
        with pytest.raises(RuntimeError, match="422"):
            provider.rerun_workflow(99999)
