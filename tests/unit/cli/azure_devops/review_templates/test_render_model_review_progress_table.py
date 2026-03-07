"""Tests for render_model_review_progress_table function."""

from agentic_devtools.cli.azure_devops.review_state import (
    ConsolidationStatus,
    ModelVerdict,
    ReviewStatus,
    VerdictType,
)
from agentic_devtools.cli.azure_devops.review_templates import (
    render_model_review_progress_table,
)


class TestRenderModelReviewProgressTable:
    """Tests for render_model_review_progress_table."""

    def test_empty_verdicts_returns_empty(self):
        """Returns empty string when no model verdicts exist."""
        result = render_model_review_progress_table([])
        assert result == ""

    def test_single_model_awaiting(self):
        """Renders single model awaiting review."""
        verdicts = [ModelVerdict(modelId="Claude Opus 4.6", status=ReviewStatus.UNREVIEWED.value)]
        result = render_model_review_progress_table(verdicts)
        assert "### Model Review Progress" in result
        assert "| Claude Opus 4.6 | ⏳ Awaiting Review |" in result

    def test_single_model_approved(self):
        """Renders single model with approved status."""
        verdicts = [
            ModelVerdict(modelId="Claude Opus 4.6", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE)
        ]
        result = render_model_review_progress_table(verdicts)
        assert "| Claude Opus 4.6 | ✅ Approved |" in result

    def test_multi_model_mixed_statuses(self):
        """Renders multiple models with different statuses."""
        verdicts = [
            ModelVerdict(modelId="Claude Opus 4.6", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
            ModelVerdict(modelId="Gemini Pro 3.1", status=ReviewStatus.IN_PROGRESS.value),
            ModelVerdict(modelId="GPT Codex 5.3", status=ReviewStatus.UNREVIEWED.value),
        ]
        result = render_model_review_progress_table(verdicts)
        assert "| Claude Opus 4.6 | ✅ Approved |" in result
        assert "| Gemini Pro 3.1 | 🔃 In Progress |" in result
        assert "| GPT Codex 5.3 | ⏳ Awaiting Review |" in result

    def test_needs_work_status(self):
        """Renders needs-work status correctly."""
        verdicts = [
            ModelVerdict(modelId="Model A", status=ReviewStatus.NEEDS_WORK.value, verdictType=VerdictType.DISAGREE)
        ]
        result = render_model_review_progress_table(verdicts)
        assert "| Model A | 📝 Needs Work |" in result

    def test_consolidation_in_progress(self):
        """Shows consolidation underway attribution."""
        verdicts = [
            ModelVerdict(modelId="A", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
            ModelVerdict(modelId="B", status=ReviewStatus.NEEDS_WORK.value, verdictType=VerdictType.DISAGREE),
        ]
        result = render_model_review_progress_table(
            verdicts,
            consolidation_status=ConsolidationStatus.IN_PROGRESS,
            boss_model="Claude Opus 4.6",
        )
        assert "*🔃 Consolidation underway by Claude Opus 4.6*" in result

    def test_consolidation_complete(self):
        """Shows final consolidation attribution with final_verdict."""
        verdicts = [
            ModelVerdict(modelId="A", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
            ModelVerdict(modelId="B", status=ReviewStatus.NEEDS_WORK.value, verdictType=VerdictType.DISAGREE),
        ]
        result = render_model_review_progress_table(
            verdicts,
            consolidation_status=ConsolidationStatus.COMPLETE,
            boss_model="Claude Opus 4.6",
            final_verdict="📝 Needs Work",
        )
        assert "*Consolidated by Claude Opus 4.6 — Final verdict: 📝 Needs Work*" in result

    def test_consolidation_complete_default_verdict(self):
        """Uses default approved verdict when final_verdict is not passed."""
        verdicts = [
            ModelVerdict(modelId="A", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
        ]
        result = render_model_review_progress_table(
            verdicts,
            consolidation_status=ConsolidationStatus.COMPLETE,
            boss_model="Boss",
        )
        assert "*Consolidated by Boss — Final verdict: ✅ Approved*" in result

    def test_no_consolidation_note_when_not_needed(self):
        """No consolidation note when status is not_needed."""
        verdicts = [
            ModelVerdict(modelId="A", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
        ]
        result = render_model_review_progress_table(
            verdicts,
            consolidation_status=ConsolidationStatus.NOT_NEEDED,
        )
        assert "Consolidat" not in result

    def test_no_consolidation_note_when_none(self):
        """No consolidation note when consolidation_status is None."""
        verdicts = [
            ModelVerdict(modelId="A", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
        ]
        result = render_model_review_progress_table(verdicts)
        assert "Consolidat" not in result

    def test_table_header_format(self):
        """Table has correct markdown header format."""
        verdicts = [ModelVerdict(modelId="A", status=ReviewStatus.UNREVIEWED.value)]
        result = render_model_review_progress_table(verdicts)
        lines = result.split("\n")
        assert lines[0] == "### Model Review Progress"
        assert lines[2] == "| Model | Verdict |"
        assert lines[3] == "|---|---|"

    def test_all_reviewers_complete_all_agree(self):
        """All agree scenario — no consolidation attribution."""
        verdicts = [
            ModelVerdict(modelId="Claude Opus 4.6", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
            ModelVerdict(modelId="Gemini Pro 3.1", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
            ModelVerdict(modelId="GPT Codex 5.3", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE),
        ]
        result = render_model_review_progress_table(
            verdicts,
            consolidation_status=ConsolidationStatus.NOT_NEEDED,
        )
        assert "| Claude Opus 4.6 | ✅ Approved |" in result
        assert "| Gemini Pro 3.1 | ✅ Approved |" in result
        assert "| GPT Codex 5.3 | ✅ Approved |" in result
        assert "Consolidat" not in result

    def test_consolidation_in_progress_without_boss_model(self):
        """No consolidation note when boss_model is None even if status is in_progress."""
        verdicts = [ModelVerdict(modelId="A", status=ReviewStatus.APPROVED.value, verdictType=VerdictType.AGREE)]
        result = render_model_review_progress_table(
            verdicts,
            consolidation_status=ConsolidationStatus.IN_PROGRESS,
            boss_model=None,
        )
        assert "Consolidat" not in result
