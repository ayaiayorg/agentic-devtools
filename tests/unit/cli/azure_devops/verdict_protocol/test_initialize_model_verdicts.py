"""Tests for initialize_model_verdicts function."""

from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    ModelVerdict,
    ReviewStatus,
)
from agentic_devtools.cli.azure_devops.verdict_protocol import initialize_model_verdicts


def _make_file_entry(**kwargs) -> FileEntry:
    defaults = {"threadId": 100, "commentId": 200, "folder": "src", "fileName": "app.py"}
    defaults.update(kwargs)
    return FileEntry(**defaults)


class TestInitializeModelVerdicts:
    """Tests for initialize_model_verdicts."""

    def test_initializes_all_models(self):
        """Creates verdict entries for all configured models."""
        fe = _make_file_entry()
        initialize_model_verdicts(fe, ["Model A", "Model B", "Model C"])
        assert len(fe.modelVerdicts) == 3
        assert fe.modelVerdicts[0].modelId == "Model A"
        assert fe.modelVerdicts[1].modelId == "Model B"
        assert fe.modelVerdicts[2].modelId == "Model C"

    def test_all_start_unreviewed(self):
        """All initialized verdicts start with unreviewed status."""
        fe = _make_file_entry()
        initialize_model_verdicts(fe, ["Model A"])
        assert fe.modelVerdicts[0].status == ReviewStatus.UNREVIEWED.value
        assert fe.modelVerdicts[0].verdictType is None

    def test_idempotent_does_not_duplicate(self):
        """Calling again with same models does not create duplicates."""
        fe = _make_file_entry()
        initialize_model_verdicts(fe, ["Model A", "Model B"])
        assert len(fe.modelVerdicts) == 2
        initialize_model_verdicts(fe, ["Model A", "Model B"])
        assert len(fe.modelVerdicts) == 2

    def test_preserves_existing_entries(self):
        """Existing entries are not overwritten."""
        existing = ModelVerdict(modelId="Model A", status=ReviewStatus.APPROVED.value, verdictType="agree")
        fe = _make_file_entry(modelVerdicts=[existing])
        initialize_model_verdicts(fe, ["Model A", "Model B"])
        assert len(fe.modelVerdicts) == 2
        assert fe.modelVerdicts[0].status == ReviewStatus.APPROVED.value  # preserved
        assert fe.modelVerdicts[1].modelId == "Model B"
        assert fe.modelVerdicts[1].status == ReviewStatus.UNREVIEWED.value

    def test_empty_models_list(self):
        """No verdicts created for empty models list."""
        fe = _make_file_entry()
        initialize_model_verdicts(fe, [])
        assert len(fe.modelVerdicts) == 0

    def test_single_model(self):
        """Single model case works correctly."""
        fe = _make_file_entry()
        initialize_model_verdicts(fe, ["Solo Model"])
        assert len(fe.modelVerdicts) == 1
        assert fe.modelVerdicts[0].modelId == "Solo Model"

    def test_duplicate_model_ids_in_input(self):
        """Duplicate model IDs in reviewer_models do not create duplicate entries."""
        fe = _make_file_entry()
        initialize_model_verdicts(fe, ["Model A", "Model A", "Model B"])
        assert len(fe.modelVerdicts) == 2
        model_ids = [mv.modelId for mv in fe.modelVerdicts]
        assert model_ids == ["Model A", "Model B"]
