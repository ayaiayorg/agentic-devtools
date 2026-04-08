"""Tests for _submit_approval helper."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.github import pr_approve


class TestSubmitApproval:
    """Tests for _submit_approval."""

    def test_success_returns_true(self):
        """Exit code 0 returns (True, '')."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            ok, err = pr_approve._submit_approval(1115, "owner/repo", "LGTM")

        assert ok is True
        assert err == ""

    def test_failure_returns_false_with_stderr(self):
        """Non-zero exit returns (False, stderr) when stderr is populated."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "pull request is in draft state"
        mock_result.stdout = ""

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            ok, err = pr_approve._submit_approval(1115, "owner/repo", "LGTM")

        assert ok is False
        assert err == "pull request is in draft state"

    def test_failure_falls_back_to_stdout_when_stderr_empty(self):
        """Non-zero exit falls back to stdout when stderr is empty."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = ""
        mock_result.stdout = "stdout error detail"

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            ok, err = pr_approve._submit_approval(1115, "owner/repo", "LGTM")

        assert ok is False
        assert err == "stdout error detail"

    def test_failure_falls_back_to_exit_code_when_both_empty(self):
        """Non-zero exit falls back to exit code message when stderr and stdout are empty."""
        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stderr = ""
        mock_result.stdout = ""

        with patch.object(pr_approve, "run_safe", return_value=mock_result):
            ok, err = pr_approve._submit_approval(1115, "owner/repo", "LGTM")

        assert ok is False
        assert err == "gh pr review failed with exit code 2"

    def test_command_args_correct(self):
        """Verifies the exact command arguments passed to run_safe."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.object(pr_approve, "run_safe", return_value=mock_result) as mock_run:
            pr_approve._submit_approval(42, "owner/repo", "my body")

        call_args = mock_run.call_args[0][0]
        assert call_args == [
            "gh",
            "pr",
            "review",
            "42",
            "--repo",
            "owner/repo",
            "--approve",
            "--body",
            "my body",
        ]

    def test_uses_shell_false(self):
        """run_safe must be called with shell=False."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.object(pr_approve, "run_safe", return_value=mock_result) as mock_run:
            pr_approve._submit_approval(1, "o/r", "b")

        assert mock_run.call_args[1]["shell"] is False
