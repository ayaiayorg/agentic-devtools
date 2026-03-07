"""Tests for has_unaddressed helper."""

from agentic_devtools.cli.azure_devops.review_state import SuggestionEntry
from agentic_devtools.cli.azure_devops.suggestion_verification import (
    CATEGORY_NEEDS_REVIEW,
    CATEGORY_UNADDRESSED,
    SuggestionVerificationResult,
    has_unaddressed,
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


def _make_result(category: str) -> SuggestionVerificationResult:
    return SuggestionVerificationResult(
        suggestion=_make_suggestion(),
        file_path="/src/a.py",
        category=category,
        has_reply=False,
        file_changed=False,
        thread_status="active",
    )


class TestHasUnaddressed:
    """Tests for the has_unaddressed helper."""

    def test_empty_list(self):
        assert has_unaddressed([]) is False

    def test_all_needs_review(self):
        results = [_make_result(CATEGORY_NEEDS_REVIEW)]
        assert has_unaddressed(results) is False

    def test_any_unaddressed_returns_true(self):
        results = [
            _make_result(CATEGORY_NEEDS_REVIEW),
            _make_result(CATEGORY_UNADDRESSED),
        ]
        assert has_unaddressed(results) is True
