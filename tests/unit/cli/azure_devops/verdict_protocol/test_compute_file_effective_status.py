"""Tests for compute_file_effective_status function."""

from agentic_devtools.cli.azure_devops.review_state import (
    ConsolidationStatus,
    FileEntry,
    ModelVerdict,
    ReviewStatus,
    VerdictType,
)
from agentic_devtools.cli.azure_devops.verdict_protocol import compute_file_effective_status


def _make_file_entry(**kwargs) -> FileEntry:
    defaults = {"threadId": 100, "commentId": 200, "folder": "src", "fileName": "app.py"}
    defaults.update(kwargs)
    return FileEntry(**defaults)


class TestComputeFileEffectiveStatus:
    """Tests for compute_file_effective_status."""

    def test_no_model_verdicts_returns_file_status(self):
        """Returns the file's current status when no model verdicts exist."""
        fe = _make_file_entry(status=ReviewStatus.UNREVIEWED.value)
        assert compute_file_effective_status(fe) == ReviewStatus.UNREVIEWED.value

    def test_all_reviewers_pending_returns_in_progress(self):
        """Returns in-progress when any reviewer is still pending."""
        verdicts = [
            ModelVerdict(modelId="A", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
            ModelVerdict(modelId="B", status=ReviewStatus.IN_PROGRESS.value),
        ]
        fe = _make_file_entry(modelVerdicts=verdicts)
        assert compute_file_effective_status(fe) == ReviewStatus.IN_PROGRESS.value

    def test_all_agree_returns_primary_status(self):
        """Returns primary reviewer's status when all agree."""
        verdicts = [
            ModelVerdict(modelId="A", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
            ModelVerdict(modelId="B", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
        ]
        fe = _make_file_entry(modelVerdicts=verdicts)
        assert compute_file_effective_status(fe) == ReviewStatus.APPROVED.value

    def test_all_agree_needs_work(self):
        """Returns needs-work when all agree with needs-work."""
        verdicts = [
            ModelVerdict(modelId="A", status=ReviewStatus.NEEDS_WORK.value, verdictType=VerdictType.AGREE),
            ModelVerdict(modelId="B", status=ReviewStatus.NEEDS_WORK.value, verdictType=VerdictType.AGREE),
        ]
        fe = _make_file_entry(modelVerdicts=verdicts)
        assert compute_file_effective_status(fe) == ReviewStatus.NEEDS_WORK.value

    def test_disagreement_pending_consolidation_returns_in_progress(self):
        """Returns in-progress when consolidation is pending."""
        verdicts = [
            ModelVerdict(modelId="A", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
            ModelVerdict(modelId="B", status=ReviewStatus.NEEDS_WORK.value, verdictType=VerdictType.DISAGREE),
        ]
        fe = _make_file_entry(
            modelVerdicts=verdicts,
            consolidationStatus=ConsolidationStatus.PENDING,
        )
        assert compute_file_effective_status(fe) == ReviewStatus.IN_PROGRESS.value

    def test_consolidation_complete_returns_file_status(self):
        """Returns file status when consolidation is complete."""
        verdicts = [
            ModelVerdict(modelId="A", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
            ModelVerdict(modelId="B", status=ReviewStatus.NEEDS_WORK.value, verdictType=VerdictType.DISAGREE),
        ]
        fe = _make_file_entry(
            modelVerdicts=verdicts,
            consolidationStatus=ConsolidationStatus.COMPLETE,
            status=ReviewStatus.APPROVED.value,
        )
        assert compute_file_effective_status(fe) == ReviewStatus.APPROVED.value

    def test_consolidation_in_progress_returns_in_progress(self):
        """Returns in-progress when consolidation is running."""
        verdicts = [
            ModelVerdict(modelId="A", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
            ModelVerdict(modelId="B", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.SUPPLEMENT),
        ]
        fe = _make_file_entry(
            modelVerdicts=verdicts,
            consolidationStatus=ConsolidationStatus.IN_PROGRESS,
        )
        assert compute_file_effective_status(fe) == ReviewStatus.IN_PROGRESS.value

    def test_single_model_approved(self):
        """Single-model case: returns the single model's status."""
        verdicts = [
            ModelVerdict(modelId="A", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
        ]
        fe = _make_file_entry(modelVerdicts=verdicts)
        assert compute_file_effective_status(fe) == ReviewStatus.APPROVED.value
