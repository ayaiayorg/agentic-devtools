"""Tests for resolve_github_repo in repo_resolution module."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.github import repo_resolution


class TestResolveGithubRepo:
    """Tests for resolve_github_repo."""

    def test_cli_arg_has_priority(self):
        """CLI argument is returned when provided."""
        result = repo_resolution.resolve_github_repo("owner/repo")
        assert result == "owner/repo"

    def test_cli_arg_stripped(self):
        """CLI argument is stripped of whitespace."""
        result = repo_resolution.resolve_github_repo("  owner/repo  ")
        assert result == "owner/repo"

    def test_empty_string_cli_arg_falls_through(self):
        """Empty string CLI arg is treated as not provided."""
        with patch.object(repo_resolution, "get_value", return_value="state/repo"):
            result = repo_resolution.resolve_github_repo("")
        assert result == "state/repo"

    def test_whitespace_cli_arg_falls_through(self):
        """Whitespace-only CLI arg is treated as not provided."""
        with patch.object(repo_resolution, "get_value", return_value="state/repo"):
            result = repo_resolution.resolve_github_repo("   ")
        assert result == "state/repo"

    def test_state_fallback(self):
        """Falls back to github.repo from state."""
        with patch.object(repo_resolution, "get_value", return_value="from-state/repo"):
            result = repo_resolution.resolve_github_repo(None)
        assert result == "from-state/repo"

    def test_git_remote_fallback(self):
        """Falls back to git remote when state is empty."""
        with patch.object(repo_resolution, "get_value", return_value=None):
            with patch.object(
                repo_resolution,
                "_get_git_origin_url",
                return_value="https://github.com/owner/repo.git",
            ):
                result = repo_resolution.resolve_github_repo(None)
        assert result == "owner/repo"

    def test_exits_when_all_fail(self):
        """Exits with code 1 when all resolution methods fail."""
        with patch.object(repo_resolution, "get_value", return_value=None):
            with patch.object(repo_resolution, "_get_git_origin_url", return_value=None):
                with pytest.raises(SystemExit) as exc_info:
                    repo_resolution.resolve_github_repo(None)
        assert exc_info.value.code == 1

    def test_non_github_remote_exits(self):
        """Non-GitHub remote URL causes exit when no other source available."""
        with patch.object(repo_resolution, "get_value", return_value=None):
            with patch.object(
                repo_resolution,
                "_get_git_origin_url",
                return_value="https://gitlab.com/owner/repo.git",
            ):
                with pytest.raises(SystemExit) as exc_info:
                    repo_resolution.resolve_github_repo(None)
        assert exc_info.value.code == 1
