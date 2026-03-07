"""Tests for evaluate_consolidation_need function."""

from agentic_devtools.cli.azure_devops.review_state import (
    ConsolidationStatus,
    FileEntry,
    ModelVerdict,
    ReviewStatus,
    VerdictType,
)
from agentic_devtools.cli.azure_devops.verdict_protocol import evaluate_consolidation_need


def _make_file_entry(**kwargs) -> FileEntry:
    defaults = {"threadId": 100, "commentId": 200, "folder": "src", "fileName": "app.py"}
    defaults.update(kwargs)
    return FileEntry(**defaults)


class TestEvaluateConsolidationNeed:
    """Tests for evaluate_consolidation_need."""

    def test_all_agree_not_needed(self):
        """Returns not_needed when all reviewers agree."""
        verdicts = [
            ModelVerdict(modelId="A", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
            ModelVerdict(modelId="B", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
        ]
        fe = _make_file_entry(modelVerdicts=verdicts)
        assert evaluate_consolidation_need(fe) == ConsolidationStatus.NOT_NEEDED

    def test_disagree_pending(self):
        """Returns pending when a reviewer disagrees."""
        verdicts = [
            ModelVerdict(modelId="A", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
            ModelVerdict(modelId="B", status=ReviewStatus.NEEDS_WORK.value, verdictType=VerdictType.DISAGREE),
        ]
        fe = _make_file_entry(modelVerdicts=verdicts)
        assert evaluate_consolidation_need(fe) == ConsolidationStatus.PENDING

    def test_supplement_pending(self):
        """Returns pending when a reviewer supplements."""
        verdicts = [
            ModelVerdict(modelId="A", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
            ModelVerdict(modelId="B", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.SUPPLEMENT),
        ]
        fe = _make_file_entry(modelVerdicts=verdicts)
        assert evaluate_consolidation_need(fe) == ConsolidationStatus.PENDING

    def test_not_all_complete_returns_not_needed(self):
        """Returns not_needed when reviewers are still pending."""
        verdicts = [
            ModelVerdict(modelId="A", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
            ModelVerdict(modelId="B", status=ReviewStatus.IN_PROGRESS.value),
        ]
        fe = _make_file_entry(modelVerdicts=verdicts)
        assert evaluate_consolidation_need(fe) == ConsolidationStatus.NOT_NEEDED

    def test_single_model_not_needed(self):
        """Single model review: no consolidation needed."""
        verdicts = [
            ModelVerdict(modelId="A", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
        ]
        fe = _make_file_entry(modelVerdicts=verdicts)
        assert evaluate_consolidation_need(fe) == ConsolidationStatus.NOT_NEEDED
