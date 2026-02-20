"""Tests for agentic_devtools.cli.git.commands._sync_with_main."""

from unittest.mock import patch

from agentic_devtools.cli.git import commands


class TestSyncWithMain:
    """Tests for _sync_with_main function.

    The function returns True if a rebase occurred (history rewritten),
    False if no rebase occurred (skipped, fetch failed, or no rebase needed).
    """

    def test_skips_rebase_when_flag_set(self, temp_state_dir, clear_state_before, capsys):
        """Test skips rebase when skip_rebase is True."""
        result = commands._sync_with_main(dry_run=False, skip_rebase=True)

        assert result is False
        captured = capsys.readouterr()
        assert "Skipping rebase" in captured.out

    @patch("agentic_devtools.cli.git.commands.fetch_main")
    def test_continues_on_fetch_failure(self, mock_fetch, temp_state_dir, clear_state_before, capsys):
        """Test continues when fetch from main fails."""
        mock_fetch.return_value = False

        result = commands._sync_with_main(dry_run=False, skip_rebase=False)

        assert result is False
        captured = capsys.readouterr()
        assert "Could not fetch from origin/main" in captured.out

    @patch("agentic_devtools.cli.git.commands.rebase_onto_main")
    @patch("agentic_devtools.cli.git.commands.fetch_main")
    def test_handles_rebase_success(self, mock_fetch, mock_rebase, temp_state_dir, clear_state_before):
        """Test returns True on successful rebase (history was rewritten)."""
        from unittest.mock import MagicMock

        mock_fetch.return_value = True
        mock_rebase.return_value = MagicMock(is_success=True, was_rebased=True)

        result = commands._sync_with_main(dry_run=False, skip_rebase=False)

        assert result is True

    @patch("agentic_devtools.cli.git.commands.rebase_onto_main")
    @patch("agentic_devtools.cli.git.commands.fetch_main")
    def test_returns_false_when_no_rebase_needed(self, mock_fetch, mock_rebase, temp_state_dir, clear_state_before):
        """Test returns False when already up-to-date (no rebase needed)."""
        from unittest.mock import MagicMock

        mock_fetch.return_value = True
        mock_rebase.return_value = MagicMock(is_success=True, was_rebased=False)

        result = commands._sync_with_main(dry_run=False, skip_rebase=False)

        assert result is False
