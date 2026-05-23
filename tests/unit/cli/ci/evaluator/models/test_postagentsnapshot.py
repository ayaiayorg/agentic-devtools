"""Tests for PostAgentSnapshot dataclass."""

from agentic_devtools.cli.ci.evaluator.models import (
    CommentInfo,
    PostAgentSnapshot,
    ThreadInfo,
)


class TestPostAgentSnapshot:
    """Tests for PostAgentSnapshot frozen dataclass."""

    def test_default_values(self):
        """Snapshot has sensible defaults."""
        snap = PostAgentSnapshot(pr_number=42)
        assert snap.pr_number == 42
        assert snap.repo == ""
        assert snap.has_sentinel is False
        assert snap.head_changed_since_review is False
        assert snap.threads == ()
        assert snap.latest_agent_comment is None
        assert snap.review_id == 0
        assert snap.review_commit_sha == ""
        assert snap.current_head_sha == ""
        assert snap.lock_holder == ""
        assert snap.lock_age_seconds == 0.0
        assert snap.diff_text == ""

    def test_with_threads(self):
        """Snapshot stores threads as tuple."""
        t = ThreadInfo(comment_id=1, path="src/main.py", start_line=10)
        snap = PostAgentSnapshot(pr_number=1, threads=(t,))
        assert len(snap.threads) == 1
        assert snap.threads[0].comment_id == 1

    def test_with_agent_comment(self):
        """Snapshot stores latest agent comment."""
        comment = CommentInfo(id=99, author="copilot[bot]", body="Fixed!")
        snap = PostAgentSnapshot(pr_number=1, latest_agent_comment=comment)
        assert snap.latest_agent_comment is not None
        assert snap.latest_agent_comment.body == "Fixed!"

    def test_frozen(self):
        """Snapshot is immutable."""
        snap = PostAgentSnapshot(pr_number=1)
        try:
            snap.pr_number = 2  # type: ignore[misc]
            assert False, "Should raise"
        except AttributeError:
            pass
