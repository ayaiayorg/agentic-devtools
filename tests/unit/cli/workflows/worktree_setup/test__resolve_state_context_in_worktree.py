"""Tests for _resolve_state_context_in_worktree."""

import os
from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import _resolve_state_context_in_worktree


def test_restores_both_state_env_vars_and_returns_run_id(tmp_path, monkeypatch):
    """The helper resolves state in worktree context and restores both state-dir env vars."""
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir(parents=True, exist_ok=True)

    original_cwd = os.getcwd()
    monkeypatch.setenv("AGENTIC_DEVTOOLS_STATE_DIR", "modern-before")
    monkeypatch.setenv("DFLY_AI_HELPERS_STATE_DIR", "legacy-before")

    captured = {}

    def fake_get_state_file_path():
        captured["cwd"] = os.getcwd()
        captured["modern"] = os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR")
        captured["legacy"] = os.environ.get("DFLY_AI_HELPERS_STATE_DIR")
        return worktree_path / ".agdt" / "workflows" / "_scope" / "state.json"

    def fake_get_value(key):
        assert key == "agdt_run_id"
        captured["value_cwd"] = os.getcwd()
        captured["value_modern"] = os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR")
        captured["value_legacy"] = os.environ.get("DFLY_AI_HELPERS_STATE_DIR")
        return "run-123"

    monkeypatch.setattr("agentic_devtools.state.get_state_file_path", fake_get_state_file_path)
    monkeypatch.setattr("agentic_devtools.state.get_value", fake_get_value)

    state_file_path, run_id = _resolve_state_context_in_worktree(str(worktree_path), include_run_id=True)

    assert state_file_path == worktree_path / ".agdt" / "workflows" / "_scope" / "state.json"
    assert run_id == "run-123"

    # During resolution, both env vars are intentionally unset.
    assert captured == {
        "cwd": str(worktree_path),
        "modern": None,
        "legacy": None,
        "value_cwd": str(worktree_path),
        "value_modern": None,
        "value_legacy": None,
    }

    # After resolution, original context is restored.
    assert os.getcwd() == original_cwd
    assert os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR") == "modern-before"
    assert os.environ.get("DFLY_AI_HELPERS_STATE_DIR") == "legacy-before"


def test_normalizes_non_string_run_id_to_empty_string(tmp_path, monkeypatch):
    """When agdt_run_id is non-string, helper returns an empty run_id."""
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "agentic_devtools.state.get_state_file_path",
        lambda: worktree_path / ".agdt" / "workflows" / "_scope" / "state.json",
    )
    monkeypatch.setattr("agentic_devtools.state.get_value", lambda _key: ["bad-type"])

    state_file_path, run_id = _resolve_state_context_in_worktree(str(worktree_path), include_run_id=True)

    assert state_file_path == worktree_path / ".agdt" / "workflows" / "_scope" / "state.json"
    assert run_id == ""


def test_strips_whitespace_from_run_id(tmp_path, monkeypatch):
    """When agdt_run_id is a string, helper returns a stripped run_id."""
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "agentic_devtools.state.get_state_file_path",
        lambda: worktree_path / ".agdt" / "workflows" / "_scope" / "state.json",
    )
    monkeypatch.setattr("agentic_devtools.state.get_value", lambda _key: "  run-xyz  ")

    _state_file_path, run_id = _resolve_state_context_in_worktree(str(worktree_path), include_run_id=True)

    assert run_id == "run-xyz"


def test_ignores_restore_cwd_failure_and_still_restores_env(tmp_path, monkeypatch):
    """If restoring previous cwd fails, helper still returns and restores state env vars."""
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir(parents=True, exist_ok=True)

    original_cwd = os.getcwd()
    monkeypatch.setenv("AGENTIC_DEVTOOLS_STATE_DIR", "modern-before")
    monkeypatch.setenv("DFLY_AI_HELPERS_STATE_DIR", "legacy-before")

    monkeypatch.setattr(
        "agentic_devtools.state.get_state_file_path",
        lambda: worktree_path / ".agdt" / "workflows" / "_scope" / "state.json",
    )

    real_chdir = os.chdir

    def flaky_chdir(path):
        if str(path) == original_cwd:
            raise FileNotFoundError("cwd disappeared")
        real_chdir(path)

    monkeypatch.setattr("agentic_devtools.cli.workflows.worktree_setup.os.chdir", flaky_chdir)

    state_file_path, run_id = _resolve_state_context_in_worktree(str(worktree_path), include_run_id=False)

    assert state_file_path == worktree_path / ".agdt" / "workflows" / "_scope" / "state.json"
    assert run_id == ""
    assert os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR") == "modern-before"
    assert os.environ.get("DFLY_AI_HELPERS_STATE_DIR") == "legacy-before"

    real_chdir(original_cwd)


def test_ignores_restore_modern_state_dir_env_failure(tmp_path, monkeypatch):
    """Raising in the AGENTIC_DEVTOOLS_STATE_DIR restore block is silently swallowed."""
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "agentic_devtools.state.get_state_file_path",
        lambda: worktree_path / ".agdt" / "workflows" / "_scope" / "state.json",
    )
    monkeypatch.delenv("AGENTIC_DEVTOOLS_STATE_DIR", raising=False)
    monkeypatch.delenv("DFLY_AI_HELPERS_STATE_DIR", raising=False)

    # The function calls os.environ.pop 4 times total (2 at entry, 2 in finally).
    # Making the 3rd call raise covers the except block for AGENTIC_DEVTOOLS_STATE_DIR restore.
    with patch.object(os.environ, "pop", side_effect=[None, None, RuntimeError("env restore failed"), None]):
        state_file_path, run_id = _resolve_state_context_in_worktree(str(worktree_path))

    assert state_file_path == worktree_path / ".agdt" / "workflows" / "_scope" / "state.json"
    assert run_id == ""


def test_ignores_restore_legacy_state_dir_env_failure(tmp_path, monkeypatch):
    """Raising in the DFLY_AI_HELPERS_STATE_DIR restore block is silently swallowed."""
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "agentic_devtools.state.get_state_file_path",
        lambda: worktree_path / ".agdt" / "workflows" / "_scope" / "state.json",
    )
    monkeypatch.delenv("AGENTIC_DEVTOOLS_STATE_DIR", raising=False)
    monkeypatch.delenv("DFLY_AI_HELPERS_STATE_DIR", raising=False)

    # The function calls os.environ.pop 4 times total (2 at entry, 2 in finally).
    # Making the 4th call raise covers the except block for DFLY_AI_HELPERS_STATE_DIR restore.
    with patch.object(os.environ, "pop", side_effect=[None, None, None, RuntimeError("env restore failed")]):
        state_file_path, run_id = _resolve_state_context_in_worktree(str(worktree_path))

    assert state_file_path == worktree_path / ".agdt" / "workflows" / "_scope" / "state.json"
    assert run_id == ""
