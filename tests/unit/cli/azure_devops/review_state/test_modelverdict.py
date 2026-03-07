"""Tests for ModelVerdict dataclass."""

from agentic_devtools.cli.azure_devops.review_state import (
    ModelVerdict,
    ReviewStatus,
)


class TestModelVerdict:
    """Tests for ModelVerdict dataclass."""

    def test_creation_with_defaults(self):
        """Test creation with minimal args and defaults."""
        mv = ModelVerdict(modelId="Claude Opus 4.6")
        assert mv.modelId == "Claude Opus 4.6"
        assert mv.status == ReviewStatus.UNREVIEWED.value
        assert mv.verdictType is None

    def test_creation_with_all_fields(self):
        """Test creation with all fields specified."""
        mv = ModelVerdict(
            modelId="Gemini Pro 3.1",
            status=ReviewStatus.APPROVED.value,
            verdictType="agree",
        )
        assert mv.modelId == "Gemini Pro 3.1"
        assert mv.status == ReviewStatus.APPROVED.value
        assert mv.verdictType == "agree"

    def test_to_dict(self):
        """Test serialization."""
        mv = ModelVerdict(
            modelId="Claude Opus 4.6",
            status=ReviewStatus.NEEDS_WORK.value,
            verdictType="disagree",
        )
        d = mv.to_dict()
        assert d == {
            "modelId": "Claude Opus 4.6",
            "status": "needs-work",
            "verdictType": "disagree",
        }

    def test_to_dict_none_verdict(self):
        """Test serialization with None verdictType."""
        mv = ModelVerdict(modelId="Model A")
        d = mv.to_dict()
        assert d["verdictType"] is None

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "modelId": "GPT Codex 5.3",
            "status": "approved",
            "verdictType": "supplement",
        }
        mv = ModelVerdict.from_dict(data)
        assert mv.modelId == "GPT Codex 5.3"
        assert mv.status == "approved"
        assert mv.verdictType == "supplement"

    def test_from_dict_defaults(self):
        """Test deserialization with missing optional fields."""
        data = {"modelId": "Model X"}
        mv = ModelVerdict.from_dict(data)
        assert mv.status == ReviewStatus.UNREVIEWED.value
        assert mv.verdictType is None

    def test_roundtrip(self):
        """Test serialize/deserialize roundtrip."""
        original = ModelVerdict(
            modelId="Claude Opus 4.6",
            status=ReviewStatus.APPROVED.value,
            verdictType="agree",
        )
        restored = ModelVerdict.from_dict(original.to_dict())
        assert restored.modelId == original.modelId
        assert restored.status == original.status
        assert restored.verdictType == original.verdictType
