"""Tests for _parse_github_remote_url in repo_resolution module."""

from agentic_devtools.cli.github.repo_resolution import _parse_github_remote_url


class TestParseGithubRemoteUrl:
    """Tests for _parse_github_remote_url."""

    def test_https_with_git_suffix(self):
        """Parses HTTPS URL with .git suffix."""
        result = _parse_github_remote_url("https://github.com/owner/repo.git")
        assert result == "owner/repo"

    def test_https_without_git_suffix(self):
        """Parses HTTPS URL without .git suffix."""
        result = _parse_github_remote_url("https://github.com/owner/repo")
        assert result == "owner/repo"

    def test_ssh_url(self):
        """Parses SSH URL."""
        result = _parse_github_remote_url("git@github.com:owner/repo.git")
        assert result == "owner/repo"

    def test_ssh_url_without_git(self):
        """Parses SSH URL without .git suffix."""
        result = _parse_github_remote_url("git@github.com:owner/repo")
        assert result == "owner/repo"

    def test_non_github_url_returns_none(self):
        """Non-GitHub URL returns None."""
        result = _parse_github_remote_url("https://gitlab.com/owner/repo.git")
        assert result is None

    def test_azure_devops_url_returns_none(self):
        """Azure DevOps URL returns None."""
        result = _parse_github_remote_url("https://dev.azure.com/org/project/_git/repo")
        assert result is None

    def test_dots_in_owner_and_repo(self):
        """Handles dots in owner and repo names."""
        result = _parse_github_remote_url("https://github.com/my.org/my.repo.git")
        assert result == "my.org/my.repo"

    def test_hyphens_in_names(self):
        """Handles hyphens in owner and repo names."""
        result = _parse_github_remote_url("https://github.com/my-org/my-repo.git")
        assert result == "my-org/my-repo"

    def test_empty_string_returns_none(self):
        """Empty string returns None."""
        result = _parse_github_remote_url("")
        assert result is None
