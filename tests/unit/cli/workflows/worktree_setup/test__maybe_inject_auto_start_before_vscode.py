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
        """When copilot args are available, inject the auto-start task."""
        result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_build_args.assert_called_once_with(COPILOT_SESSION_START_PROMPT, interactive=True)
        mock_inject.assert_called_once_with(str(tmp_path), COPILOT_SESSION_START_PROMPT)
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
    ):
        """When build_copilot_args returns None (Copilot CLI not found), skip injection."""
        result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_build_args.assert_called_once()
        mock_inject.assert_not_called()
        assert result is False

    @patch(f"{_MODULE}.inject_auto_start_task", return_value=False)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "prompt"])
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_does_not_print_when_injection_fails(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
        capsys,
    ):
        """When inject_auto_start_task returns False, no success message should be printed."""
        result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_inject.assert_called_once()
        captured = capsys.readouterr()
        assert "auto-start task injected" not in captured.out
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
