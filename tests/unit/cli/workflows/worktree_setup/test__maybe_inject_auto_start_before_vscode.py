"""Tests for _maybe_inject_auto_start_before_vscode."""

import json
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
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-123"),
        ) as mock_resolve:
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_resolve.assert_called_once_with(str(tmp_path), include_run_id=True)
        mock_build_args.assert_called_once_with(COPILOT_SESSION_START_PROMPT, interactive=True, model=None)
        mock_inject.assert_called_once_with(str(tmp_path), COPILOT_SESSION_START_PROMPT, run_id="run-123", model=None)
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
        """When build_copilot_args returns None (prompt too large), skip injection."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-123"),
        ):
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_build_args.assert_called_once()
        mock_inject.assert_not_called()
        assert result is False
        captured = capsys.readouterr()
        assert "Copilot prompt exceeds argv limits" in captured.out

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
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-123"),
        ):
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
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-123"),
        ):
            _maybe_inject_auto_start_before_vscode(
                str(tmp_path),
                start_prompt=COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE,
            )

        mock_build_args.assert_called_once_with(
            COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE, interactive=True, model=None
        )
        mock_inject.assert_called_once()

    def test_returns_false_in_pytest_environment(self, tmp_path):
        """Returns False without calling build_copilot_args when running in test environment.

        On Windows, mock paths like /repos/PROJECT-1234 resolve to C:\\repos\\PROJECT-1234
        which may be a real worktree. Writing a runOn:folderOpen task there causes
        VS Code to open unexpected windows during test runs.
        """
        # _in_test_environment() returns True by default during pytest runs
        result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        assert result is False

    @patch(f"{_MODULE}.inject_auto_start_task", return_value=True)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "prompt"])
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_skips_injection_when_resolve_returns_none_state_path(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
        capsys,
    ):
        """When _resolve_state_context_in_worktree returns None state path, injection is skipped."""
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(None, ""),
        ):
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_build_args.assert_not_called()
        mock_inject.assert_not_called()
        assert result is False
        captured = capsys.readouterr()
        assert "could not read agdt_run_id" in captured.out
        assert str(tmp_path) in captured.out

    @patch(f"{_MODULE}.inject_auto_start_task")
    @patch("agentic_devtools.cli.copilot.build_copilot_args")
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_skips_injection_when_run_id_is_missing(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
        capsys,
    ):
        """When agdt_run_id is missing from the target worktree state, helper returns False."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, ""),
        ):
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_build_args.assert_not_called()
        mock_inject.assert_not_called()
        assert result is False
        captured = capsys.readouterr()
        assert "missing or empty agdt_run_id" in captured.out

    @patch(f"{_MODULE}.inject_auto_start_task")
    @patch("agentic_devtools.cli.copilot.build_copilot_args")
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_skips_injection_when_run_id_is_empty(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
        capsys,
    ):
        """When agdt_run_id is empty (e.g. whitespace-only, normalized by resolver), helper returns False."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, ""),
        ):
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_build_args.assert_not_called()
        mock_inject.assert_not_called()
        assert result is False
        captured = capsys.readouterr()
        assert "missing or empty agdt_run_id" in captured.out

    @patch(f"{_MODULE}.inject_auto_start_task", return_value=True)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "prompt"])
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_forwards_model_to_inject_auto_start_task(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
    ):
        """When model is provided, it is forwarded to inject_auto_start_task."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-123"),
        ):
            _maybe_inject_auto_start_before_vscode(str(tmp_path), model="gpt-4")

        mock_inject.assert_called_once_with(
            str(tmp_path), COPILOT_SESSION_START_PROMPT, run_id="run-123", model="gpt-4"
        )

    @patch(f"{_MODULE}.inject_auto_start_task", return_value=True)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "prompt"])
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_reads_model_from_state_when_not_provided(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
    ):
        """When model is not provided, reads copilot.model_id from target worktree state file."""
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"copilot": {"model_id": "claude-3.5-sonnet"}}), encoding="utf-8")

        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-123"),
        ):
            _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_inject.assert_called_once_with(
            str(tmp_path), COPILOT_SESSION_START_PROMPT, run_id="run-123", model="claude-3.5-sonnet"
        )

    @patch(f"{_MODULE}.inject_auto_start_task", return_value=True)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "prompt"])
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_model_fallback_handles_unreadable_state_file(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
    ):
        """When state file has invalid JSON, model fallback gracefully leaves model as None."""
        state_file = tmp_path / "state.json"
        state_file.write_text("not valid json{{{", encoding="utf-8")

        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-123"),
        ):
            _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_inject.assert_called_once_with(
            str(tmp_path), COPILOT_SESSION_START_PROMPT, run_id="run-123", model=None
        )

    @patch(f"{_MODULE}.inject_auto_start_task", return_value=True)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "prompt"])
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_reads_run_id_from_target_worktree_state_context(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
    ):
        """Verifies _resolve_state_context_in_worktree is called with correct worktree_path."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-456"),
        ) as mock_resolve:
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_resolve.assert_called_once_with(str(tmp_path), include_run_id=True)
        mock_inject.assert_called_once_with(str(tmp_path), COPILOT_SESSION_START_PROMPT, run_id="run-456", model=None)
        assert result is True
