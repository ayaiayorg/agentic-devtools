"""Tests for _maybe_inject_auto_start_before_vscode."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import (
    COPILOT_SESSION_START_PROMPT,
    COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE,
    _maybe_inject_auto_start_before_vscode,
)

_MODULE = "agentic_devtools.cli.workflows.worktree_setup"


class TestMaybeInjectAutoStartBeforeVscode:
    """Tests for _maybe_inject_auto_start_before_vscode helper."""

    @patch(f"{_MODULE}.inject_auto_start_task", return_value=True)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "prompt"])
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_injects_task_when_copilot_args_available(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
        capsys,
    ):
        """When copilot args are available and run_id is present, inject the auto-start task."""
        with patch("agentic_devtools.state.get_value", return_value="run-123"):
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_build_args.assert_called_once_with(COPILOT_SESSION_START_PROMPT, interactive=True)
        mock_inject.assert_called_once_with(str(tmp_path), COPILOT_SESSION_START_PROMPT, run_id="run-123")
        captured = capsys.readouterr()
        assert "auto-start task injected" in captured.out
        assert result is True

    @patch(f"{_MODULE}.inject_auto_start_task")
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=None)
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_skips_when_build_copilot_args_returns_none(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
        capsys,
    ):
        """When build_copilot_args returns None (Copilot CLI not found), skip injection."""
        with patch("agentic_devtools.state.get_value", return_value="run-123"):
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_build_args.assert_called_once()
        mock_inject.assert_not_called()
        assert result is False
        captured = capsys.readouterr()
        assert "Copilot CLI not available" in captured.out

    @patch(f"{_MODULE}.inject_auto_start_task", return_value=False)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "prompt"])
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_prints_warning_when_injection_fails(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
        capsys,
    ):
        """When inject_auto_start_task returns False, a warning message should be printed."""
        with patch("agentic_devtools.state.get_value", return_value="run-123"):
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_inject.assert_called_once()
        captured = capsys.readouterr()
        assert "auto-start task injected" not in captured.out
        assert "auto-start task injection failed" in captured.out
        assert result is False

    @patch(f"{_MODULE}.inject_auto_start_task", return_value=True)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "custom"])
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_passes_custom_start_prompt_to_build_copilot_args(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
    ):
        """When a custom start_prompt is provided, it is forwarded to build_copilot_args."""
        with patch("agentic_devtools.state.get_value", return_value="run-123"):
            _maybe_inject_auto_start_before_vscode(
                str(tmp_path),
                start_prompt=COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE,
            )

        mock_build_args.assert_called_once_with(COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE, interactive=True)
        mock_inject.assert_called_once()

    def test_returns_false_in_pytest_environment(self, tmp_path):
        """Returns False without calling build_copilot_args when running in test environment.

        On Windows, mock paths like /repos/DFLY-1234 resolve to C:\\repos\\DFLY-1234
        which may be a real worktree. Writing a runOn:folderOpen task there causes
        VS Code to open unexpected windows during test runs.
        """
        # _in_test_environment() returns True by default during pytest runs
        result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        assert result is False

    @patch(f"{_MODULE}.inject_auto_start_task", return_value=True)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "prompt"])
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_skips_injection_when_get_value_raises(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
        capsys,
    ):
        """When get_value raises, injection is skipped and False is returned."""
        with patch("agentic_devtools.state.get_value", side_effect=RuntimeError("state unavailable")):
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_build_args.assert_not_called()
        mock_inject.assert_not_called()
        assert result is False
        captured = capsys.readouterr()
        assert "could not read agdt_run_id" in captured.out

    @patch(f"{_MODULE}.inject_auto_start_task")
    @patch("agentic_devtools.cli.copilot.build_copilot_args")
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_skips_injection_when_run_id_is_not_string(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
        capsys,
    ):
        """When agdt_run_id is not a string, helper returns False before building args."""
        with patch("agentic_devtools.state.get_value", return_value=123):
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_build_args.assert_not_called()
        mock_inject.assert_not_called()
        assert result is False
        captured = capsys.readouterr()
        assert "agdt_run_id is not a string" in captured.out

    @patch(f"{_MODULE}.inject_auto_start_task")
    @patch("agentic_devtools.cli.copilot.build_copilot_args")
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_skips_injection_when_run_id_is_whitespace_only(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
        capsys,
    ):
        """When agdt_run_id is only whitespace, helper returns False before building args."""
        with patch("agentic_devtools.state.get_value", return_value="   "):
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_build_args.assert_not_called()
        mock_inject.assert_not_called()
        assert result is False
        captured = capsys.readouterr()
        assert "agdt_run_id is empty or whitespace" in captured.out
