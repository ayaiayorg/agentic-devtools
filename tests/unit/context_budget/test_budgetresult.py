"""Tests for BudgetResult frozen dataclass."""

import pytest

from agentic_devtools.context_budget import BudgetResult, ReductionStage


class TestBudgetResult:
    """Verify BudgetResult fields, types, and frozen immutability."""

    def test_fields_present(self):
        result = BudgetResult(
            description="desc",
            comments="comm",
            stage=ReductionStage.PASSTHROUGH,
            original_chars=8,
            final_chars=8,
            budget=100,
        )
        assert result.description == "desc"
        assert result.comments == "comm"
        assert result.stage is ReductionStage.PASSTHROUGH
        assert result.original_chars == 8
        assert result.final_chars == 8
        assert result.budget == 100

    def test_frozen_immutability(self):
        result = BudgetResult(
            description="d",
            comments="c",
            stage=ReductionStage.REDUCED,
            original_chars=2,
            final_chars=2,
            budget=50,
        )
        with pytest.raises(AttributeError):
            result.description = "changed"  # type: ignore[misc]

    def test_stage_type(self):
        result = BudgetResult(
            description="",
            comments="",
            stage=ReductionStage.TRUNCATED,
            original_chars=0,
            final_chars=0,
            budget=10,
        )
        assert isinstance(result.stage, ReductionStage)

    def test_chars_are_int(self):
        result = BudgetResult(
            description="abc",
            comments="",
            stage=ReductionStage.PASSTHROUGH,
            original_chars=3,
            final_chars=3,
            budget=100,
        )
        assert isinstance(result.original_chars, int)
        assert isinstance(result.final_chars, int)
        assert isinstance(result.budget, int)
