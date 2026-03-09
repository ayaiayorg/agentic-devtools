"""Tests for _load_amendment_replies stub."""

from agentic_devtools.cli.review.consolidate import _load_amendment_replies


class TestLoadAmendmentReplies:
    """Tests for _load_amendment_replies stub."""

    def test_returns_empty_dict(self):
        """Stub returns empty dict."""
        result = _load_amendment_replies(pr_id=123)
        assert result == {}
