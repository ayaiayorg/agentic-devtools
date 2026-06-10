"""Tests for agentic_devtools.cli.pr_template.resolve_main_ref."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli import pr_template


class TestResolveMainRef:
    """Tests for resolve_main_ref()."""

    @patch("agentic_devtools.cli.pr_template.run_git")
    def test_returns_origin_main_when_exists(self, mock_run_git):
        """Happy path: origin/main exists."""
        mock_run_git.return_value = MagicMock(returncode=0)
        result = pr_template.resolve_main_ref()
        assert result == "origin/main"
        mock_run_git.assert_called_once_with("rev-parse", "--verify", "origin/main", check=False)

    @patch("agentic_devtools.cli.pr_template.run_git")
    def test_returns_main_when_origin_main_missing(self, mock_run_git):
        """Falls back to main when origin/main doesn't exist."""
        origin_fail = MagicMock(returncode=1)
        main_ok = MagicMock(returncode=0)
        mock_run_git.side_effect = [origin_fail, main_ok]

        result = pr_template.resolve_main_ref()
        assert result == "main"
        assert mock_run_git.call_count == 2

    @patch("agentic_devtools.cli.pr_template.run_git")
    def test_returns_none_when_neither_exists(self, mock_run_git):
        """Returns None when neither ref exists."""
        mock_run_git.return_value = MagicMock(returncode=1)
        result = pr_template.resolve_main_ref()
        assert result is None
        assert mock_run_git.call_count == 2
