"""Tests for PostAgentAction enum."""

from agentic_devtools.cli.ci.evaluator.models import PostAgentAction


class TestPostAgentAction:
    """Tests for PostAgentAction enum."""

    def test_all_variants_exist(self):
        """All five action variants are defined."""
        assert PostAgentAction.no_action.value == "no_action"
        assert PostAgentAction.verify_and_resolve.value == "verify_and_resolve"
        assert PostAgentAction.synthesize_sentinel.value == "synthesize_sentinel"
        assert PostAgentAction.trigger_re_review.value == "trigger_re_review"
        assert PostAgentAction.agentic_fallback.value == "agentic_fallback"

    def test_variant_count(self):
        """Exactly five variants exist."""
        assert len(PostAgentAction) == 5
