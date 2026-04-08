"""Tests for _resolve_current_user helper."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.github import pr_approve


class TestResolveCurrentUser:
    """Tests for _resolve_current_user."""

    def test_returns_stripped_login(self):
        """Successful call returns stripped login string."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "  acmarsnik  \n"

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            login = pr_approve._resolve_current_user()

        assert login == "acmarsnik"

    def test_exits_on_nonzero_exit_code(self):
        """sys.exit(1) when gh api returns non-zero exit code."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "authentication required"

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            with pytest.raises(SystemExit) as exc_info:
                pr_approve._resolve_current_user()

        assert exc_info.value.code == 1

    def test_exits_on_empty_stdout(self):
        """sys.exit(1) when stdout is empty."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            with pytest.raises(SystemExit) as exc_info:
                pr_approve._resolve_current_user()

        assert exc_info.value.code == 1

    def test_exits_on_whitespace_only_stdout(self):
        """sys.exit(1) when stdout contains only whitespace."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "   \n  "
        mock_result.stderr = ""

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            with pytest.raises(SystemExit) as exc_info:
                pr_approve._resolve_current_user()

        assert exc_info.value.code == 1

    def test_error_includes_gh_stderr_detail(self, capsys):
        """Error message includes gh stderr when available."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "HTTP 401: Bad credentials"

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            with pytest.raises(SystemExit):
                pr_approve._resolve_current_user()

        captured = capsys.readouterr()
        assert "HTTP 401: Bad credentials" in captured.err

    def test_error_includes_exit_code_when_no_detail(self, capsys):
        """Error message includes exit code when no stderr/stdout."""
        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            with pytest.raises(SystemExit):
                pr_approve._resolve_current_user()

        captured = capsys.readouterr()
        assert "gh exited with code 2" in captured.err

    def test_calls_gh_api_with_shell_false(self):
        """Verifies run_safe is called with shell=False."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "testuser\n"

        with patch.object(pr_approve, "run_safe", return_value=mock_result) as mock_run:
            pr_approve._resolve_current_user()

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["shell"] is False
