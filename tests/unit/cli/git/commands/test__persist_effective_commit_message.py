"""Tests for agentic_devtools.cli.git.commands._persist_effective_commit_message."""

from contextlib import nullcontext
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git import commands


class TestPersistEffectiveCommitMessage:
    """Tests for _persist_effective_commit_message()."""

    @patch("agentic_devtools.cli.git.commands.read_modify_write_state")
    @patch("agentic_devtools.cli.git.commands.run_git")
    def test_persists_commit_message_on_success(self, mock_run_git, mock_read_modify_write_state):
        """Happy path: reads back commit and stores all keys in state."""
        state = {}
        mock_read_modify_write_state.return_value = nullcontext(state)
        mock_run_git.return_value = MagicMock(returncode=0, stdout="feat: my commit\n\nBody text\n")
        commands._persist_effective_commit_message(dry_run=False)
        assert state["git"]["last_commit_message"] == "feat: my commit\n\nBody text"
        assert state["git"]["last_commit_title"] == "feat: my commit"
        assert state["git"]["last_commit_body"] == "Body text"

    @patch("agentic_devtools.cli.git.commands.read_modify_write_state")
    @patch("agentic_devtools.cli.git.commands.run_git")
    def test_skips_on_dry_run(self, mock_run_git, mock_read_modify_write_state):
        """Skips persistence in dry-run mode."""
        commands._persist_effective_commit_message(dry_run=True)
        mock_run_git.assert_not_called()
        mock_read_modify_write_state.assert_not_called()

    @patch("agentic_devtools.cli.git.commands.read_modify_write_state")
    @patch("agentic_devtools.cli.git.commands.run_git")
    def test_skips_on_git_failure(self, mock_run_git, mock_read_modify_write_state):
        """Does not store when git log fails."""
        mock_run_git.return_value = MagicMock(returncode=1, stdout="")
        commands._persist_effective_commit_message(dry_run=False)
        mock_read_modify_write_state.assert_not_called()

    @patch("agentic_devtools.cli.git.commands.read_modify_write_state")
    @patch("agentic_devtools.cli.git.commands.run_git")
    def test_skips_on_empty_output(self, mock_run_git, mock_read_modify_write_state):
        """Does not store when git log returns empty output."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="   \n")
        commands._persist_effective_commit_message(dry_run=False)
        mock_read_modify_write_state.assert_not_called()

    @patch("agentic_devtools.cli.git.commands.read_modify_write_state")
    @patch("agentic_devtools.cli.git.commands.run_git")
    def test_strips_trailing_newlines(self, mock_run_git, mock_read_modify_write_state):
        """Trailing newlines are stripped from the stored message."""
        state = {}
        mock_read_modify_write_state.return_value = nullcontext(state)
        mock_run_git.return_value = MagicMock(returncode=0, stdout="fix: bug\n\n\n")
        commands._persist_effective_commit_message(dry_run=False)
        assert state["git"]["last_commit_message"] == "fix: bug"
        assert state["git"]["last_commit_title"] == "fix: bug"
        assert state["git"]["last_commit_body"] == ""

    @patch("agentic_devtools.cli.git.commands.read_modify_write_state")
    @patch("agentic_devtools.cli.git.commands.run_git")
    def test_title_only_message_sets_empty_body(self, mock_run_git, mock_read_modify_write_state):
        """Title-only message sets body to empty string."""
        state = {}
        mock_read_modify_write_state.return_value = nullcontext(state)
        mock_run_git.return_value = MagicMock(returncode=0, stdout="feat(#42): title only\n")
        commands._persist_effective_commit_message(dry_run=False)
        assert state["git"]["last_commit_body"] == ""

    @patch("agentic_devtools.cli.git.commands.read_modify_write_state")
    @patch("agentic_devtools.cli.git.commands.run_git")
    def test_overwrites_non_dict_git_state(self, mock_run_git, mock_read_modify_write_state):
        """Non-dict git state is replaced with a dict before persisting keys."""
        state = {"git": "invalid"}
        mock_read_modify_write_state.return_value = nullcontext(state)
        mock_run_git.return_value = MagicMock(returncode=0, stdout="feat: my commit\n")

        commands._persist_effective_commit_message(dry_run=False)

        assert state["git"]["last_commit_message"] == "feat: my commit"

    @patch("agentic_devtools.cli.git.commands.read_modify_write_state")
    @patch("agentic_devtools.cli.git.commands.run_git")
    def test_reuses_existing_git_dict_state(self, mock_run_git, mock_read_modify_write_state):
        """Existing git dict state is updated in place."""
        existing_git_state = {"existing_key": "existing_value"}
        state = {"git": existing_git_state}
        mock_read_modify_write_state.return_value = nullcontext(state)
        mock_run_git.return_value = MagicMock(returncode=0, stdout="feat: my commit\n")

        commands._persist_effective_commit_message(dry_run=False)

        assert state["git"] is existing_git_state
        assert state["git"]["existing_key"] == "existing_value"
        assert state["git"]["last_commit_message"] == "feat: my commit"
