"""Tests for agentic_devtools.cli.git.operations.fetch_main."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git import operations


class TestFetchMain:
    """Tests for fetch_main function."""

    def test_fetch_success(self, mock_run_safe):
        """Test successful fetch."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = operations.fetch_main(dry_run=False)
            assert result is True

    def test_fetch_failure(self, mock_run_safe):
        """Test fetch failure returns False."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=1, stdout="", stderr="error")
            result = operations.fetch_main(dry_run=False)
            assert result is False

    def test_fetch_dry_run(self, mock_run_safe, capsys):
        """Test fetch dry run."""
        result = operations.fetch_main(dry_run=True)
        assert result is True
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
