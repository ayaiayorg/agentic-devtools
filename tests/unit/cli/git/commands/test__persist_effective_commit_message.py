"""Tests for agentic_devtools.cli.git.commands._persist_effective_commit_message."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git import commands


class TestPersistEffectiveCommitMessage:
    """Tests for _persist_effective_commit_message()."""

    @patch("agentic_devtools.cli.git.commands.set_value")
    @patch("agentic_devtools.cli.git.commands.run_git")
    def test_persists_commit_message_on_success(self, mock_run_git, mock_set_value):
        """Happy path: reads back commit and stores in state."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="feat: my commit\n\nBody text\n")
        commands._persist_effective_commit_message(dry_run=False)
        mock_set_value.assert_called_once_with("git.last_commit_message", "feat: my commit\n\nBody text")

    @patch("agentic_devtools.cli.git.commands.set_value")
    @patch("agentic_devtools.cli.git.commands.run_git")
    def test_skips_on_dry_run(self, mock_run_git, mock_set_value):
        """Skips persistence in dry-run mode."""
        commands._persist_effective_commit_message(dry_run=True)
        mock_run_git.assert_not_called()
        mock_set_value.assert_not_called()

    @patch("agentic_devtools.cli.git.commands.set_value")
    @patch("agentic_devtools.cli.git.commands.run_git")
    def test_skips_on_git_failure(self, mock_run_git, mock_set_value):
        """Does not store when git log fails."""
        mock_run_git.return_value = MagicMock(returncode=1, stdout="")
        commands._persist_effective_commit_message(dry_run=False)
        mock_set_value.assert_not_called()

    @patch("agentic_devtools.cli.git.commands.set_value")
    @patch("agentic_devtools.cli.git.commands.run_git")
    def test_skips_on_empty_output(self, mock_run_git, mock_set_value):
        """Does not store when git log returns empty output."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="   \n")
        commands._persist_effective_commit_message(dry_run=False)
        mock_set_value.assert_not_called()

    @patch("agentic_devtools.cli.git.commands.set_value")
    @patch("agentic_devtools.cli.git.commands.run_git")
    def test_strips_trailing_newlines(self, mock_run_git, mock_set_value):
        """Trailing newlines are stripped from the stored message."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="fix: bug\n\n\n")
        commands._persist_effective_commit_message(dry_run=False)
        mock_set_value.assert_called_once_with("git.last_commit_message", "fix: bug")
