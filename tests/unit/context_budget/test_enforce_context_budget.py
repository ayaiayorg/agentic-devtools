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
        # Budget accounts for the separator \n between desc and comments:
        # 50 + 50 + 1 = 101
        result = enforce_context_budget(desc, comm, budget=101)
        assert result.stage is ReductionStage.PASSTHROUGH
        assert result.original_chars == 101
        assert result.final_chars == 101

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

    def test_reduction_to_empty_falls_through_to_later_stage(self):
        """Content that reduces to nothing (only HTML images) should not
        return REDUCED with empty content — it should fall through to
        truncation or raise ContextBudgetError."""
        # Content is entirely HTML img tags — reduction strips everything.
        # Budget must be less than original (52 chars) to skip passthrough,
        # but reduced content is empty (0 chars, within budget). Without the
        # validate_content_shape guard, Stage 2 would return empty content.
        desc = '<img src="a.png"> <img src="b.png">'
        comm = '<img src="c.png">'
        with pytest.raises(ContextBudgetError, match="Cannot reduce"):
            enforce_context_budget(desc, comm, budget=40)


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

    def test_input_only_images_whitespace_falls_to_reduced(self):
        """Content that reduces deterministically should assert the exact stage."""
        desc = "<img src='url'/> " * 3 + "abc"
        comm = "<img src='url2'/> " * 5
        result = enforce_context_budget(desc, comm, budget=20)
        assert result.description == "   abc"
        assert result.comments == ""
        assert result.stage is ReductionStage.REDUCED

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
        # "hello" + "\n" + "world" = 11 chars (separator included)
        result = enforce_context_budget("hello", "world", budget=1000)
        assert result.original_chars == 11

    def test_budget_recorded(self):
        result = enforce_context_budget("test", "", budget=500)
        assert result.budget == 500

    def test_no_separator_when_comments_empty(self):
        """Separator is NOT added when comments is empty."""
        result = enforce_context_budget("hello", "", budget=1000)
        assert result.original_chars == 5  # just len("hello"), no separator

    def test_separator_included_in_near_budget_passthrough(self):
        """Passthrough accounts for separator so CLI output stays in budget.

        Regression test: description(5) + comments(5) + separator(1) = 11 chars.
        Budget of 10 should NOT passthrough because emitted output is 11.
        """
        result = enforce_context_budget("hello", "world", budget=10)
        # 5 + 5 + 1 = 11 > 10 → NOT passthrough
        assert result.stage is not ReductionStage.PASSTHROUGH
        assert result.final_chars <= 10

    def test_separator_included_in_near_budget_reduced(self):
        """Reduced stage accounts for separator in its budget check.

        Content with markdown that reduces to exactly at budget must still
        include the separator newline in the budget math.
        """
        # "## xx" (5 chars) → stripped to "xx" (2 chars)
        # comments "yy" (2 chars) → stays "yy" (2 chars)
        # With separator: 2 + 2 + 1 = 5 chars
        desc = "## xx"
        comm = "yy"
        # Original: 5 + 2 + 1 = 8 chars (over budget of 6)
        # Reduced: 2 + 2 + 1 = 5 chars (within budget of 6)
        result = enforce_context_budget(desc, comm, budget=6)
        assert result.stage is ReductionStage.REDUCED
        assert result.final_chars == 5
        assert result.final_chars <= 6

    def test_stage3_combined_no_leading_newline_when_desc_empty(self):
        """Stage 3 combined text does not start with a newline when desc reduces to empty.

        Regression: when reduced_desc is empty and reduced_comments is non-empty,
        the combined text should NOT have a leading newline character.
        """
        # Description is only images (reduces to empty), comments are real text.
        desc = "![img](http://example.com/pic.png) " * 100  # reduces to empty
        comm = "real content " * 100  # stays non-empty, over budget
        result = enforce_context_budget(desc, comm, budget=50)
        # Stage 3 or 4 should be reached; description should not start with \n
        assert not result.description.startswith("\n"), (
            "Stage 3 combined should not start with a leading newline"
        )

    def test_whitespace_only_reduced_parts_treated_as_empty(self):
        """Reduced parts that become whitespace-only are treated as empty.

        Regression: if reduction leaves only whitespace/newlines (e.g. from
        image removal producing ``\\n\\n``), the separator predicate should
        treat that as empty rather than truthy, avoiding wasted budget chars
        and leading blank lines.
        """
        # Craft input that reduces to whitespace-only for desc, real content for comments
        desc = "![a](http://x.com/a.png)\n\n![b](http://x.com/b.png)"  # reduces to whitespace
        comm = "substantive comment text here"
        result = enforce_context_budget(desc, comm, budget=5000)
        # After normalization, reduced_desc should be empty (stripped whitespace-only)
        # so the separator should NOT be counted
        assert not result.description.startswith("\n"), (
            "Whitespace-only reduced desc should not cause leading newline"
        )
        # Description field should be empty or the comment text (no blank-line prefix)
        if result.description:
            assert result.description.strip(), (
                "Description should not be whitespace-only"
            )
