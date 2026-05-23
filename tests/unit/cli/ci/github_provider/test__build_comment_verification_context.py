"""Tests for _build_comment_verification_context()."""

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.models import ReviewCommentInfo


class TestBuildCommentVerificationContext:
    """Tests for _build_comment_verification_context edge cases."""

    def test_truncates_file_diff_exceeding_4000_chars(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        long_line = "+" + "a" * 5000
        full_diff = f"diff --git a/src/foo.py b/src/foo.py\n{long_line}\n"
        comment = ReviewCommentInfo(
            id=101,
            path="src/foo.py",
            body="fix",
            html_url="http://url",
            diff_hunk="@@ original @@",
        )

        result = provider._build_comment_verification_context(comment, full_diff)

        assert len(result) == 4000

    def test_no_path_returns_full_diff(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        comment = ReviewCommentInfo(
            id=101,
            path="",
            body="fix",
            html_url="http://url",
            diff_hunk="@@ hunk @@",
        )

        result = provider._build_comment_verification_context(comment, "diff --git a/x b/x\n+new")

        assert result == "diff --git a/x b/x\n+new"

    def test_no_path_no_diff_returns_diff_hunk(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        comment = ReviewCommentInfo(
            id=101,
            path="",
            body="fix",
            html_url="http://url",
            diff_hunk="@@ fallback @@",
        )

        result = provider._build_comment_verification_context(comment, "")

        assert result == "@@ fallback @@"
