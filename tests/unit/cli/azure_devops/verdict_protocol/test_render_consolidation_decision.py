"""Tests for render_consolidation_decision function."""

from agentic_devtools.cli.azure_devops.verdict_protocol import render_consolidation_decision


class TestRenderConsolidationDecision:
    """Tests for render_consolidation_decision."""

    def test_basic_approved(self):
        """Renders a basic approved consolidation decision."""
        result = render_consolidation_decision(
            boss_model="Claude Opus 4.6",
            final_verdict="✅ Approved",
            resolved_from=["Gemini Pro 3.1", "GPT Codex 5.3"],
            commit_hash="abc1234567890",
            resolution_notes=["The null check concern was valid but already handled elsewhere"],
        )
        assert "## Consolidation Decision — Claude Opus 4.6" in result
        assert "Gemini Pro 3.1, GPT Codex 5.3" in result
        assert "**Final Verdict:** ✅ Approved" in result
        assert "### Resolution Notes" in result
        assert "`abc1234`" in result

    def test_needs_work(self):
        """Renders a needs-work consolidation decision."""
        result = render_consolidation_decision(
            boss_model="Claude Opus 4.6",
            final_verdict="📝 Needs Work",
            resolved_from=["Model B"],
            commit_hash="def5678",
        )
        assert "**Final Verdict:** 📝 Needs Work" in result

    def test_with_commit_url(self):
        """Uses commit URL when provided."""
        result = render_consolidation_decision(
            boss_model="Boss",
            final_verdict="✅ Approved",
            resolved_from=["A"],
            commit_hash="abc1234",
            commit_url="https://example.com/commit",
        )
        assert "[`abc1234`](https://example.com/commit)" in result

    def test_without_commit_hash(self):
        """Uses 'unknown' when commit_hash is None."""
        result = render_consolidation_decision(
            boss_model="Boss",
            final_verdict="✅ Approved",
            resolved_from=["A"],
        )
        assert "`unknown`" in result

    def test_no_resolution_notes(self):
        """Omits resolution notes section when None."""
        result = render_consolidation_decision(
            boss_model="Boss",
            final_verdict="✅ Approved",
            resolved_from=["A"],
            commit_hash="abc",
        )
        assert "### Resolution Notes" not in result

    def test_starts_with_separator(self):
        """Decision starts with horizontal rule."""
        result = render_consolidation_decision(
            boss_model="Boss",
            final_verdict="✅ Approved",
            resolved_from=["A"],
            commit_hash="abc",
        )
        assert result.startswith("---")

    def test_empty_resolved_from(self):
        """Uses 'reviewers' when resolved_from is empty."""
        result = render_consolidation_decision(
            boss_model="Boss",
            final_verdict="✅ Approved",
            resolved_from=[],
            commit_hash="abc",
        )
        assert "reviewers" in result
