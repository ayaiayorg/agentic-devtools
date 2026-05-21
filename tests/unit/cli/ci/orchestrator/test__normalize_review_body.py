"""Tests for _normalize_review_body."""

from agentic_devtools.cli.ci.orchestrator import _normalize_review_body


class TestNormalizeReviewBody:
    """Tests for _normalize_review_body."""

    def test_replaces_typographic_apostrophe(self):
        """Typographic apostrophes are normalized to straight ones."""
        assert _normalize_review_body("wasn\u2019t") == "wasn't"

    def test_casefolds_text(self):
        """Text is case-folded for case-insensitive matching."""
        assert _normalize_review_body("Hello World") == "hello world"

    def test_combined_normalization(self):
        """Both replacements and case-folding are applied."""
        result = _normalize_review_body("I wasn\u2019t ABLE to review")
        assert result == "i wasn't able to review"
