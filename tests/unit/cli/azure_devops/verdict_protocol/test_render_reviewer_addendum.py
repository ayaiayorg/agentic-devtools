"""Tests for render_reviewer_addendum function."""

import pytest

from agentic_devtools.cli.azure_devops.review_state import VerdictType
from agentic_devtools.cli.azure_devops.verdict_protocol import render_reviewer_addendum


class TestRenderReviewerAddendum:
    """Tests for render_reviewer_addendum."""

    def test_supplement_with_items(self):
        """Renders supplement addendum with supplements list."""
        result = render_reviewer_addendum(
            model_name="Gemini Pro 3.1",
            verdict_type=VerdictType.SUPPLEMENT,
            commit_hash="abc1234567890",
            supplements=["Additional observation 1", "Additional observation 2"],
        )
        assert "## Reviewer Addendum — Gemini Pro 3.1" in result
        assert "**Verdict:** Agree + Supplement" in result
        assert "### Supplements" in result
        assert "- Additional observation 1" in result
        assert "- Additional observation 2" in result
        assert "`abc1234`" in result

    def test_disagree_with_items(self):
        """Renders disagree addendum with disagreements list."""
        result = render_reviewer_addendum(
            model_name="GPT Codex 5.3",
            verdict_type=VerdictType.DISAGREE,
            commit_hash="def5678901234",
            disagreements=["The null check is actually correct", "This is not a bug"],
        )
        assert "## Reviewer Addendum — GPT Codex 5.3" in result
        assert "**Verdict:** Disagree" in result
        assert "### Disagreements" in result
        assert "- The null check is actually correct" in result

    def test_with_commit_url(self):
        """Renders commit hash as a link when commit_url is provided."""
        result = render_reviewer_addendum(
            model_name="Model A",
            verdict_type=VerdictType.SUPPLEMENT,
            commit_hash="abc1234567890",
            commit_url="https://example.com/commit/abc1234",
            supplements=["Found something"],
        )
        assert "[`abc1234`](https://example.com/commit/abc1234)" in result

    def test_without_commit_hash(self):
        """Uses 'unknown' when commit_hash is None."""
        result = render_reviewer_addendum(
            model_name="Model A",
            verdict_type=VerdictType.SUPPLEMENT,
            supplements=["A finding"],
        )
        assert "`unknown`" in result

    def test_model_icon_included(self):
        """Includes model icon in the attribution line."""
        result = render_reviewer_addendum(
            model_name="Claude Opus 4.6",
            verdict_type=VerdictType.DISAGREE,
            commit_hash="abc1234",
            disagreements=["Point of disagreement"],
        )
        # Claude models use 🧠
        assert "🧠" in result
        assert "🤖" in result

    def test_both_supplements_and_disagreements(self):
        """Renders both sections when both lists are provided."""
        result = render_reviewer_addendum(
            model_name="Model A",
            verdict_type=VerdictType.DISAGREE,
            commit_hash="abc1234",
            supplements=["Supplement item"],
            disagreements=["Disagree item"],
        )
        assert "### Supplements" in result
        assert "### Disagreements" in result

    def test_starts_with_separator(self):
        """Addendum starts with horizontal rule separator."""
        result = render_reviewer_addendum(
            model_name="Model A",
            verdict_type=VerdictType.SUPPLEMENT,
            commit_hash="abc",
            supplements=["Item"],
        )
        assert result.startswith("---")

    def test_no_supplements_section_when_empty(self):
        """Supplements section omitted when list is None."""
        result = render_reviewer_addendum(
            model_name="Model A",
            verdict_type=VerdictType.DISAGREE,
            commit_hash="abc",
            disagreements=["Point"],
        )
        assert "### Supplements" not in result

    def test_invalid_verdict_type_raises(self):
        """Raises ValueError for unsupported verdict type."""
        with pytest.raises(ValueError, match="Unsupported verdict_type"):
            render_reviewer_addendum(
                model_name="Model A",
                verdict_type=VerdictType.AGREE,
                commit_hash="abc",
            )

    def test_arbitrary_string_verdict_type_raises(self):
        """Raises ValueError for arbitrary string verdict type."""
        with pytest.raises(ValueError, match="Unsupported verdict_type"):
            render_reviewer_addendum(
                model_name="Model A",
                verdict_type="invalid_type",
                commit_hash="abc",
            )
