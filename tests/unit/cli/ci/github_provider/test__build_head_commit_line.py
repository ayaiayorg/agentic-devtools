"""Tests for GitHubActionsProvider._build_head_commit_line."""

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


class TestBuildHeadCommitLine:
    """Tests for the HEAD commit link helper."""

    def test_valid_sha_returns_link(self) -> None:
        result = GitHubActionsProvider._build_head_commit_line("6fdcfb7abc1234567890", "ayaiayorg/agentic-devtools")
        assert result == (
            "\n\n**HEAD**: [6fdcfb7](https://github.com/ayaiayorg/agentic-devtools/commit/6fdcfb7abc1234567890)"
        )

    def test_empty_sha_returns_empty(self) -> None:
        result = GitHubActionsProvider._build_head_commit_line("", "owner/repo")
        assert result == ""

    def test_invalid_repo_returns_empty(self) -> None:
        result = GitHubActionsProvider._build_head_commit_line("abc1234", "owner/repo/extra")
        assert result == ""

    def test_short_sha_returns_empty(self) -> None:
        result = GitHubActionsProvider._build_head_commit_line("abc12", "owner/repo")
        assert result == ""

    def test_exactly_7_char_sha(self) -> None:
        result = GitHubActionsProvider._build_head_commit_line("abc1234", "owner/repo")
        assert "abc1234" in result
        assert "https://github.com/owner/repo/commit/abc1234" in result

    def test_repo_whitespace_is_trimmed(self) -> None:
        result = GitHubActionsProvider._build_head_commit_line("abc1234", " owner/repo ")
        assert "https://github.com/owner/repo/commit/abc1234" in result

    def test_repo_internal_whitespace_returns_empty(self) -> None:
        result = GitHubActionsProvider._build_head_commit_line("abc1234", "owner /repo")
        assert result == ""
