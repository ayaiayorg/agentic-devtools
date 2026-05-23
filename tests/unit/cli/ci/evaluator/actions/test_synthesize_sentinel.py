"""Tests for synthesize_sentinel action handler."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.evaluator.actions import synthesize_sentinel
from agentic_devtools.cli.ci.evaluator.models import (
    PostAgentAction,
    PostAgentClassification,
    PostAgentSnapshot,
)


class TestSynthesizeSentinel:
    """Tests for synthesize_sentinel action."""

    def test_dry_run(self):
        """Dry run reports success without posting."""
        snap = PostAgentSnapshot(pr_number=42, repo="owner/repo", current_head_sha="abc123")
        provider = MagicMock()

        result = synthesize_sentinel(provider, snap, dry_run=True)

        assert result.dry_run is True
        assert result.action_taken == PostAgentAction.synthesize_sentinel
        assert result.success is True
        provider.post_comment.assert_not_called()

    def test_posts_sentinel_comment(self):
        """Posts a sentinel comment with HEAD info."""
        snap = PostAgentSnapshot(pr_number=42, repo="owner/repo", current_head_sha="abc12345")
        provider = MagicMock()

        result = synthesize_sentinel(provider, snap, dry_run=False)

        assert result.success is True
        provider.post_comment.assert_called_once()
        body = provider.post_comment.call_args[0][1]
        assert "<!-- copilot-agent-result -->" in body
        assert "abc12345" in body

    def test_handles_post_failure(self):
        """Reports failure when post_comment raises."""
        snap = PostAgentSnapshot(pr_number=42, repo="owner/repo", current_head_sha="abc")
        provider = MagicMock()
        provider.post_comment.side_effect = RuntimeError("API error")

        result = synthesize_sentinel(provider, snap, dry_run=False)

        assert result.success is False
        assert result.error_details == "API error"

    def test_classification_in_result(self):
        """Result has threads_resolved_no_sentinel classification."""
        snap = PostAgentSnapshot(pr_number=42)
        provider = MagicMock()

        result = synthesize_sentinel(provider, snap, dry_run=True)

        assert result.classification == PostAgentClassification.threads_resolved_no_sentinel
