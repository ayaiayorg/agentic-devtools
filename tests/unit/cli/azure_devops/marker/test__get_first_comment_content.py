"""Tests for _get_first_comment_content helper function."""

from agentic_devtools.cli.azure_devops.marker import _get_first_comment_content


class TestGetFirstCommentContent:
    """Tests for _get_first_comment_content."""

    def test_returns_content_from_first_comment(self):
        """Returns the content of the first comment when present."""
        thread = {"comments": [{"content": "Hello world"}]}
        assert _get_first_comment_content(thread) == "Hello world"

    def test_returns_empty_when_thread_is_deleted(self):
        """Returns empty string when the thread is deleted."""
        thread = {"isDeleted": True, "comments": [{"content": "Hello"}]}
        assert _get_first_comment_content(thread) == ""

    def test_returns_empty_when_first_comment_is_deleted(self):
        """Returns empty string when the first comment is deleted."""
        thread = {"comments": [{"isDeleted": True, "content": "Hello"}]}
        assert _get_first_comment_content(thread) == ""

    def test_returns_empty_when_no_comments_key(self):
        """Returns empty string when thread has no comments key."""
        thread = {"id": 1}
        assert _get_first_comment_content(thread) == ""

    def test_returns_empty_when_comments_is_empty(self):
        """Returns empty string when comments list is empty."""
        thread = {"comments": []}
        assert _get_first_comment_content(thread) == ""

    def test_returns_empty_when_first_comment_is_not_dict(self):
        """Returns empty string when first comment is not a dict."""
        thread = {"comments": ["not a dict"]}
        assert _get_first_comment_content(thread) == ""

    def test_returns_empty_when_content_is_none(self):
        """Returns empty string when content field is None."""
        thread = {"comments": [{"content": None}]}
        assert _get_first_comment_content(thread) == ""

    def test_returns_empty_when_content_key_missing(self):
        """Returns empty string when content key is absent."""
        thread = {"comments": [{}]}
        assert _get_first_comment_content(thread) == ""
