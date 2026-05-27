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
    def test_skips_injection_when_run_id_is_empty(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
        capsys,
    ):
        """When agdt_run_id is empty (missing or whitespace-only, normalized by resolver), helper returns False."""
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
    def test_model_none_does_not_read_from_state(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
    ):
        """When model is not provided, it stays None without reading copilot.model_id from state."""
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"copilot": {"model_id": "claude-3.5-sonnet"}}), encoding="utf-8")

        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-123"),
        ):
            _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_inject.assert_called_once_with(str(tmp_path), COPILOT_SESSION_START_PROMPT, run_id="run-123", model=None)

    @patch(f"{_MODULE}.inject_auto_start_task", return_value=True)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "prompt"])
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_model_parameter_forwarded_without_state_fallback(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
    ):
        """When model is provided explicitly, it is used directly without any state fallback."""
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"copilot": {"model_id": "stale-model"}}), encoding="utf-8")

        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-123"),
        ):
            _maybe_inject_auto_start_before_vscode(str(tmp_path), model="gpt-4o")

        mock_inject.assert_called_once_with(
            str(tmp_path), COPILOT_SESSION_START_PROMPT, run_id="run-123", model="gpt-4o"
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

    @patch(f"{_MODULE}._write_pending_auto_start_marker")
    @patch(f"{_MODULE}.inject_auto_start_task", return_value=True)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "prompt"])
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_writes_marker_file_after_successful_injection(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        mock_write_marker,
        tmp_path,
    ):
        """When injection succeeds, _write_pending_auto_start_marker is called."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-789"),
        ):
            _maybe_inject_auto_start_before_vscode(str(tmp_path), model="gpt-4")

        mock_write_marker.assert_called_once_with(str(tmp_path), "run-789", COPILOT_SESSION_START_PROMPT, model="gpt-4")

    @patch(f"{_MODULE}._write_pending_auto_start_marker")
    @patch(f"{_MODULE}.inject_auto_start_task", return_value=False)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "prompt"])
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_writes_marker_even_when_injection_fails(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        mock_write_marker,
        tmp_path,
    ):
        """When injection fails, marker is still written for terminal sendSequence fallback."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-fail"),
        ):
            _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_write_marker.assert_called_once_with(str(tmp_path), "run-fail", COPILOT_SESSION_START_PROMPT, model=None)

    @patch(f"{_MODULE}._write_pending_auto_start_marker")
    @patch(f"{_MODULE}.inject_auto_start_task")
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=None)
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_writes_marker_when_build_copilot_args_returns_none(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        mock_write_marker,
        tmp_path,
    ):
        """Marker is written even when build_copilot_args returns None (prompt exceeds argv limits)."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-no-args"),
        ):
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_write_marker.assert_called_once_with(
            str(tmp_path), "run-no-args", COPILOT_SESSION_START_PROMPT, model=None
        )
        mock_inject.assert_not_called()
        assert result is False

    @patch(f"{_MODULE}._write_pending_auto_start_marker")
    @patch(f"{_MODULE}.inject_auto_start_task")
    @patch("agentic_devtools.cli.copilot.build_copilot_args")
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_marker_not_written_when_run_id_empty(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        mock_write_marker,
        tmp_path,
    ):
        """Marker is NOT written when run_id is empty."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, ""),
        ):
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_write_marker.assert_not_called()
        mock_build_args.assert_not_called()
        mock_inject.assert_not_called()
        assert result is False

    # ── Tests for the ``run_id`` parameter (pre-generated by caller) ──

    @patch(f"{_MODULE}._write_pending_auto_start_marker")
    @patch(f"{_MODULE}.inject_auto_start_task", return_value=True)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "prompt"])
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_uses_provided_run_id_and_skips_state_read(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        mock_write_marker,
        tmp_path,
    ):
        """When run_id is provided, _resolve_state_context_in_worktree is called with include_run_id=False."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, ""),
        ) as mock_resolve:
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path), run_id="abc123def456")

        mock_resolve.assert_called_once_with(str(tmp_path), include_run_id=False)
        mock_inject.assert_called_once_with(
            str(tmp_path), COPILOT_SESSION_START_PROMPT, run_id="abc123def456", model=None
        )
        mock_write_marker.assert_called_once_with(
            str(tmp_path), "abc123def456", COPILOT_SESSION_START_PROMPT, model=None
        )
        assert result is True

    @patch(f"{_MODULE}.inject_auto_start_task")
    @patch("agentic_devtools.cli.copilot.build_copilot_args")
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_provided_run_id_skips_when_state_path_is_none(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
        capsys,
    ):
        """When run_id is provided but resolved context returns no state path.

        Injection is skipped.
        """
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(None, ""),
        ):
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path), run_id="abc123def456")

        mock_build_args.assert_not_called()
        mock_inject.assert_not_called()
        assert result is False
        captured = capsys.readouterr()
        assert "could not resolve state context" in captured.out
        assert str(tmp_path) in captured.out

    @patch(f"{_MODULE}.inject_auto_start_task", return_value=True)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "prompt"])
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_none_run_id_falls_back_to_state_read(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
    ):
        """When run_id is None (default), the existing state-reading behaviour is preserved."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "state-run-id"),
        ) as mock_resolve:
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path))

        mock_resolve.assert_called_once_with(str(tmp_path), include_run_id=True)
        mock_inject.assert_called_once_with(
            str(tmp_path), COPILOT_SESSION_START_PROMPT, run_id="state-run-id", model=None
        )
        assert result is True

    @patch(f"{_MODULE}.inject_auto_start_task")
    @patch("agentic_devtools.cli.copilot.build_copilot_args")
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_empty_string_run_id_falls_back_to_state_read(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
        capsys,
    ):
        """When run_id is empty string, it falls through to state-reading path."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, ""),
        ) as mock_resolve:
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path), run_id="")

        mock_resolve.assert_called_once_with(str(tmp_path), include_run_id=True)
        mock_inject.assert_not_called()
        assert result is False
        captured = capsys.readouterr()
        assert "missing or empty agdt_run_id" in captured.out

    @patch(f"{_MODULE}.inject_auto_start_task")
    @patch("agentic_devtools.cli.copilot.build_copilot_args")
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_whitespace_only_run_id_falls_back_to_state_read(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        tmp_path,
        capsys,
    ):
        """When run_id is whitespace-only, it falls through to state-reading path."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, ""),
        ) as mock_resolve:
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path), run_id="   ")

        mock_resolve.assert_called_once_with(str(tmp_path), include_run_id=True)
        mock_inject.assert_not_called()
        assert result is False
        captured = capsys.readouterr()
        assert "missing or empty agdt_run_id" in captured.out

    @patch(f"{_MODULE}._write_pending_auto_start_marker")
    @patch(f"{_MODULE}.inject_auto_start_task", return_value=True)
    @patch("agentic_devtools.cli.copilot.build_copilot_args", return_value=["copilot", "-i", "prompt"])
    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_provided_run_id_is_stripped(
        self,
        mock_in_test,
        mock_build_args,
        mock_inject,
        mock_write_marker,
        tmp_path,
    ):
        """When run_id has leading/trailing whitespace, it is stripped before use."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, ""),
        ) as mock_resolve:
            result = _maybe_inject_auto_start_before_vscode(str(tmp_path), run_id="  abc123  ")

        mock_resolve.assert_called_once_with(str(tmp_path), include_run_id=False)
        mock_inject.assert_called_once_with(str(tmp_path), COPILOT_SESSION_START_PROMPT, run_id="abc123", model=None)
        assert result is True
