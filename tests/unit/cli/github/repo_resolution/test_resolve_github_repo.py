"""Tests for resolve_github_repo."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.github.repo_resolution import resolve_github_repo

_MOD = "agentic_devtools.cli.github.repo_resolution"


class TestResolveGithubRepo:
    """Tests for resolve_github_repo."""

    def test_cli_arg_preferred(self):
        """CLI arg is used when provided."""
        result = resolve_github_repo("myorg/myrepo")
        assert result == "myorg/myrepo"

    def test_cli_arg_strips_whitespace(self):
        """CLI arg is stripped before validation."""
        result = resolve_github_repo("  myorg/myrepo  ")
        assert result == "myorg/myrepo"

    def test_cli_arg_invalid_format_exits(self, capsys):
        """Exits with code 1 for invalid --repo format."""
        with pytest.raises(SystemExit) as exc_info:
            resolve_github_repo("justrepo")
        assert exc_info.value.code == 1
        assert "Invalid --repo format" in capsys.readouterr().err

    @patch(f"{_MOD}.get_value", return_value="state-org/state-repo")
    def test_fallback_to_state(self, mock_get):
        """Falls back to github.repo state key."""
        result = resolve_github_repo(None)
        assert result == "state-org/state-repo"
        mock_get.assert_called_once_with("github.repo")

    @patch(f"{_MOD}._resolve_repo_from_git_remote", return_value="remote-org/remote-repo")
    @patch(f"{_MOD}.get_value", return_value=None)
    def test_fallback_to_git_remote(self, mock_get, mock_remote):
        """Falls back to git remote URL."""
        result = resolve_github_repo(None)
        assert result == "remote-org/remote-repo"

    @patch(f"{_MOD}._resolve_repo_from_git_remote", return_value="remote-org/remote-repo")
    @patch(f"{_MOD}.get_value", return_value="justrepo")
    def test_malformed_state_falls_through_to_remote(self, mock_get, mock_remote):
        """Malformed state value (no slash) falls through to git remote."""
        result = resolve_github_repo(None)
        assert result == "remote-org/remote-repo"

    @patch(f"{_MOD}._resolve_repo_from_git_remote", return_value="remote-org/remote-repo")
    @patch(f"{_MOD}.get_value", return_value="a/b/c")
    def test_state_with_extra_slashes_falls_through(self, mock_get, mock_remote):
        """State value with extra slashes is rejected, falls through."""
        result = resolve_github_repo(None)
        assert result == "remote-org/remote-repo"

    @patch(f"{_MOD}.get_value", return_value="  state-org/state-repo  ")
    def test_state_value_stripped(self, mock_get):
        """State value is stripped before use."""
        result = resolve_github_repo(None)
        assert result == "state-org/state-repo"

    @patch(f"{_MOD}._resolve_repo_from_git_remote", return_value=None)
    @patch(f"{_MOD}.get_value", return_value=None)
    def test_exits_when_all_fail(self, mock_get, mock_remote):
        """Calls sys.exit(1) when no resolution succeeds."""
        with pytest.raises(SystemExit) as exc_info:
            resolve_github_repo(None)
        assert exc_info.value.code == 1
