"""Tests for _rerun_single_workflow."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.github.rerun_checks import _rerun_single_workflow

_MOD = "agentic_devtools.cli.github.rerun_checks"


class TestRerunSingleWorkflow:
    """Tests for _rerun_single_workflow."""

    @patch(f"{_MOD}.run_safe")
    def test_success_returns_triggered(self, mock_run):
        """Returns (True, 'triggered') on exit code 0."""
        mock_run.return_value = MagicMock(returncode=0)

        success, message = _rerun_single_workflow("owner/repo", 12345)

        assert success is True
        assert message == "triggered"
        args = mock_run.call_args[0][0]
        assert "repos/owner/repo/actions/runs/12345/rerun" in args[4]

    @patch(f"{_MOD}.run_safe")
    def test_failure_returns_stderr(self, mock_run):
        """Returns (False, stderr) on non-zero exit code."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="403 Forbidden: SAML enforcement",
        )

        success, message = _rerun_single_workflow("owner/repo", 99)

        assert success is False
        assert "403 Forbidden" in message

    @patch(f"{_MOD}.run_safe")
    def test_failure_empty_stderr(self, mock_run):
        """Returns 'Unknown error' when stderr is empty."""
        mock_run.return_value = MagicMock(returncode=1, stderr="")

        success, message = _rerun_single_workflow("owner/repo", 99)

        assert success is False
        assert message == "Unknown error"

    @patch(f"{_MOD}.run_safe", side_effect=FileNotFoundError)
    def test_gh_not_installed_returns_error(self, mock_run):
        """Returns (False, error) when gh CLI is not found."""
        success, message = _rerun_single_workflow("owner/repo", 42)

        assert success is False
        assert "gh" in message
        assert "not found" in message.lower() or "was not found" in message.lower()

    @patch(f"{_MOD}.run_safe", side_effect=PermissionError("Permission denied"))
    def test_os_error_returns_error(self, mock_run):
        """Returns (False, error) when an OSError occurs."""
        success, message = _rerun_single_workflow("owner/repo", 42)

        assert success is False
        assert "Failed to execute" in message
        assert "Permission denied" in message
