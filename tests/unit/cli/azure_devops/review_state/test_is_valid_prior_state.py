"""Tests for is_valid_prior_state()."""

from agentic_devtools.cli.azure_devops.review_state import FileEntry, ReviewStatus, is_valid_prior_state


def _make_entry(
    status: str = ReviewStatus.APPROVED.value,
    thread_id: int = 100,
    comment_id: int = 200,
    folder: str = "src",
) -> FileEntry:
    return FileEntry(
        threadId=thread_id,
        commentId=comment_id,
        folder=folder,
        fileName="file.ts",
        status=status,
    )


def test_valid_approved_entry():
    assert is_valid_prior_state(_make_entry(status=ReviewStatus.APPROVED.value), "abc123") is True


def test_valid_needs_work_entry():
    assert is_valid_prior_state(_make_entry(status=ReviewStatus.NEEDS_WORK.value), "abc123") is True


def test_invalid_when_status_not_terminal():
    assert is_valid_prior_state(_make_entry(status=ReviewStatus.UNREVIEWED.value), "abc123") is False


def test_invalid_when_no_commit_hash():
    assert is_valid_prior_state(_make_entry(), None) is False


def test_invalid_when_empty_commit_hash():
    assert is_valid_prior_state(_make_entry(), "") is False


def test_invalid_when_no_thread_id():
    assert is_valid_prior_state(_make_entry(thread_id=0), "abc") is False


def test_invalid_when_no_comment_id():
    assert is_valid_prior_state(_make_entry(comment_id=0), "abc") is False


def test_invalid_when_no_folder():
    assert is_valid_prior_state(_make_entry(folder=""), "abc") is False
