"""Tests for _build_consolidation_prompt stub."""

from agentic_devtools.cli.review.consolidate import _build_consolidation_prompt


class TestBuildConsolidationPrompt:
    """Tests for _build_consolidation_prompt stub."""

    def test_returns_prompt_string(self):
        """Stub returns a prompt string."""
        result = _build_consolidation_prompt(pr_id=123, amendment_replies={"file.ts": {}})
        assert "123" in result
        assert isinstance(result, str)
