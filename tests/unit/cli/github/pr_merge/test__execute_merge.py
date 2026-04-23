"""Tests for _execute_merge helper."""

from types import SimpleNamespace
from unittest.mock import patch

from agentic_devtools.cli.github import pr_merge


class TestExecuteMerge:
    """Tests for _execute_merge."""

    def test_success_squash(self):
        """Successful squash merge returns (True, '')."""
        mock_result = SimpleNamespace(returncode=0, stdout="", stderr="")
        with patch.object(pr_merge, "run_safe", return_value=mock_result) as mock_run:
            ok, err = pr_merge._execute_merge(42, "o/r", "squash", True)

        assert ok is True
        assert err == ""
        cmd = mock_run.call_args[0][0]
        assert "--squash" in cmd
        assert "--yes" not in cmd

    def test_success_merge_strategy(self):
        """Successful merge strategy includes --merge."""
        mock_result = SimpleNamespace(returncode=0, stdout="", stderr="")
        with patch.object(pr_merge, "run_safe", return_value=mock_result) as mock_run:
            ok, err = pr_merge._execute_merge(42, "o/r", "merge", True)

        assert ok is True
        cmd = mock_run.call_args[0][0]
        assert "--merge" in cmd

    def test_success_rebase_strategy(self):
        """Successful rebase strategy includes --rebase."""
        mock_result = SimpleNamespace(returncode=0, stdout="", stderr="")
        with patch.object(pr_merge, "run_safe", return_value=mock_result) as mock_run:
            ok, err = pr_merge._execute_merge(42, "o/r", "rebase", True)

        assert ok is True
        cmd = mock_run.call_args[0][0]
        assert "--rebase" in cmd

    def test_delete_branch_true(self):
        """--delete-branch present when delete_branch=True."""
        mock_result = SimpleNamespace(returncode=0, stdout="", stderr="")
        with patch.object(pr_merge, "run_safe", return_value=mock_result) as mock_run:
            pr_merge._execute_merge(42, "o/r", "squash", True)

        cmd = mock_run.call_args[0][0]
        assert "--delete-branch" in cmd

    def test_delete_branch_false(self):
        """--delete-branch absent when delete_branch=False."""
        mock_result = SimpleNamespace(returncode=0, stdout="", stderr="")
        with patch.object(pr_merge, "run_safe", return_value=mock_result) as mock_run:
            pr_merge._execute_merge(42, "o/r", "squash", False)

        cmd = mock_run.call_args[0][0]
        assert "--delete-branch" not in cmd

    def test_failure_returns_stderr(self):
        """Non-zero exit returns stderr content when available."""
        mock_result = SimpleNamespace(returncode=1, stdout="", stderr="  conflict detected  ")
        with patch.object(pr_merge, "run_safe", return_value=mock_result):
            ok, err = pr_merge._execute_merge(42, "o/r", "squash", True)

        assert ok is False
        assert err == "conflict detected"

    def test_failure_uses_stdout_when_stderr_empty(self):
        """Non-zero exit falls back to stdout when stderr is empty."""
        mock_result = SimpleNamespace(returncode=1, stdout="  merge failed on stdout  ", stderr="")
        with patch.object(pr_merge, "run_safe", return_value=mock_result):
            ok, err = pr_merge._execute_merge(42, "o/r", "squash", True)

        assert ok is False
        assert err == "merge failed on stdout"

    def test_failure_uses_default_message_when_no_output(self):
        """Non-zero exit uses default message when stderr/stdout are both empty."""
        mock_result = SimpleNamespace(returncode=1, stdout="", stderr="")
        with patch.object(pr_merge, "run_safe", return_value=mock_result):
            ok, err = pr_merge._execute_merge(42, "o/r", "squash", True)

        assert ok is False
        assert err == "Merge command failed with no output."

    def test_shell_false_always(self):
        """shell=False is always passed to run_safe."""
        mock_result = SimpleNamespace(returncode=0, stdout="", stderr="")
        with patch.object(pr_merge, "run_safe", return_value=mock_result) as mock_run:
            pr_merge._execute_merge(42, "o/r", "squash", True)

        assert mock_run.call_args[1]["shell"] is False

    def test_repo_in_command(self):
        """--repo flag includes the repo string."""
        mock_result = SimpleNamespace(returncode=0, stdout="", stderr="")
        with patch.object(pr_merge, "run_safe", return_value=mock_result) as mock_run:
            pr_merge._execute_merge(42, "owner/repo", "squash", True)

        cmd = mock_run.call_args[0][0]
        assert "--repo" in cmd
        repo_idx = cmd.index("--repo")
        assert cmd[repo_idx + 1] == "owner/repo"

    def test_file_not_found_error_returns_failure(self):
        """FileNotFoundError from run_safe is caught and returned as failure."""
        with patch.object(pr_merge, "run_safe", side_effect=FileNotFoundError("gh not found")):
            ok, err = pr_merge._execute_merge(42, "o/r", "squash", True)

        assert ok is False
        assert "gh not found" in err

    def test_os_error_returns_failure(self):
        """OSError from run_safe is caught and returned as failure."""
        with patch.object(pr_merge, "run_safe", side_effect=OSError("permission denied")):
            ok, err = pr_merge._execute_merge(42, "o/r", "squash", True)

        assert ok is False
        assert "permission denied" in err
