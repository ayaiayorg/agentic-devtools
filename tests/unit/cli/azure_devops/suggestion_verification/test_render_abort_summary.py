"""Tests for render_abort_summary function."""

from agentic_devtools.cli.azure_devops.review_state import SuggestionEntry
from agentic_devtools.cli.azure_devops.suggestion_verification import (
    CATEGORY_NEEDS_REVIEW,
    CATEGORY_UNADDRESSED,
    SuggestionVerificationResult,
    render_abort_summary,
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


def _make_result(
    category: str, file_path: str = "/src/a.py", has_reply: bool = False, file_changed: bool = False
) -> SuggestionVerificationResult:
    return SuggestionVerificationResult(
        suggestion=_make_suggestion(),
        file_path=file_path,
        category=category,
        has_reply=has_reply,
        file_changed=file_changed,
        thread_status="active",
    )


class TestRenderAbortSummary:
    """Tests for render_abort_summary."""

    def test_contains_heading_and_status(self):
        unaddressed = [_make_result(CATEGORY_UNADDRESSED, "/src/a.py")]
        needs_review = [_make_result(CATEGORY_NEEDS_REVIEW, "/src/b.py", has_reply=True)]
        result = render_abort_summary(unaddressed, needs_review, "abc1234")
        assert "## Overall PR Review Summary" in result
        assert "⛔ Review Blocked" in result
        assert "Unaddressed (1)" in result
        assert "Needs Review (1)" in result

    def test_unaddressed_items_listed(self):
        unaddressed = [_make_result(CATEGORY_UNADDRESSED, "/src/a.py")]
        result = render_abort_summary(unaddressed, [], "abc1234")
        assert "/src/a.py" in result
        assert "No reply, no file changes" in result

    def test_needs_review_reason_reply(self):
        needs = [_make_result(CATEGORY_NEEDS_REVIEW, "/src/b.py", has_reply=True)]
        result = render_abort_summary([], needs, "abc1234")
        assert "reply exists" in result

    def test_needs_review_reason_file_changed(self):
        needs = [_make_result(CATEGORY_NEEDS_REVIEW, "/src/b.py", file_changed=True)]
        result = render_abort_summary([], needs, "abc1234")
        assert "file changed" in result

    def test_needs_review_reason_both(self):
        needs = [_make_result(CATEGORY_NEEDS_REVIEW, "/src/b.py", has_reply=True, file_changed=True)]
        result = render_abort_summary([], needs, "abc1234")
        assert "reply exists and file changed" in result

    def test_needs_review_reason_thread_not_found(self):
        """Thread not found produces has_reply=False, file_changed=False → unknown state reason."""
        needs = [_make_result(CATEGORY_NEEDS_REVIEW, "/src/b.py", has_reply=False, file_changed=False)]
        result = render_abort_summary([], needs, "abc1234")
        assert "thread not found (unknown state)" in result

    def test_no_needs_review_shows_none(self):
        unaddressed = [_make_result(CATEGORY_UNADDRESSED)]
        result = render_abort_summary(unaddressed, [], "abc1234")
        assert "*(none)*" in result

    def test_custom_model_info(self):
        result = render_abort_summary(
            [_make_result(CATEGORY_UNADDRESSED)],
            [],
            "abc1234",
            model_name="Claude 3.5",
            model_icon="🧠",
        )
        assert "🧠" in result
        assert "Claude 3.5" in result
