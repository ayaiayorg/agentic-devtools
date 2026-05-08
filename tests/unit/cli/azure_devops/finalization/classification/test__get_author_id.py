"""Tests for _get_author_id function."""

from agentic_devtools.cli.azure_devops.finalization.classification import _get_author_id


class TestGetAuthorId:
    """Tests for _get_author_id function."""

    def test_extracts_author_id(self):
        """Should extract author ID from comment dict."""
        comment = {"author": {"id": "user-123"}}
        assert _get_author_id(comment) == "user-123"

    def test_returns_none_when_no_author(self):
        """Should return None when comment has no author key."""
        comment = {}
        assert _get_author_id(comment) is None

    def test_returns_none_when_author_has_no_id(self):
        """Should return None when author dict has no id key."""
        comment = {"author": {"name": "John"}}
        assert _get_author_id(comment) is None
