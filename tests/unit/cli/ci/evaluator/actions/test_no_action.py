"""Tests for no_action action handler."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.evaluator.actions import no_action
from agentic_devtools.cli.ci.evaluator.models import (
    PostAgentAction,
    PostAgentClassification,
    PostAgentSnapshot,
    ThreadInfo,
)


class TestNoAction:
    """Tests for no_action()."""

    def test_defaults_to_complete_when_sentinel_present(self) -> None:
        snapshot = PostAgentSnapshot(
            pr_number=42,
            has_sentinel=True,
            threads=(ThreadInfo(comment_id=1, is_resolved=False),),
        )

        result = no_action(MagicMock(), snapshot, dry_run=False)

        assert result.classification == PostAgentClassification.complete
        assert result.action_taken == PostAgentAction.no_action
        assert result.threads_unresolved == 1
        assert result.success is True
        assert result.dry_run is False

    def test_defaults_to_concurrent_skipped_without_sentinel(self) -> None:
        snapshot = PostAgentSnapshot(pr_number=42, has_sentinel=False)

        result = no_action(MagicMock(), snapshot, dry_run=True)

        assert result.classification == PostAgentClassification.concurrent_evaluation_skipped
        assert result.action_taken == PostAgentAction.no_action
        assert result.threads_unresolved == 0
        assert result.success is True
        assert result.dry_run is True

    def test_preserves_explicit_classification(self) -> None:
        snapshot = PostAgentSnapshot(pr_number=42, has_sentinel=False)

        result = no_action(
            MagicMock(),
            snapshot,
            classification=PostAgentClassification.agent_claims_fixed_no_sentinel,
            dry_run=True,
        )

        assert result.classification == PostAgentClassification.agent_claims_fixed_no_sentinel
        assert result.action_taken == PostAgentAction.no_action
