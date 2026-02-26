"""Tests for build_discussion_url function."""

from agentic_devtools.cli.azure_devops.review_templates import build_discussion_url


class TestBuildDiscussionUrl:
    """Tests for build_discussion_url."""

    def test_returns_url_with_both_ids(self):
        """Test that the URL contains discussionId and commentId."""
        base = "https://dev.azure.com/org/proj/_git/repo/pullRequest/123"
        result = build_discussion_url(base, thread_id=456, comment_id=789)
        assert result == f"{base}?discussionId=456&commentId=789"

    def test_includes_discussion_id(self):
        """Test that discussionId query param is present."""
        base = "https://dev.azure.com/org/proj/_git/repo/pullRequest/1"
        result = build_discussion_url(base, thread_id=10, comment_id=20)
        assert "discussionId=10" in result

    def test_includes_comment_id(self):
        """Test that commentId query param is present."""
        base = "https://dev.azure.com/org/proj/_git/repo/pullRequest/1"
        result = build_discussion_url(base, thread_id=10, comment_id=20)
        assert "commentId=20" in result

    def test_base_url_preserved(self):
        """Test that the base URL is preserved as a prefix."""
        base = "https://dev.azure.com/myorg/myproj/_git/myrepo/pullRequest/999"
        result = build_discussion_url(base, thread_id=1, comment_id=2)
        assert result.startswith(base)

    def test_uses_question_mark_separator(self):
        """Test that a ? separates the base URL from query params."""
        base = "https://dev.azure.com/org/proj/_git/repo/pullRequest/5"
        result = build_discussion_url(base, thread_id=1, comment_id=2)
        assert "?" in result
