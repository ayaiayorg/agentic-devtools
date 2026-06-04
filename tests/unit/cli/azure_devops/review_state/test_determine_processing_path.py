"""Tests for determine_processing_path()."""

from agentic_devtools.cli.azure_devops.review_state import (
    PROCESSING_PATH_INHERITED,
    PROCESSING_PATH_REVIEWED,
    PROCESSING_PATH_REVIEWED_NO_PRIOR,
    FileEntry,
    ModelVerdict,
    ReviewStatus,
    determine_processing_path,
)


def _make_entry(
    status: str = ReviewStatus.APPROVED.value,
    model_verdicts: list | None = None,
) -> FileEntry:
    entry = FileEntry(
        threadId=100,
        commentId=200,
        folder="src",
        fileName="file.ts",
        status=status,
    )
    if model_verdicts is not None:
        entry.modelVerdicts = model_verdicts
    return entry


def test_changed_file_returns_reviewed():
    assert (
        determine_processing_path(_make_entry(), is_unchanged=False, prior_commit_hash="abc", has_model_verdicts=False)
        == PROCESSING_PATH_REVIEWED
    )


def test_unchanged_no_prior_entry_returns_reviewed_no_prior():
    assert (
        determine_processing_path(None, is_unchanged=True, prior_commit_hash="abc", has_model_verdicts=False)
        == PROCESSING_PATH_REVIEWED_NO_PRIOR
    )


def test_unchanged_valid_prior_returns_inherited():
    assert (
        determine_processing_path(_make_entry(), is_unchanged=True, prior_commit_hash="abc", has_model_verdicts=False)
        == PROCESSING_PATH_INHERITED
    )


def test_unchanged_invalid_prior_returns_reviewed_no_prior():
    assert (
        determine_processing_path(
            _make_entry(status=ReviewStatus.UNREVIEWED.value),
            is_unchanged=True,
            prior_commit_hash="abc",
            has_model_verdicts=False,
        )
        == PROCESSING_PATH_REVIEWED_NO_PRIOR
    )


def test_unchanged_multi_model_valid_returns_inherited():
    verdicts = [ModelVerdict(modelId="gpt-4", status=ReviewStatus.APPROVED.value)]
    assert (
        determine_processing_path(_make_entry(model_verdicts=verdicts), True, "abc", True) == PROCESSING_PATH_INHERITED
    )


def test_unchanged_multi_model_incomplete_returns_reviewed_no_prior():
    verdicts = [ModelVerdict(modelId="gpt-4", status=ReviewStatus.UNREVIEWED.value)]
    assert (
        determine_processing_path(_make_entry(model_verdicts=verdicts), True, "abc", True)
        == PROCESSING_PATH_REVIEWED_NO_PRIOR
    )
