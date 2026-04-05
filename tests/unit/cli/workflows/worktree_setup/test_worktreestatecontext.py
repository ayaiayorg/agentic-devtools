"""Tests for WorktreeStateContext."""

import os
from unittest.mock import patch

import pytest

from agentic_devtools.cli.workflows.worktree_setup import WorktreeStateContext


class TestWorktreeStateContext:
    """Tests for the WorktreeStateContext context manager."""

    def test_enter_changes_cwd_and_clears_env_vars(self, tmp_path, monkeypatch):
        """On enter, CWD is changed and both env vars are cleared."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        monkeypatch.setenv("AGENTIC_DEVTOOLS_STATE_DIR", "/some/dir")
        monkeypatch.setenv("AGDT_AI_HELPERS_STATE_DIR", "/legacy/dir")

        ctx = WorktreeStateContext(str(worktree))
        ctx.__enter__()
        try:
            assert os.getcwd() == str(worktree)
            assert "AGENTIC_DEVTOOLS_STATE_DIR" not in os.environ
            assert "AGDT_AI_HELPERS_STATE_DIR" not in os.environ
        finally:
            ctx.__exit__(None, None, None)

    def test_exit_restores_cwd_and_env_vars(self, tmp_path, monkeypatch):
        """On exit, CWD and both env vars are restored to pre-entry values."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        original_cwd = os.getcwd()
        monkeypatch.setenv("AGENTIC_DEVTOOLS_STATE_DIR", "/original/modern")
        monkeypatch.setenv("AGDT_AI_HELPERS_STATE_DIR", "/original/legacy")

        with WorktreeStateContext(str(worktree)):
            pass

        assert os.getcwd() == original_cwd
        assert os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR") == "/original/modern"
        assert os.environ.get("AGDT_AI_HELPERS_STATE_DIR") == "/original/legacy"

    def test_exit_restores_when_env_vars_were_absent(self, tmp_path, monkeypatch):
        """When env vars were absent before entering, they remain absent after exiting."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        monkeypatch.delenv("AGENTIC_DEVTOOLS_STATE_DIR", raising=False)
        monkeypatch.delenv("AGDT_AI_HELPERS_STATE_DIR", raising=False)

        with WorktreeStateContext(str(worktree)):
            pass

        assert "AGENTIC_DEVTOOLS_STATE_DIR" not in os.environ
        assert "AGDT_AI_HELPERS_STATE_DIR" not in os.environ

    def test_exit_restores_on_exception(self, tmp_path, monkeypatch):
        """CWD and env vars are restored even when body raises an exception."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        original_cwd = os.getcwd()
        monkeypatch.setenv("AGENTIC_DEVTOOLS_STATE_DIR", "/before")
        monkeypatch.setenv("AGDT_AI_HELPERS_STATE_DIR", "/legacy-before")

        with pytest.raises(RuntimeError, match="test error"):
            with WorktreeStateContext(str(worktree)):
                raise RuntimeError("test error")

        assert os.getcwd() == original_cwd
        assert os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR") == "/before"
        assert os.environ.get("AGDT_AI_HELPERS_STATE_DIR") == "/legacy-before"

    def test_exit_restores_cwd_even_if_env_restore_fails(self, tmp_path, monkeypatch):
        """CWD is restored even when restoring an env var raises."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        original_cwd = os.getcwd()
        monkeypatch.setenv("AGENTIC_DEVTOOLS_STATE_DIR", "/before")

        ctx = WorktreeStateContext(str(worktree))
        ctx.__enter__()

        # Sabotage env var restore so it raises on __setitem__
        real_setitem = os.environ.__class__.__setitem__
        call_count = 0

        def broken_setitem(self_env, key, value):
            nonlocal call_count
            if key == "AGENTIC_DEVTOOLS_STATE_DIR":
                call_count += 1
                if call_count == 1:
                    raise RuntimeError("env restore failed")
            return real_setitem(self_env, key, value)

        with patch.object(os.environ.__class__, "__setitem__", broken_setitem):
            ctx.__exit__(None, None, None)

        # CWD must still be restored despite the env restore failure
        assert os.getcwd() == original_cwd

    def test_chdir_failure_restores_env_vars(self, tmp_path, monkeypatch):
        """When os.chdir fails in __enter__, env vars are restored and the exception propagates."""
        nonexistent = str(tmp_path / "does_not_exist")

        monkeypatch.setenv("AGENTIC_DEVTOOLS_STATE_DIR", "/saved/modern")
        monkeypatch.setenv("AGDT_AI_HELPERS_STATE_DIR", "/saved/legacy")

        with pytest.raises((FileNotFoundError, OSError)):
            with WorktreeStateContext(nonexistent):
                pass  # pragma: no cover

        assert os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR") == "/saved/modern"
        assert os.environ.get("AGDT_AI_HELPERS_STATE_DIR") == "/saved/legacy"
