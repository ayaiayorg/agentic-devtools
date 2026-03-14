"""Tests for _maybe_inject_auto_start_before_vscode."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import (
    _maybe_inject_auto_start_before_vscode,
)


class TestMaybeInjectAutoStartBeforeVscode:
    """Tests for _maybe_inject_auto_start_before_vscode helper."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_auto_start_task", return_value=True)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "prompt"])
    def test_injects_task_when_interactive(
        self,
        mock_build_args,
        mock_inject,
        tmp_path,
        capsys,
    ):
        """When interactive=True and copilot args are available, inject the auto-start task."""
        _maybe_inject_auto_start_before_vscode(str(tmp_path), interactive=True)

        mock_build_args.assert_called_once()
        mock_inject.assert_called_once_with(str(tmp_path), ["copilot", "-i", "prompt"])
        captured = capsys.readouterr()
        assert "auto-start task injected" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_auto_start_task")
    @patch("agentic_devtools.cli.copilot.build_copilot_args")
    def test_skips_when_not_interactive(
        self,
        mock_build_args,
        mock_inject,
        tmp_path,
    ):
        """When interactive=False, skip injection entirely."""
        _maybe_inject_auto_start_before_vscode(str(tmp_path), interactive=False)

        mock_build_args.assert_not_called()
        mock_inject.assert_not_called()

    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_auto_start_task")
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=None)
    def test_skips_when_build_copilot_args_returns_none(
        self,
        mock_build_args,
        mock_inject,
        tmp_path,
    ):
        """When build_copilot_args returns None (Copilot CLI not found), skip injection."""
        _maybe_inject_auto_start_before_vscode(str(tmp_path), interactive=True)

        mock_build_args.assert_called_once()
        mock_inject.assert_not_called()

    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_auto_start_task", return_value=False)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "prompt"])
    def test_does_not_print_when_injection_fails(
        self,
        mock_build_args,
        mock_inject,
        tmp_path,
        capsys,
    ):
        """When inject_auto_start_task returns False, no success message should be printed."""
        _maybe_inject_auto_start_before_vscode(str(tmp_path), interactive=True)

        mock_inject.assert_called_once()
        captured = capsys.readouterr()
        assert "auto-start task injected" not in captured.out
