"""Tests for _prompt_file_relative_path."""

import os
from unittest.mock import patch

import pytest

from agentic_devtools.cli.workflows.worktree_setup import _prompt_file_relative_path


class TestPromptFileRelativePath:
    """Tests for _prompt_file_relative_path function."""

    @patch("agentic_devtools.state.get_state_dir")
    def test_returns_relative_path(self, mock_state_dir, tmp_path):
        """Verify the returned path is relative to the worktree root."""
        state_dir = tmp_path / ".agdt" / "workflows" / "_unscoped"
        state_dir.mkdir(parents=True)
        mock_state_dir.return_value = state_dir

        result = _prompt_file_relative_path(str(tmp_path), "temp-my-workflow-initiate-prompt.md")

        expected = os.path.relpath(
            str(state_dir / "temp-my-workflow-initiate-prompt.md"),
            str(tmp_path),
        )
        assert result == expected

    @patch("agentic_devtools.state.get_state_dir")
    def test_restores_cwd_on_success(self, mock_state_dir, tmp_path):
        """Verify the CWD is restored after successful resolution."""
        state_dir = tmp_path / ".agdt" / "workflows" / "_unscoped"
        state_dir.mkdir(parents=True)
        mock_state_dir.return_value = state_dir

        cwd_before = os.getcwd()
        _prompt_file_relative_path(str(tmp_path), "prompt.md")
        assert os.getcwd() == cwd_before

    @patch("agentic_devtools.state.get_state_dir")
    def test_restores_env_var_on_success(self, mock_state_dir, tmp_path):
        """Verify the env var is restored after successful resolution."""
        state_dir = tmp_path / ".agdt" / "workflows" / "_unscoped"
        state_dir.mkdir(parents=True)
        mock_state_dir.return_value = state_dir

        os.environ["AGENTIC_DEVTOOLS_STATE_DIR"] = "/original/state"
        try:
            _prompt_file_relative_path(str(tmp_path), "prompt.md")
            assert os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR") == "/original/state"
        finally:
            os.environ.pop("AGENTIC_DEVTOOLS_STATE_DIR", None)

    def test_raises_on_invalid_worktree_path(self, tmp_path):
        """Verify that an invalid worktree path raises an error (not UnboundLocalError)."""
        nonexistent = str(tmp_path / "does_not_exist")
        with pytest.raises((FileNotFoundError, OSError)):
            _prompt_file_relative_path(nonexistent, "prompt.md")

    def test_restores_cwd_on_chdir_failure(self, tmp_path):
        """Verify the CWD is restored even when os.chdir() fails."""
        nonexistent = str(tmp_path / "does_not_exist")
        cwd_before = os.getcwd()
        with pytest.raises((FileNotFoundError, OSError)):
            _prompt_file_relative_path(nonexistent, "prompt.md")
        assert os.getcwd() == cwd_before

    def test_restores_env_var_on_chdir_failure(self, tmp_path):
        """Verify the env var is restored even when os.chdir() fails."""
        nonexistent = str(tmp_path / "does_not_exist")
        os.environ["AGENTIC_DEVTOOLS_STATE_DIR"] = "/original/state"
        try:
            with pytest.raises((FileNotFoundError, OSError)):
                _prompt_file_relative_path(nonexistent, "prompt.md")
            assert os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR") == "/original/state"
        finally:
            os.environ.pop("AGENTIC_DEVTOOLS_STATE_DIR", None)
