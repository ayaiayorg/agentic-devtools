"""Tests for SuggestionVerificationResult dataclass."""

from agentic_devtools.cli.azure_devops.review_state import SuggestionEntry
from agentic_devtools.cli.azure_devops.suggestion_verification import (
    CATEGORY_NEEDS_REVIEW,
    CATEGORY_UNADDRESSED,
    SuggestionVerificationResult,
)


def _make_suggestion(thread_id: int = 100) -> SuggestionEntry:
    return SuggestionEntry(
        threadId=thread_id,
        commentId=200,
        line=10,
        endLine=20,
        severity="high",
        outOfScope=False,
        linkText="lines 10 - 20",
        content="Missing null check",
    )


class TestSuggestionVerificationResult:
    """Tests for SuggestionVerificationResult dataclass."""

    def test_creation(self):
        """Test basic creation."""
        sug = _make_suggestion()
        r = SuggestionVerificationResult(
            suggestion=sug,
            file_path="/src/app.py",
            category=CATEGORY_UNADDRESSED,
            has_reply=False,
            file_changed=False,
            thread_status="active",
        )
        assert r.suggestion is sug
        assert r.file_path == "/src/app.py"
        assert r.category == CATEGORY_UNADDRESSED
        assert r.has_reply is False
        assert r.file_changed is False
        assert r.thread_status == "active"

    def test_needs_review_category(self):
        """Test needs_review category."""
        sug = _make_suggestion()
        r = SuggestionVerificationResult(
            suggestion=sug,
            file_path="/src/app.py",
            category=CATEGORY_NEEDS_REVIEW,
            has_reply=True,
            file_changed=True,
            thread_status="closed",
        )
        assert r.category == CATEGORY_NEEDS_REVIEW
        assert r.has_reply is True
        assert r.file_changed is True
        assert r.thread_status == "closed"

    def test_category_constants(self):
        """Test category constant values."""
        assert CATEGORY_UNADDRESSED == "unaddressed"
        assert CATEGORY_NEEDS_REVIEW == "needs_review"
