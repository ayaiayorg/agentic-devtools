"""Exhaustive unit tests for classify_post_agent_state()."""

from agentic_devtools.cli.ci.evaluator.classifier import classify_post_agent_state
from agentic_devtools.cli.ci.evaluator.models import (
    CommentInfo,
    PostAgentClassification,
    PostAgentSnapshot,
    ThreadInfo,
)


class TestClassifyPostAgentState:
    """Tests covering all six classification branches."""

    def test_concurrent_evaluation_skipped(self):
        """Lock held by another run → concurrent_evaluation_skipped."""
        snap = PostAgentSnapshot(pr_number=1, lock_holder="other-run-123")
        assert classify_post_agent_state(snap) == PostAgentClassification.concurrent_evaluation_skipped

    def test_complete_with_sentinel(self):
        """Sentinel present → complete."""
        snap = PostAgentSnapshot(pr_number=1, has_sentinel=True)
        assert classify_post_agent_state(snap) == PostAgentClassification.complete

    def test_complete_with_sentinel_and_lock(self):
        """Sentinel present but lock held → concurrent_evaluation_skipped (lock takes priority)."""
        snap = PostAgentSnapshot(pr_number=1, has_sentinel=True, lock_holder="other")
        assert classify_post_agent_state(snap) == PostAgentClassification.concurrent_evaluation_skipped

    def test_threads_resolved_no_sentinel(self):
        """All threads resolved, no sentinel → threads_resolved_no_sentinel."""
        threads = (
            ThreadInfo(comment_id=1, is_resolved=True),
            ThreadInfo(comment_id=2, is_resolved=True),
        )
        snap = PostAgentSnapshot(pr_number=1, threads=threads)
        assert classify_post_agent_state(snap) == PostAgentClassification.threads_resolved_no_sentinel

    def test_agent_claims_fixed_no_sentinel(self):
        """Agent comment present, no head change, unresolved threads."""
        threads = (ThreadInfo(comment_id=1, is_resolved=False),)
        comment = CommentInfo(id=99, author="copilot[bot]", body="Already fixed")
        snap = PostAgentSnapshot(
            pr_number=1,
            threads=threads,
            latest_agent_comment=comment,
            head_changed_since_review=False,
        )
        assert classify_post_agent_state(snap) == PostAgentClassification.agent_claims_fixed_no_sentinel

    def test_changes_made_threads_unresolved(self):
        """Head changed, unresolved threads → changes_made_threads_unresolved."""
        threads = (ThreadInfo(comment_id=1, is_resolved=False),)
        snap = PostAgentSnapshot(
            pr_number=1,
            threads=threads,
            head_changed_since_review=True,
        )
        assert classify_post_agent_state(snap) == PostAgentClassification.changes_made_threads_unresolved

    def test_agent_silent_no_threads(self):
        """No sentinel, no threads, no comment → agent_silent."""
        snap = PostAgentSnapshot(pr_number=1)
        assert classify_post_agent_state(snap) == PostAgentClassification.agent_silent

    def test_agent_silent_with_head_change_no_threads(self):
        """Head changed but no unresolved threads (empty) → agent_silent."""
        snap = PostAgentSnapshot(pr_number=1, head_changed_since_review=True)
        assert classify_post_agent_state(snap) == PostAgentClassification.agent_silent

    def test_agent_claims_fixed_overrides_changes_made(self):
        """Agent comment without head change takes priority over changes_made."""
        threads = (ThreadInfo(comment_id=1, is_resolved=False),)
        comment = CommentInfo(id=99, body="Done")
        snap = PostAgentSnapshot(
            pr_number=1,
            threads=threads,
            latest_agent_comment=comment,
            head_changed_since_review=False,
        )
        assert classify_post_agent_state(snap) == PostAgentClassification.agent_claims_fixed_no_sentinel

    def test_changes_made_with_agent_comment(self):
        """Head changed with agent comment still classifies as changes_made."""
        threads = (ThreadInfo(comment_id=1, is_resolved=False),)
        comment = CommentInfo(id=99, body="Fixed")
        snap = PostAgentSnapshot(
            pr_number=1,
            threads=threads,
            latest_agent_comment=comment,
            head_changed_since_review=True,
        )
        # head_changed + unresolved → changes_made (rule 5), even if agent commented
        assert classify_post_agent_state(snap) == PostAgentClassification.changes_made_threads_unresolved
