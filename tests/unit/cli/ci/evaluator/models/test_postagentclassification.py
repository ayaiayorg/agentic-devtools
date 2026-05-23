"""Tests for PostAgentClassification enum."""

from agentic_devtools.cli.ci.evaluator.models import PostAgentClassification


class TestPostAgentClassification:
    """Tests for PostAgentClassification enum."""

    def test_all_variants_exist(self):
        """All six classification variants are defined."""
        assert PostAgentClassification.complete.value == "complete"
        assert PostAgentClassification.agent_claims_fixed_no_sentinel.value == "agent_claims_fixed_no_sentinel"
        assert PostAgentClassification.threads_resolved_no_sentinel.value == "threads_resolved_no_sentinel"
        assert PostAgentClassification.changes_made_threads_unresolved.value == "changes_made_threads_unresolved"
        assert PostAgentClassification.agent_silent.value == "agent_silent"
        assert PostAgentClassification.concurrent_evaluation_skipped.value == "concurrent_evaluation_skipped"

    def test_variant_count(self):
        """Exactly six variants exist."""
        assert len(PostAgentClassification) == 6
