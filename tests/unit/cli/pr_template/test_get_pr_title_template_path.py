"""Tests for agentic_devtools.cli.pr_template.get_pr_title_template_path."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from agentic_devtools.cli import pr_template


class TestGetPrTitleTemplatePath:
    """Tests for get_pr_title_template_path()."""

    def test_returns_path_with_explicit_git_root(self):
        """Returns correct path when git_root is provided."""
        root = Path("/repo")
        result = pr_template.get_pr_title_template_path(git_root=root)
        assert result == root / ".agdt" / "config" / "pr-title-template.j2"

    @patch("agentic_devtools.cli.pr_template.run_git")
    def test_resolves_git_root_from_git(self, mock_run_git):
        """Resolves git root via git rev-parse when not provided."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="/home/user/project\n")
        result = pr_template.get_pr_title_template_path()
        assert result == Path("/home/user/project/.agdt/config/pr-title-template.j2")

    @patch("agentic_devtools.cli.pr_template.run_git")
    def test_falls_back_to_cwd_when_not_git_repo(self, mock_run_git, tmp_path, monkeypatch):
        """Falls back to cwd when not in a git repository."""
        mock_run_git.return_value = MagicMock(returncode=128, stdout="")
        monkeypatch.chdir(tmp_path)
        result = pr_template.get_pr_title_template_path()
        assert result == tmp_path / ".agdt" / "config" / "pr-title-template.j2"
