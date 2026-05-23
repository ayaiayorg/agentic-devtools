"""Tests for trigger_re_review action handler."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.evaluator.actions import trigger_re_review
from agentic_devtools.cli.ci.evaluator.models import (
    PostAgentAction,
    PostAgentClassification,
    PostAgentSnapshot,
    ThreadInfo,
)
from agentic_devtools.cli.ci.models import COPILOT_REVIEWER_LOGIN


class TestTriggerReReview:
    """Tests for trigger_re_review action."""

    def test_dry_run(self):
        """Dry run reports success without requesting reviewer."""
        threads = (ThreadInfo(comment_id=1, is_resolved=False),)
        snap = PostAgentSnapshot(pr_number=42, threads=threads)
        provider = MagicMock()

        result = trigger_re_review(provider, snap, dry_run=True)

        assert result.dry_run is True
        assert result.action_taken == PostAgentAction.trigger_re_review
        assert result.success is True
        provider.request_reviewer.assert_not_called()

    def test_requests_copilot_reviewer(self):
        """Requests Copilot as a reviewer."""
        threads = (ThreadInfo(comment_id=1, is_resolved=False),)
        snap = PostAgentSnapshot(pr_number=42, threads=threads)
        provider = MagicMock()

        result = trigger_re_review(provider, snap, dry_run=False)

        assert result.success is True
        provider.request_reviewer.assert_called_once_with(42, COPILOT_REVIEWER_LOGIN)

    def test_handles_request_failure(self):
        """Reports failure when request_reviewer raises."""
        snap = PostAgentSnapshot(pr_number=42)
        provider = MagicMock()
        provider.request_reviewer.side_effect = RuntimeError("rate limited")

        result = trigger_re_review(provider, snap, dry_run=False)

        assert result.success is False
        assert "rate limited" in result.error_details

    def test_classification_in_result(self):
        """Result has changes_made_threads_unresolved classification by default."""
        snap = PostAgentSnapshot(pr_number=42)
        provider = MagicMock()

        result = trigger_re_review(provider, snap, dry_run=True)

        assert result.classification == PostAgentClassification.changes_made_threads_unresolved

    def test_preserves_custom_classification(self):
        """Caller can pass a different classification that is reflected in the result."""
        snap = PostAgentSnapshot(pr_number=42)
        provider = MagicMock()

        result = trigger_re_review(
            provider,
            snap,
            classification=PostAgentClassification.agent_claims_fixed_no_sentinel,
            dry_run=True,
        )

        assert result.classification == PostAgentClassification.agent_claims_fixed_no_sentinel
        assert result.action_taken == PostAgentAction.trigger_re_review
