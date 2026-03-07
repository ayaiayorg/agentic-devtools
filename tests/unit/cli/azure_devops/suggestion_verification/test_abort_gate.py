"""Tests for abort gate logic: has_unaddressed, partition_results, render functions."""

from agentic_devtools.cli.azure_devops.review_state import SuggestionEntry
from agentic_devtools.cli.azure_devops.suggestion_verification import (
    CATEGORY_NEEDS_REVIEW,
    CATEGORY_UNADDRESSED,
    SuggestionVerificationResult,
    has_unaddressed,
    partition_results,
    render_abort_summary,
    render_unaddressed_thread_comment,
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


class TestPartitionResults:
    """Tests for the partition_results helper."""

    def test_empty(self):
        unaddr, needs = partition_results([])
        assert unaddr == []
        assert needs == []

    def test_mixed(self):
        r1 = _make_result(CATEGORY_UNADDRESSED, "/a.py")
        r2 = _make_result(CATEGORY_NEEDS_REVIEW, "/b.py")
        r3 = _make_result(CATEGORY_UNADDRESSED, "/c.py")
        unaddr, needs = partition_results([r1, r2, r3])
        assert len(unaddr) == 2
        assert len(needs) == 1
        assert unaddr[0].file_path == "/a.py"
        assert unaddr[1].file_path == "/c.py"
        assert needs[0].file_path == "/b.py"


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


class TestRenderUnaddressedThreadComment:
    """Tests for render_unaddressed_thread_comment."""

    def test_contains_hash(self):
        result = render_unaddressed_thread_comment("abc1234")
        assert "abc1234" in result
        assert "⚠️ **Unaddressed Suggestion**" in result

    def test_contains_instructions(self):
        result = render_unaddressed_thread_comment("abc1234")
        assert "Make the suggested changes" in result
        assert "Reply to this thread" in result
