"""
Tests for run_details_commands module.
"""

import sys
from unittest.mock import patch

import pytest

from agentic_devtools.cli.azure_devops.run_details_commands import (
    wait_for_run,
    wait_for_run_impl,
)


class TestWaitForRun:
    """Tests for wait_for_run CLI entry point."""

    def test_missing_run_id_exits_with_error(self, temp_state_dir, clear_state_before, capsys):
        """Should exit with error if run_id is not set."""
        with pytest.raises(SystemExit) as exc_info:
            wait_for_run()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "run_id" in captured.err

    def test_invalid_run_id_exits_with_error(self, temp_state_dir, clear_state_before, capsys):
        """Should exit with error if run_id is not an integer."""
        from agentic_devtools.state import set_value

        set_value("run_id", "not-a-number")

        with pytest.raises(SystemExit) as exc_info:
            wait_for_run()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "integer" in captured.err

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Should show dry run output when dry_run is set."""
        from agentic_devtools.state import set_value

        set_value("run_id", "12345")
        set_value("dry_run", "true")

        wait_for_run()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "12345" in captured.out

    @patch("agentic_devtools.cli.azure_devops.run_details_commands.wait_for_run_impl")
    def test_cli_args_override_state(self, mock_impl, temp_state_dir, clear_state_before, capsys, monkeypatch):
        """CLI args should override state values."""
        from agentic_devtools.state import set_value

        set_value("run_id", "111")

        mock_impl.return_value = {"success": True}

        # Simulate CLI args
        monkeypatch.setattr(sys, "argv", ["wait_for_run", "--run-id", "222", "--poll-interval", "5"])

        wait_for_run()

        # Verify impl was called with CLI arg values
        mock_impl.assert_called_once()
        call_kwargs = mock_impl.call_args[1]
        assert call_kwargs["run_id"] == 222
        assert call_kwargs["poll_interval"] == 5

    @patch("agentic_devtools.cli.azure_devops.run_details_commands.wait_for_run_impl")
    def test_exits_on_failure(self, mock_impl, temp_state_dir, clear_state_before, capsys):
        """Should exit with code 1 when impl returns failure."""
        from agentic_devtools.state import set_value

        set_value("run_id", "123")

        mock_impl.return_value = {"success": False, "error": "Some error"}

        with pytest.raises(SystemExit) as exc_info:
            wait_for_run()

        assert exc_info.value.code == 1

    @patch("agentic_devtools.cli.azure_devops.run_details_commands.wait_for_run_impl")
    def test_invalid_poll_interval_uses_default(self, mock_impl, temp_state_dir, clear_state_before, capsys):
        """Should use default poll interval when state value is invalid."""
        from agentic_devtools.state import set_value

        set_value("run_id", "123")
        set_value("poll_interval", "not-a-number")

        mock_impl.return_value = {"success": True}

        wait_for_run()

        captured = capsys.readouterr()
        assert "Invalid poll_interval" in captured.out
        # Should still call impl with default
        mock_impl.assert_called_once()

    @patch("agentic_devtools.cli.azure_devops.run_details_commands.wait_for_run_impl")
    def test_invalid_max_failures_uses_default(self, mock_impl, temp_state_dir, clear_state_before, capsys):
        """Should use default max failures when state value is invalid."""
        from agentic_devtools.state import set_value

        set_value("run_id", "123")
        set_value("max_failures", "invalid")

        mock_impl.return_value = {"success": True}

        wait_for_run()

        captured = capsys.readouterr()
        assert "Invalid max_failures" in captured.out
        mock_impl.assert_called_once()

    @patch("agentic_devtools.cli.azure_devops.run_details_commands.wait_for_run_impl")
    def test_fetch_logs_from_state_string_true(self, mock_impl, temp_state_dir, clear_state_before):
        """Should parse fetch_logs string value from state."""
        from agentic_devtools.state import set_value

        set_value("run_id", "123")
        set_value("fetch_logs", "true")

        mock_impl.return_value = {"success": True}

        wait_for_run()

        call_kwargs = mock_impl.call_args[1]
        assert call_kwargs["fetch_logs"] is True

    @patch("agentic_devtools.cli.azure_devops.run_details_commands.wait_for_run_impl")
    def test_vpn_toggle_from_state_string_yes(self, mock_impl, temp_state_dir, clear_state_before):
        """Should parse vpn_toggle string value from state."""
        from agentic_devtools.state import set_value

        set_value("run_id", "123")
        set_value("vpn_toggle", "yes")

        mock_impl.return_value = {"success": True}

        wait_for_run()

        call_kwargs = mock_impl.call_args[1]
        assert call_kwargs["vpn_toggle"] is True


class TestWaitForRunImpl:
    """Tests for wait_for_run_impl function."""

    def test_dry_run_returns_success(self, capsys):
        """Should return success in dry run mode."""
        result = wait_for_run_impl(run_id=12345, dry_run=True)

        assert result["success"] is True
        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "12345" in captured.out

    @patch("agentic_devtools.cli.azure_devops.run_details_commands.get_run_details_impl")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands.time.sleep")
    def test_returns_after_run_completes(self, mock_sleep, mock_get_details, capsys):
        """Should return when run completes successfully."""
        mock_get_details.return_value = {
            "success": True,
            "data": {
                "status": "completed",
                "result": "succeeded",
                "_links": {"web": {"href": "https://example.com"}},
            },
        }

        result = wait_for_run_impl(run_id=123, poll_interval=1)

        assert result["success"] is True
        assert result["finished"] is True
        assert result["result"] == "succeeded"
        mock_sleep.assert_not_called()

    @patch("agentic_devtools.cli.azure_devops.run_details_commands.get_run_details_impl")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands.time.sleep")
    def test_polls_until_complete(self, mock_sleep, mock_get_details, capsys):
        """Should poll multiple times until run completes."""
        # First call: in progress, second call: completed
        mock_get_details.side_effect = [
            {
                "success": True,
                "data": {"status": "inProgress", "result": None},
            },
            {
                "success": True,
                "data": {
                    "status": "completed",
                    "result": "succeeded",
                    "_links": {"web": {"href": "https://example.com"}},
                },
            },
        ]

        result = wait_for_run_impl(run_id=123, poll_interval=1)

        assert result["success"] is True
        assert result["poll_count"] == 2
        mock_sleep.assert_called_once_with(1)

    @patch("agentic_devtools.cli.azure_devops.run_details_commands.get_run_details_impl")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands.time.sleep")
    def test_fails_after_max_consecutive_failures(self, mock_sleep, mock_get_details, capsys):
        """Should fail after max consecutive fetch failures."""
        mock_get_details.return_value = {
            "success": False,
            "error": "API error",
        }

        result = wait_for_run_impl(run_id=123, poll_interval=1, max_failures=2)

        assert result["success"] is False
        assert "2 times consecutively" in result["error"]
        # Sleep is called once after first failure, then second failure hits max and returns
        assert mock_sleep.call_count == 1

    @patch("agentic_devtools.cli.azure_devops.run_details_commands.get_run_details_impl")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands.fetch_failed_job_logs")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands._print_failed_logs_summary")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands.time.sleep")
    def test_fetches_logs_on_failure_when_requested(
        self, mock_sleep, mock_print_summary, mock_fetch_logs, mock_get_details, capsys
    ):
        """Should fetch logs when run fails and fetch_logs is True."""
        mock_get_details.return_value = {
            "success": True,
            "data": {
                "status": "completed",
                "result": "failed",
                "_links": {"web": {"href": "https://example.com"}},
            },
        }
        mock_fetch_logs.return_value = {
            "success": True,
            "log_files": [{"task_name": "Build", "path": "/tmp/log"}],
        }

        result = wait_for_run_impl(run_id=123, fetch_logs=True)

        assert result["success"] is True
        assert result["result"] == "failed"
        mock_fetch_logs.assert_called_once()
