"""Tests for dispatch_action()."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.evaluator.actions import dispatch_action
from agentic_devtools.cli.ci.evaluator.models import (
    PostAgentAction,
    PostAgentClassification,
    PostAgentSnapshot,
)


class TestDispatchAction:
    """Tests for evaluator action dispatch behavior."""

    def test_preserves_concurrent_classification_for_no_action(self):
        """No-action handler must keep the input concurrent classification."""
        provider = MagicMock()
        snapshot = PostAgentSnapshot(pr_number=42, repo="owner/repo", has_sentinel=True)

        result = dispatch_action(
            PostAgentClassification.concurrent_evaluation_skipped,
            provider,
            snapshot,
            dry_run=True,
        )

        assert result.classification == PostAgentClassification.concurrent_evaluation_skipped

    def test_dispatches_non_no_action_handler(self):
        """Non-no_action classifications dispatch to their mapped handler."""
        provider = MagicMock()
        snapshot = PostAgentSnapshot(pr_number=42, repo="owner/repo")

        result = dispatch_action(
            PostAgentClassification.threads_resolved_no_sentinel,
            provider,
            snapshot,
            dry_run=True,
        )

        assert result.action_taken == PostAgentAction.synthesize_sentinel

    def test_agent_claims_without_head_change_routes_to_rereview(self):
        """No post-review change should route to re-review, not auto-resolution."""
        provider = MagicMock()
        snapshot = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            head_changed_since_review=False,
        )

        result = dispatch_action(
            PostAgentClassification.agent_claims_fixed_no_sentinel,
            provider,
            snapshot,
            dry_run=True,
        )

        assert result.action_taken == PostAgentAction.trigger_re_review

    def test_agent_claims_without_head_change_preserves_classification(self):
        """Classification must remain agent_claims_fixed_no_sentinel when routed to re-review."""
        provider = MagicMock()
        snapshot = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            head_changed_since_review=False,
        )

        result = dispatch_action(
            PostAgentClassification.agent_claims_fixed_no_sentinel,
            provider,
            snapshot,
            dry_run=True,
        )

        assert result.classification == PostAgentClassification.agent_claims_fixed_no_sentinel

    def test_agent_claims_with_head_change_routes_to_verify(self):
        """Post-review changes with agent claim should use verify-and-resolve."""
        provider = MagicMock()
        snapshot = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            head_changed_since_review=True,
        )

        result = dispatch_action(
            PostAgentClassification.agent_claims_fixed_no_sentinel,
            provider,
            snapshot,
            dry_run=True,
        )

        assert result.action_taken == PostAgentAction.verify_and_resolve
