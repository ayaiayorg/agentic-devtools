"""Tests for FileEntry multi-model verdict methods."""

from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    ModelVerdict,
)


def _make_file_entry(**kwargs) -> FileEntry:
    """Create a FileEntry with test defaults."""
    defaults = {
        "threadId": 100,
        "commentId": 200,
        "folder": "src",
        "fileName": "app.py",
    }
    defaults.update(kwargs)
    return FileEntry(**defaults)


class TestFileEntryMultiModel:
    """Tests for FileEntry multi-model verdict methods."""

    def test_get_model_verdict_found(self):
        """Returns the matching ModelVerdict by modelId."""
        mv = ModelVerdict(modelId="Claude Opus 4.6", status="approved", verdictType="agree")
        fe = _make_file_entry(modelVerdicts=[mv])
        assert fe.get_model_verdict("Claude Opus 4.6") is mv

    def test_get_model_verdict_not_found(self):
        """Returns None when no matching modelId exists."""
        fe = _make_file_entry(modelVerdicts=[])
        assert fe.get_model_verdict("Missing Model") is None

    def test_all_reviewers_complete_true(self):
        """Returns True when all model verdicts are terminal."""
        verdicts = [
            ModelVerdict(modelId="A", status="approved", verdictType="agree"),
            ModelVerdict(modelId="B", status="needs-work", verdictType="disagree"),
        ]
        fe = _make_file_entry(modelVerdicts=verdicts)
        assert fe.all_reviewers_complete() is True

    def test_all_reviewers_complete_false(self):
        """Returns False when any model is still pending."""
        verdicts = [
            ModelVerdict(modelId="A", status="approved", verdictType="agree"),
            ModelVerdict(modelId="B", status="in-progress"),
        ]
        fe = _make_file_entry(modelVerdicts=verdicts)
        assert fe.all_reviewers_complete() is False

    def test_all_reviewers_complete_empty(self):
        """Returns False when no model verdicts exist."""
        fe = _make_file_entry(modelVerdicts=[])
        assert fe.all_reviewers_complete() is False

    def test_has_disagreements_true(self):
        """Returns True when any model has supplement or disagree verdict."""
        verdicts = [
            ModelVerdict(modelId="A", status="approved", verdictType="agree"),
            ModelVerdict(modelId="B", status="needs-work", verdictType="disagree"),
        ]
        fe = _make_file_entry(modelVerdicts=verdicts)
        assert fe.has_disagreements() is True

    def test_has_disagreements_supplement(self):
        """Returns True when a model has supplement verdict."""
        verdicts = [
            ModelVerdict(modelId="A", status="approved", verdictType="agree"),
            ModelVerdict(modelId="B", status="approved", verdictType="supplement"),
        ]
        fe = _make_file_entry(modelVerdicts=verdicts)
        assert fe.has_disagreements() is True

    def test_has_disagreements_false(self):
        """Returns False when all models agree."""
        verdicts = [
            ModelVerdict(modelId="A", status="approved", verdictType="agree"),
            ModelVerdict(modelId="B", status="approved", verdictType="agree"),
        ]
        fe = _make_file_entry(modelVerdicts=verdicts)
        assert fe.has_disagreements() is False

    def test_needs_consolidation_true(self):
        """Returns True when all reviewers done and disagreements exist."""
        verdicts = [
            ModelVerdict(modelId="A", status="approved", verdictType="agree"),
            ModelVerdict(modelId="B", status="needs-work", verdictType="disagree"),
        ]
        fe = _make_file_entry(modelVerdicts=verdicts)
        assert fe.needs_consolidation() is True

    def test_needs_consolidation_false_all_agree(self):
        """Returns False when all agree."""
        verdicts = [
            ModelVerdict(modelId="A", status="approved", verdictType="agree"),
            ModelVerdict(modelId="B", status="approved", verdictType="agree"),
        ]
        fe = _make_file_entry(modelVerdicts=verdicts)
        assert fe.needs_consolidation() is False

    def test_needs_consolidation_false_not_complete(self):
        """Returns False when not all reviewers are complete."""
        verdicts = [
            ModelVerdict(modelId="A", status="approved", verdictType="agree"),
            ModelVerdict(modelId="B", status="unreviewed"),
        ]
        fe = _make_file_entry(modelVerdicts=verdicts)
        assert fe.needs_consolidation() is False

    def test_to_dict_includes_model_verdicts(self):
        """Model verdicts are included in serialization when non-empty."""
        mv = ModelVerdict(modelId="A", status="approved", verdictType="agree")
        fe = _make_file_entry(modelVerdicts=[mv], consolidationStatus="not_needed")
        d = fe.to_dict()
        assert "modelVerdicts" in d
        assert len(d["modelVerdicts"]) == 1
        assert d["modelVerdicts"][0]["modelId"] == "A"
        assert d["consolidationStatus"] == "not_needed"

    def test_to_dict_omits_empty_model_verdicts(self):
        """Model verdicts key is omitted when list is empty."""
        fe = _make_file_entry()
        d = fe.to_dict()
        assert "modelVerdicts" not in d
        assert "consolidationStatus" not in d

    def test_from_dict_with_model_verdicts(self):
        """Deserialization correctly reads model verdicts."""
        data = {
            "threadId": 100,
            "commentId": 200,
            "folder": "src",
            "fileName": "app.py",
            "modelVerdicts": [
                {"modelId": "A", "status": "approved", "verdictType": "agree"},
                {"modelId": "B", "status": "needs-work", "verdictType": "disagree"},
            ],
            "consolidationStatus": "pending",
        }
        fe = FileEntry.from_dict(data)
        assert len(fe.modelVerdicts) == 2
        assert fe.modelVerdicts[0].modelId == "A"
        assert fe.modelVerdicts[1].verdictType == "disagree"
        assert fe.consolidationStatus == "pending"

    def test_from_dict_without_model_verdicts(self):
        """Backward compatibility: missing modelVerdicts defaults to empty list."""
        data = {
            "threadId": 100,
            "commentId": 200,
            "folder": "src",
            "fileName": "app.py",
        }
        fe = FileEntry.from_dict(data)
        assert fe.modelVerdicts == []
        assert fe.consolidationStatus is None
