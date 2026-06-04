"""Tests for can_inherit_multi_model()."""

from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    ModelVerdict,
    ReviewStatus,
    can_inherit_multi_model,
)


def _make_entry(model_verdicts: list | None = None) -> FileEntry:
    entry = FileEntry(
        threadId=100,
        commentId=200,
        folder="src",
        fileName="file.ts",
        status=ReviewStatus.APPROVED.value,
    )
    if model_verdicts is not None:
        entry.modelVerdicts = model_verdicts
    return entry


def test_true_when_no_model_verdicts():
    assert can_inherit_multi_model(_make_entry(), is_unchanged=True, prior_commit_hash="abc") is True


def test_true_when_all_verdicts_terminal():
    verdicts = [
        ModelVerdict(modelId="gpt-4", status=ReviewStatus.APPROVED.value),
        ModelVerdict(modelId="sonnet", status=ReviewStatus.NEEDS_WORK.value),
    ]
    assert can_inherit_multi_model(_make_entry(verdicts), is_unchanged=True, prior_commit_hash="abc") is True


def test_false_when_verdict_not_terminal():
    verdicts = [
        ModelVerdict(modelId="gpt-4", status=ReviewStatus.APPROVED.value),
        ModelVerdict(modelId="sonnet", status=ReviewStatus.UNREVIEWED.value),
    ]
    assert can_inherit_multi_model(_make_entry(verdicts), is_unchanged=True, prior_commit_hash="abc") is False


def test_false_when_file_changed():
    verdicts = [ModelVerdict(modelId="gpt-4", status=ReviewStatus.APPROVED.value)]
    assert can_inherit_multi_model(_make_entry(verdicts), is_unchanged=False, prior_commit_hash="abc") is False
