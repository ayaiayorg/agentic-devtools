"""Tests for agentic_fallback action handler."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.evaluator.actions import agentic_fallback
from agentic_devtools.cli.ci.evaluator.models import (
    PostAgentAction,
    PostAgentClassification,
    PostAgentSnapshot,
)


class TestAgenticFallback:
    """Tests for agentic_fallback action."""

    def test_dry_run(self):
        """Dry run reports success without dispatching."""
        snap = PostAgentSnapshot(pr_number=42, current_head_sha="abc", review_id=100)
        provider = MagicMock()

        result = agentic_fallback(provider, snap, dry_run=True)

        assert result.dry_run is True
        assert result.action_taken == PostAgentAction.agentic_fallback
        assert result.success is True
        provider.dispatch_repair.assert_not_called()

    def test_dispatches_repair(self):
        """Dispatches repair with correct parameters."""
        snap = PostAgentSnapshot(pr_number=42, current_head_sha="abc123", review_id=100)
        provider = MagicMock()

        result = agentic_fallback(provider, snap, dry_run=False)

        assert result.success is True
        provider.dispatch_repair.assert_called_once_with(
            pr_number=42,
            head_sha="abc123",
            repair_type="review",
            failed_checks=[],
            review_comments=[],
            review_id=100,
        )

    def test_handles_dispatch_failure(self):
        """Reports failure when dispatch_repair raises."""
        snap = PostAgentSnapshot(pr_number=42, current_head_sha="abc", review_id=1)
        provider = MagicMock()
        provider.dispatch_repair.side_effect = RuntimeError("dispatch failed")

        result = agentic_fallback(provider, snap, dry_run=False)

        assert result.success is False
        assert "dispatch failed" in result.error_details

    def test_classification_in_result(self):
        """Result has agent_silent classification."""
        snap = PostAgentSnapshot(pr_number=42)
        provider = MagicMock()

        result = agentic_fallback(provider, snap, dry_run=True)

        assert result.classification == PostAgentClassification.agent_silent
