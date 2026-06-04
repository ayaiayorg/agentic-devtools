"""Tests for can_inherit_file()."""

from agentic_devtools.cli.azure_devops.review_state import FileEntry, ReviewStatus, can_inherit_file


def _make_entry(status: str = ReviewStatus.APPROVED.value) -> FileEntry:
    return FileEntry(
        threadId=100,
        commentId=200,
        folder="src",
        fileName="file.ts",
        status=status,
    )


def test_true_when_unchanged_and_valid():
    assert can_inherit_file(_make_entry(), is_unchanged=True, prior_commit_hash="abc") is True


def test_false_when_changed():
    assert can_inherit_file(_make_entry(), is_unchanged=False, prior_commit_hash="abc") is False


def test_false_when_state_invalid():
    assert (
        can_inherit_file(
            _make_entry(status=ReviewStatus.UNREVIEWED.value),
            is_unchanged=True,
            prior_commit_hash="abc",
        )
        is False
    )
