"""Tests for resolve_github_repo_safe."""

from unittest.mock import patch

from agentic_devtools.cli.github.repo_resolution import resolve_github_repo_safe

_MOD = "agentic_devtools.cli.github.repo_resolution"


class TestResolveGithubRepoSafe:
    """Tests for resolve_github_repo_safe."""

    @patch(f"{_MOD}.get_value", return_value="myorg/myrepo")
    def test_returns_state_repo(self, mock_get):
        """Returns github.repo state key when valid."""
        result = resolve_github_repo_safe()
        assert result == "myorg/myrepo"
        mock_get.assert_called_once_with("github.repo")

    @patch(f"{_MOD}._resolve_repo_from_git_remote", return_value="remote-org/remote-repo")
    @patch(f"{_MOD}.get_value", return_value=None)
    def test_falls_back_to_git_remote(self, mock_get, mock_remote):
        """Falls back to git remote when state is empty."""
        result = resolve_github_repo_safe()
        assert result == "remote-org/remote-repo"

    @patch(f"{_MOD}._resolve_repo_from_git_remote", return_value=None)
    @patch(f"{_MOD}.get_value", return_value=None)
    def test_returns_none_when_all_fail(self, mock_get, mock_remote):
        """Returns None when no resolution succeeds (no sys.exit)."""
        result = resolve_github_repo_safe()
        assert result is None

    @patch(f"{_MOD}._resolve_repo_from_git_remote", return_value="remote-org/remote-repo")
    @patch(f"{_MOD}.get_value", return_value="invalid-format")
    def test_malformed_state_falls_through(self, mock_get, mock_remote):
        """Malformed state value falls through to git remote."""
        result = resolve_github_repo_safe()
        assert result == "remote-org/remote-repo"

    @patch(f"{_MOD}.get_value", return_value="  owner/repo  ")
    def test_state_value_stripped(self, mock_get):
        """State value is stripped before validation."""
        result = resolve_github_repo_safe()
        assert result == "owner/repo"

    @patch(f"{_MOD}.get_value", return_value="owner/repo.git")
    def test_strips_dot_git_suffix(self, mock_get):
        """Strips .git suffix from state value."""
        result = resolve_github_repo_safe()
        assert result == "owner/repo"

    @patch(f"{_MOD}._resolve_repo_from_git_remote", return_value=None)
    @patch(f"{_MOD}.get_value", return_value="")
    def test_empty_state_returns_none(self, mock_get, mock_remote):
        """Empty string state value returns None."""
        result = resolve_github_repo_safe()
        assert result is None
