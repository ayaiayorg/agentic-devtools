"""Tests for ReductionStage enum."""

from agentic_devtools.context_budget import ReductionStage


class TestReductionStage:
    """Verify ReductionStage enum members and values."""

    def test_has_passthrough_member(self):
        assert hasattr(ReductionStage, "PASSTHROUGH")

    def test_has_reduced_member(self):
        assert hasattr(ReductionStage, "REDUCED")

    def test_has_truncated_member(self):
        assert hasattr(ReductionStage, "TRUNCATED")

    def test_has_summary_only_member(self):
        assert hasattr(ReductionStage, "SUMMARY_ONLY")

    def test_passthrough_value(self):
        assert ReductionStage.PASSTHROUGH.value == "passthrough"

    def test_reduced_value(self):
        assert ReductionStage.REDUCED.value == "reduced"

    def test_truncated_value(self):
        assert ReductionStage.TRUNCATED.value == "truncated"

    def test_summary_only_value(self):
        assert ReductionStage.SUMMARY_ONLY.value == "summary_only"

    def test_member_count(self):
        assert len(ReductionStage) == 4
