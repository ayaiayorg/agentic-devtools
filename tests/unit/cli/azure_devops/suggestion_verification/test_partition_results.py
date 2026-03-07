"""Tests for partition_results helper."""

from agentic_devtools.cli.azure_devops.review_state import SuggestionEntry
from agentic_devtools.cli.azure_devops.suggestion_verification import (
    CATEGORY_NEEDS_REVIEW,
    CATEGORY_UNADDRESSED,
    SuggestionVerificationResult,
    partition_results,
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


def _make_result(category: str, file_path: str = "/src/a.py") -> SuggestionVerificationResult:
    return SuggestionVerificationResult(
        suggestion=_make_suggestion(),
        file_path=file_path,
        category=category,
        has_reply=False,
        file_changed=False,
        thread_status="active",
    )


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
