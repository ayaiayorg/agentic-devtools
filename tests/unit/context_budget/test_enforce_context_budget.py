"""Tests for enforce_context_budget() — all stages and edge cases."""

import pytest

from agentic_devtools.context_budget import (
    ContextBudgetError,
    ReductionStage,
    enforce_context_budget,
)


class TestEnforceContextBudgetPassthrough:
    """Passthrough path: content within budget."""

    def test_below_budget_returns_unchanged(self):
        desc = "hello"
        comm = "world"
        result = enforce_context_budget(desc, comm, budget=100)
        assert result.description is desc
        assert result.comments is comm
        assert result.stage is ReductionStage.PASSTHROUGH

    def test_exactly_at_budget_returns_passthrough(self):
        desc = "a" * 50
        comm = "b" * 50
        result = enforce_context_budget(desc, comm, budget=100)
        assert result.stage is ReductionStage.PASSTHROUGH
        assert result.original_chars == 100
        assert result.final_chars == 100

    def test_passthrough_identity(self):
        """Below budget → objects are the exact same Python objects (identity)."""
        desc = "some description"
        comm = "some comments"
        result = enforce_context_budget(desc, comm, budget=1000)
        assert result.description is desc
        assert result.comments is comm


class TestEnforceContextBudgetReduced:
    """Reduced path: markdown stripping brings content within budget."""

    def test_markdown_stripped_reduces_below_budget(self):
        # Construct a description that's over budget with markdown but under
        # budget once markdown is stripped
        desc = "## " + "x" * 90
        comm = ""
        # Original: 2 + 1 + 90 = 93 chars; stripped: ~90 chars
        result = enforce_context_budget(desc, comm, budget=91)
        assert result.stage is ReductionStage.REDUCED
        assert result.final_chars <= 91

    def test_determinism_identical_input_identical_output(self):
        desc = "## **bold** heading\n\n\n" + "x" * 100
        comm = "![img](url)" + "y" * 50
        r1 = enforce_context_budget(desc, comm, budget=160)
        r2 = enforce_context_budget(desc, comm, budget=160)
        assert r1.description == r2.description
        assert r1.comments == r2.comments
        assert r1.stage == r2.stage


class TestEnforceContextBudgetTruncated:
    """Truncated path: reduction alone is not enough."""

    def test_hard_truncation_applied(self):
        desc = "word " * 5000  # 25000 chars
        comm = "more " * 5000  # 25000 chars
        result = enforce_context_budget(desc, comm, budget=500)
        assert result.stage is ReductionStage.TRUNCATED
        assert result.final_chars <= 500

    def test_truncation_marker_present(self):
        desc = "text " * 5000
        result = enforce_context_budget(desc, "", budget=100)
        assert "[…truncated]" in result.description


class TestEnforceContextBudgetSummaryOnly:
    """Summary-only path: comments dropped, description truncated.

    The summary-only stage is reached when truncated combined content fails
    ``validate_content_shape()``.  Since the ``[…truncated]`` marker itself
    contains alpha characters, this is a very narrow edge case in practice.
    These tests verify both the common TRUNCATED outcome and exercise the
    summary-only path directly.
    """

    def test_large_desc_and_comments_truncated_stage(self):
        """When both desc and comments are huge, TRUNCATED handles it."""
        desc = "x" * 100
        comm = "y" * 100
        result = enforce_context_budget(desc, comm, budget=50)
        assert result.comments == ""
        assert result.stage is ReductionStage.TRUNCATED
        assert result.final_chars <= 50

    def test_input_only_images_whitespace_falls_to_truncated_or_summary(self):
        """Content that is mostly images/whitespace after reduction."""
        desc = "![img](url) " * 50 + "abc"  # after stripping, very small
        comm = "![img2](url2) " * 50
        result = enforce_context_budget(desc, comm, budget=20)
        assert result.stage in (
            ReductionStage.TRUNCATED,
            ReductionStage.SUMMARY_ONLY,
            ReductionStage.REDUCED,
        )

    def test_summary_only_via_mocked_validation(self):
        """Directly exercise the summary-only return path.

        Patch ``validate_content_shape`` to reject the truncated-combined
        output (stage 3) but accept the description-only output (stage 4).
        """
        from unittest.mock import patch

        desc = "abc valid description"
        comm = "z" * 200
        call_count = 0

        def _fake_validate(text: str) -> bool:
            nonlocal call_count
            call_count += 1
            # First call is from stage 3 (truncated combined) → reject
            if call_count == 1:
                return False
            # Second call is from stage 4 (summary-only desc) → accept
            return True

        with patch("agentic_devtools.context_budget.validate_content_shape", side_effect=_fake_validate):
            result = enforce_context_budget(desc, comm, budget=30)

        assert result.stage is ReductionStage.SUMMARY_ONLY
        assert result.comments == ""


class TestEnforceContextBudgetErrors:
    """Error paths: budget ≤ 0, permanent failure."""

    def test_zero_budget_raises(self):
        with pytest.raises(ContextBudgetError, match="positive integer"):
            enforce_context_budget("hello", "world", budget=0)

    def test_negative_budget_raises(self):
        with pytest.raises(ContextBudgetError, match="positive integer"):
            enforce_context_budget("hello", "world", budget=-10)

    def test_already_minimal_content_raises(self):
        """Content that can't fit even after all stages."""
        with pytest.raises(ContextBudgetError, match="Cannot reduce"):
            enforce_context_budget("abc", "", budget=2)

    def test_error_message_contains_budget(self):
        with pytest.raises(ContextBudgetError) as exc_info:
            enforce_context_budget("abc", "", budget=2)
        assert "2" in str(exc_info.value)


class TestEnforceContextBudgetMetadata:
    """BudgetResult metadata accuracy."""

    def test_original_chars_correct(self):
        result = enforce_context_budget("hello", "world", budget=1000)
        assert result.original_chars == 10

    def test_budget_recorded(self):
        result = enforce_context_budget("test", "", budget=500)
        assert result.budget == 500
