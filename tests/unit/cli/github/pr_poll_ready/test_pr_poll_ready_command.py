"""Tests for agentic_devtools.cli.github.pr_poll_ready.pr_poll_ready_command."""

import json
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.github.pr_poll_ready import pr_poll_ready_command

_MODULE = "agentic_devtools.cli.github.pr_poll_ready"


class TestPrPollReadyCommandArgs:
    """Tests for CLI argument parsing."""

    @patch(f"{_MODULE}.poll_pr_ready")
    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_pr_from_cli(self, mock_resolve, mock_poll, capsys):
        """Uses --pr CLI argument."""
        mock_poll.return_value = {"ready": True, "reason": "copilot_clean_and_ci_green"}
        with patch("sys.argv", ["agdt-gh-pr-poll-ready", "--pr", "42"]):
            pr_poll_ready_command()
        mock_poll.assert_called_once()
        assert mock_poll.call_args.kwargs["pr_number"] == 42

    @patch(f"{_MODULE}.poll_pr_ready")
    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{_MODULE}.get_value", return_value=99)
    def test_pr_from_state(self, mock_get, mock_resolve, mock_poll, capsys):
        """Falls back to github.pull_request_number from state."""
        mock_poll.return_value = {"ready": True, "reason": "test"}
        with patch("sys.argv", ["agdt-gh-pr-poll-ready"]):
            pr_poll_ready_command()
        mock_poll.assert_called_once()
        assert mock_poll.call_args.kwargs["pr_number"] == 99

    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{_MODULE}.get_value", return_value=None)
    def test_exits_when_no_pr(self, mock_get, mock_resolve):
        """Exits with code 1 when no PR number is available."""
        with patch("sys.argv", ["agdt-gh-pr-poll-ready"]):
            with pytest.raises(SystemExit) as exc_info:
                pr_poll_ready_command()
        assert exc_info.value.code == 1

    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    @patch(f"{_MODULE}.get_value", return_value="not-a-number")
    def test_exits_when_pr_state_is_invalid(self, mock_get, mock_resolve):
        """Exits with code 1 when state PR value is not a valid int."""
        with patch("sys.argv", ["agdt-gh-pr-poll-ready"]):
            with pytest.raises(SystemExit) as exc_info:
                pr_poll_ready_command()
        assert exc_info.value.code == 1

    @patch(f"{_MODULE}.poll_pr_ready")
    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_repo_from_cli(self, mock_resolve, mock_poll, capsys):
        """Uses --repo CLI argument."""
        mock_poll.return_value = {"ready": True, "reason": "test"}
        with patch("sys.argv", ["agdt-gh-pr-poll-ready", "--pr", "1", "--repo", "a/b"]):
            pr_poll_ready_command()
        mock_resolve.assert_called_once_with("a/b")


class TestPrPollReadyCommandValidation:
    """Tests for parameter validation."""

    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_rejects_poll_interval_too_low(self, mock_resolve):
        """Rejects poll-interval below minimum."""
        with patch("sys.argv", ["agdt-gh-pr-poll-ready", "--pr", "1", "--poll-interval", "5"]):
            with pytest.raises(SystemExit) as exc_info:
                pr_poll_ready_command()
        assert exc_info.value.code == 1

    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_rejects_poll_interval_too_high(self, mock_resolve):
        """Rejects poll-interval above maximum."""
        with patch("sys.argv", ["agdt-gh-pr-poll-ready", "--pr", "1", "--poll-interval", "500"]):
            with pytest.raises(SystemExit) as exc_info:
                pr_poll_ready_command()
        assert exc_info.value.code == 1

    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_rejects_max_wait_too_low(self, mock_resolve):
        """Rejects max-wait below minimum."""
        with patch("sys.argv", ["agdt-gh-pr-poll-ready", "--pr", "1", "--max-wait", "10"]):
            with pytest.raises(SystemExit) as exc_info:
                pr_poll_ready_command()
        assert exc_info.value.code == 1

    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_rejects_max_wait_too_high(self, mock_resolve):
        """Rejects max-wait above maximum."""
        with patch("sys.argv", ["agdt-gh-pr-poll-ready", "--pr", "1", "--max-wait", "5000"]):
            with pytest.raises(SystemExit) as exc_info:
                pr_poll_ready_command()
        assert exc_info.value.code == 1


class TestPrPollReadyCommandOutput:
    """Tests for output formatting."""

    @patch(f"{_MODULE}.poll_pr_ready")
    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_prints_json_to_stdout(self, mock_resolve, mock_poll, capsys):
        """Prints structured JSON to stdout."""
        mock_poll.return_value = {"ready": True, "reason": "copilot_clean_and_ci_green"}
        with patch("sys.argv", ["agdt-gh-pr-poll-ready", "--pr", "1"]):
            pr_poll_ready_command()
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["ready"] is True


class TestPrPollReadyCommandBackground:
    """Tests for background task mode."""

    @patch("agentic_devtools.task_state.print_task_tracking_info")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_dispatches_to_background(self, mock_resolve, mock_bg, mock_track):
        """Dispatches to background when --background is set."""
        mock_bg.return_value = MagicMock()
        with patch("sys.argv", ["agdt-gh-pr-poll-ready", "--pr", "1", "--background"]):
            pr_poll_ready_command()
        mock_bg.assert_called_once()
        call_kwargs = mock_bg.call_args.kwargs
        assert call_kwargs["module_path"] == "agentic_devtools.cli.github.pr_poll_ready"
        assert call_kwargs["function_name"] == "poll_pr_ready"
        assert call_kwargs["args"]["pr_number"] == 1
        mock_track.assert_called_once()
        assert "PR #1" in mock_track.call_args.args[1]

    @patch(f"{_MODULE}.poll_pr_ready")
    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_does_not_dispatch_background_by_default(self, mock_resolve, mock_poll, capsys):
        """Does not run in background when --background is not set."""
        mock_poll.return_value = {"ready": True, "reason": "test"}
        with patch("sys.argv", ["agdt-gh-pr-poll-ready", "--pr", "1"]):
            pr_poll_ready_command()
        mock_poll.assert_called_once()


class TestPrPollReadyCommandRerunFlag:
    """Tests for --rerun-stale-checks flag."""

    @patch(f"{_MODULE}.poll_pr_ready")
    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_rerun_enabled_by_default(self, mock_resolve, mock_poll, capsys):
        """Rerun stale checks is enabled by default."""
        mock_poll.return_value = {"ready": True, "reason": "test"}
        with patch("sys.argv", ["agdt-gh-pr-poll-ready", "--pr", "1"]):
            pr_poll_ready_command()
        assert mock_poll.call_args.kwargs["rerun_stale_checks"] is True

    @patch(f"{_MODULE}.poll_pr_ready")
    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_rerun_can_be_disabled(self, mock_resolve, mock_poll, capsys):
        """Rerun stale checks can be disabled."""
        mock_poll.return_value = {"ready": True, "reason": "test"}
        with patch(
            "sys.argv",
            ["agdt-gh-pr-poll-ready", "--pr", "1", "--no-rerun-stale-checks"],
        ):
            pr_poll_ready_command()
        assert mock_poll.call_args.kwargs["rerun_stale_checks"] is False
