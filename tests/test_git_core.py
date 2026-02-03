"""
Tests for git core utilities.

Tests cover:
- State helpers (get_bool_state)
- Commit message retrieval
- Git command execution
- Branch detection
- Temp file handling
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agdt_ai_helpers import state
from agdt_ai_helpers.cli.git import core

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state.clear_state()
    yield


@pytest.fixture
def mock_run_safe():
    """Mock run_safe for git commands."""
    with patch.object(core, "run_safe") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        yield mock_run


# =============================================================================
# State Helper Tests
# =============================================================================


class TestGetBoolState:
    """Tests for get_bool_state helper."""

    def test_get_bool_state_true_values(self, temp_state_dir, clear_state_before):
        """Test that truthy values return True."""
        for value in [True, "true", "1", "yes"]:
            state.set_value("test_key", value)
            assert core.get_bool_state("test_key") is True

    def test_get_bool_state_false_values(self, temp_state_dir, clear_state_before):
        """Test that falsy values return False."""
        for value in [False, "false", "0", "no", "", "anything"]:
            state.set_value("test_key", value)
            assert core.get_bool_state("test_key") is False

    def test_get_bool_state_missing_key_default_false(self, temp_state_dir, clear_state_before):
        """Test that missing key returns default False."""
        result = core.get_bool_state("nonexistent_key")
        assert result is False

    def test_get_bool_state_missing_key_custom_default(self, temp_state_dir, clear_state_before):
        """Test that missing key returns custom default."""
        result = core.get_bool_state("nonexistent_key", default=True)
        assert result is True


class TestGetCommitMessage:
    """Tests for commit message retrieval."""

    def test_get_commit_message_returns_value(self, temp_state_dir, clear_state_before):
        """Test getting commit message from state."""
        state.set_value("commit_message", "Test commit")
        message = core.get_commit_message()
        assert message == "Test commit"

    def test_get_commit_message_missing_exits(self, temp_state_dir, clear_state_before):
        """Test that missing commit message causes exit."""
        with pytest.raises(SystemExit) as exc_info:
            core.get_commit_message()
        assert exc_info.value.code == 1

    def test_get_multiline_commit_message(self, temp_state_dir, clear_state_before):
        """Test getting multiline commit message."""
        multiline = "Title\n\n- Change 1\n- Change 2"
        state.set_value("commit_message", multiline)
        message = core.get_commit_message()
        assert message == multiline

    def test_get_commit_message_with_special_characters(self, temp_state_dir, clear_state_before):
        """Test commit message with special characters works without tokens."""
        special = 'feature([DFLY-1234](https://jira.swica.ch)): test\'s "quotes" & more!'
        state.set_value("commit_message", special)
        message = core.get_commit_message()
        assert message == special


# =============================================================================
# Git Execution Tests
# =============================================================================


class TestRunGit:
    """Tests for git command execution."""

    def test_run_git_success(self, mock_run_safe):
        """Test successful git command."""
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="output", stderr="")
        result = core.run_git("status")
        mock_run_safe.assert_called_once()
        assert result.returncode == 0

    def test_run_git_failure_exits(self, mock_run_safe):
        """Test git command failure causes exit."""
        mock_run_safe.return_value = MagicMock(returncode=1, stdout="", stderr="error message")
        with pytest.raises(SystemExit) as exc_info:
            core.run_git("bad-command")
        assert exc_info.value.code == 1

    def test_run_git_failure_prints_stderr(self, mock_run_safe, capsys):
        """Test git command failure prints stderr output."""
        mock_run_safe.return_value = MagicMock(returncode=128, stdout="", stderr="fatal: not a git repository")
        with pytest.raises(SystemExit):
            core.run_git("status")
        captured = capsys.readouterr()
        assert "fatal: not a git repository" in captured.err

    def test_run_git_failure_without_stderr(self, mock_run_safe, capsys):
        """Test git command failure with empty stderr."""
        mock_run_safe.return_value = MagicMock(returncode=1, stdout="", stderr="")
        with pytest.raises(SystemExit):
            core.run_git("bad-command")
        captured = capsys.readouterr()
        assert "Error:" in captured.err

    def test_run_git_failure_with_check_false_returns_result(self, mock_run_safe):
        """Test that check=False returns result instead of exiting."""
        mock_run_safe.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = core.run_git("bad-command", check=False)
        assert result.returncode == 1

    def test_run_git_constructs_correct_command(self, mock_run_safe):
        """Test that command is constructed correctly."""
        core.run_git("commit", "-m", "message")
        called_cmd = mock_run_safe.call_args[0][0]
        assert called_cmd == ["git", "commit", "-m", "message"]


class TestGetCurrentBranch:
    """Tests for branch name detection."""

    def test_get_current_branch_success(self, mock_run_safe):
        """Test getting branch name."""
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="feature/test\n", stderr="")
        branch = core.get_current_branch()
        assert branch == "feature/test"

    def test_get_current_branch_detached_head_exits(self, mock_run_safe):
        """Test that detached HEAD state causes exit."""
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="HEAD\n", stderr="")
        with pytest.raises(SystemExit) as exc_info:
            core.get_current_branch()
        assert exc_info.value.code == 1

    def test_get_current_branch_empty_exits(self, mock_run_safe):
        """Test that empty branch name causes exit."""
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="", stderr="")
        with pytest.raises(SystemExit) as exc_info:
            core.get_current_branch()
        assert exc_info.value.code == 1


# =============================================================================
# Temp File Tests
# =============================================================================


class TestTempMessageFile:
    """Tests for temporary message file context manager."""

    def test_temp_message_file_creates_and_cleans_up(self):
        """Test temp file is created and cleaned up."""
        message = "Test message\nLine 2"
        temp_path = None

        with core.temp_message_file(message) as path:
            temp_path = path
            assert Path(path).exists()
            assert Path(path).read_text(encoding="utf-8") == message

        assert not Path(temp_path).exists()

    def test_temp_message_file_cleans_up_on_exception(self):
        """Test temp file is cleaned up even on exception."""
        temp_path = None

        try:
            with core.temp_message_file("Test") as path:
                temp_path = path
                raise ValueError("Test exception")
        except ValueError:
            pass

        assert not Path(temp_path).exists()

    def test_temp_message_file_handles_cleanup_oserror(self, monkeypatch):
        """Test that OSError during cleanup is silently handled."""
        message = "Test message"
        cleanup_attempted = []

        def mock_unlink(self, missing_ok=False):
            cleanup_attempted.append(True)
            raise OSError("Permission denied")

        with monkeypatch.context() as m:
            m.setattr(Path, "unlink", mock_unlink)
            with core.temp_message_file(message):
                pass

        assert len(cleanup_attempted) == 1
