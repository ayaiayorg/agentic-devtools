"""Tests for _run_copilot_with_retry."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.copilot.auto_start import _run_copilot_with_retry

_SUBPROC = "agentic_devtools.cli.copilot.auto_start.subprocess.run"
_SLEEP = "agentic_devtools.cli.copilot.auto_start.time.sleep"


def _win_error_32() -> OSError:
    """Create an OSError simulating WinError 32."""
    exc = OSError("The process cannot access the file because it is being used by another process")
    exc.winerror = 32  # type: ignore[attr-defined]
    return exc


class TestRunCopilotWithRetrySuccess:
    """Tests for successful execution paths."""

    def test_succeeds_on_first_try(self):
        """Returns CompletedProcess when subprocess succeeds immediately."""
        mock_result = MagicMock(spec=subprocess.CompletedProcess, returncode=0)
        with patch(_SUBPROC, return_value=mock_result) as mock_run:
            result = _run_copilot_with_retry(["copilot", "-i"], "/some/path")

        assert result.returncode == 0
        mock_run.assert_called_once_with(["copilot", "-i"], cwd="/some/path")

    def test_succeeds_after_one_retry(self):
        """Retries once on WinError 32 then succeeds."""
        mock_result = MagicMock(spec=subprocess.CompletedProcess, returncode=0)
        with (
            patch(_SUBPROC, side_effect=[_win_error_32(), mock_result]) as mock_run,
            patch(_SLEEP) as mock_sleep,
        ):
            result = _run_copilot_with_retry(["copilot", "-i"], "/some/path")

        assert result.returncode == 0
        assert mock_run.call_count == 2
        mock_sleep.assert_called_once_with(0.5)

    def test_succeeds_after_two_retries(self):
        """Retries twice on WinError 32 then succeeds."""
        mock_result = MagicMock(spec=subprocess.CompletedProcess, returncode=0)
        with (
            patch(_SUBPROC, side_effect=[_win_error_32(), _win_error_32(), mock_result]) as mock_run,
            patch(_SLEEP) as mock_sleep,
        ):
            result = _run_copilot_with_retry(["copilot", "-i"], "/some/path")

        assert result.returncode == 0
        assert mock_run.call_count == 3
        assert mock_sleep.call_count == 2
        # Verify backoff delays: 0.5, 1.0
        mock_sleep.assert_any_call(0.5)
        mock_sleep.assert_any_call(1.0)

    def test_succeeds_after_five_retries(self):
        """Retries 5 times (max) on WinError 32 then succeeds on 6th try."""
        mock_result = MagicMock(spec=subprocess.CompletedProcess, returncode=0)
        side_effects = [_win_error_32() for _ in range(5)] + [mock_result]
        with (
            patch(_SUBPROC, side_effect=side_effects) as mock_run,
            patch(_SLEEP) as mock_sleep,
        ):
            result = _run_copilot_with_retry(["copilot", "-i"], "/some/path")

        assert result.returncode == 0
        assert mock_run.call_count == 6
        assert mock_sleep.call_count == 5
        # Verify backoff delays: 0.5, 1.0, 2.0, 4.0, 4.0 (capped)
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [0.5, 1.0, 2.0, 4.0, 4.0]


class TestRunCopilotWithRetryExhaustion:
    """Tests for retry budget exhaustion."""

    def test_raises_after_six_total_tries(self, capsys):
        """Raises last OSError after exhausting all 6 attempts."""
        side_effects = [_win_error_32() for _ in range(6)]
        with (
            patch(_SUBPROC, side_effect=side_effects) as mock_run,
            patch(_SLEEP),
        ):
            with pytest.raises(OSError) as exc_info:
                _run_copilot_with_retry(["copilot", "-i"], "/some/path")

        assert getattr(exc_info.value, "winerror", None) == 32
        assert mock_run.call_count == 6
        captured = capsys.readouterr()
        assert "retry budget exhausted" in captured.err
        assert "6 attempts" in captured.err

    def test_exhaustion_log_contains_winerror_code(self, capsys):
        """Final failure log includes the winerror code."""
        side_effects = [_win_error_32() for _ in range(6)]
        with patch(_SUBPROC, side_effect=side_effects), patch(_SLEEP):
            with pytest.raises(OSError):
                _run_copilot_with_retry(["copilot", "-i"], "/some/path")

        captured = capsys.readouterr()
        assert "winerror=32" in captured.err


class TestRunCopilotWithRetryNonRetryable:
    """Tests for non-retryable errors (no retry attempted)."""

    def test_non_retryable_oserror_no_winerror_fails_immediately(self):
        """OSError without winerror attribute raises immediately without retry."""
        exc = OSError("Permission denied")
        with (
            patch(_SUBPROC, side_effect=exc) as mock_run,
            patch(_SLEEP) as mock_sleep,
        ):
            with pytest.raises(OSError, match="Permission denied"):
                _run_copilot_with_retry(["copilot", "-i"], "/some/path")

        mock_run.assert_called_once()
        mock_sleep.assert_not_called()

    def test_oserror_winerror_5_fails_immediately(self):
        """OSError with winerror=5 (access denied) raises immediately without retry."""
        exc = OSError("Access denied")
        exc.winerror = 5  # type: ignore[attr-defined]
        with (
            patch(_SUBPROC, side_effect=exc) as mock_run,
            patch(_SLEEP) as mock_sleep,
        ):
            with pytest.raises(OSError, match="Access denied"):
                _run_copilot_with_retry(["copilot", "-i"], "/some/path")

        mock_run.assert_called_once()
        mock_sleep.assert_not_called()

    def test_filenotfounderror_fails_immediately(self):
        """FileNotFoundError raises immediately without retry."""
        with (
            patch(_SUBPROC, side_effect=FileNotFoundError("not found")) as mock_run,
            patch(_SLEEP) as mock_sleep,
        ):
            with pytest.raises(FileNotFoundError):
                _run_copilot_with_retry(["copilot", "-i"], "/some/path")

        mock_run.assert_called_once()
        mock_sleep.assert_not_called()

    def test_error_type_change_mid_retry(self):
        """WinError 32 followed by FileNotFoundError raises immediately on the new error."""
        side_effects = [_win_error_32(), _win_error_32(), FileNotFoundError("gone")]
        with (
            patch(_SUBPROC, side_effect=side_effects) as mock_run,
            patch(_SLEEP),
        ):
            with pytest.raises(FileNotFoundError):
                _run_copilot_with_retry(["copilot", "-i"], "/some/path")

        assert mock_run.call_count == 3


class TestRunCopilotWithRetryDefensiveRaise:
    """Tests for validation of retry configuration."""

    def test_raises_value_error_when_max_attempts_negative(self):
        """Negative _RETRY_MAX_ATTEMPTS raises ValueError with clear message."""
        with patch("agentic_devtools.cli.copilot.auto_start._RETRY_MAX_ATTEMPTS", -1):
            with pytest.raises(ValueError, match="_RETRY_MAX_ATTEMPTS must be >= 0"):
                _run_copilot_with_retry(["copilot", "-i"], "/some/path")


class TestRunCopilotWithRetryInterrupt:
    """Tests for KeyboardInterrupt during backoff."""

    def test_keyboard_interrupt_during_sleep_propagates(self):
        """KeyboardInterrupt during time.sleep propagates immediately."""
        with (
            patch(_SUBPROC, side_effect=_win_error_32()),
            patch(_SLEEP, side_effect=KeyboardInterrupt),
        ):
            with pytest.raises(KeyboardInterrupt):
                _run_copilot_with_retry(["copilot", "-i"], "/some/path")


class TestRunCopilotWithRetryLogging:
    """Tests for retry log output."""

    def test_retry_log_contains_attempt_and_delay(self, capsys):
        """Each retry log line includes attempt number and delay."""
        mock_result = MagicMock(spec=subprocess.CompletedProcess, returncode=0)
        with (
            patch(_SUBPROC, side_effect=[_win_error_32(), mock_result]),
            patch(_SLEEP),
        ):
            _run_copilot_with_retry(["copilot", "-i"], "/some/path")

        captured = capsys.readouterr()
        assert "attempt 1/6" in captured.err
        assert "0.5s" in captured.err
        assert "winerror=32" in captured.err
