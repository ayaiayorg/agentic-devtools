"""Tests for verify_and_resolve action handler."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.evaluator.actions import verify_and_resolve
from agentic_devtools.cli.ci.evaluator.models import (
    PostAgentAction,
    PostAgentClassification,
    PostAgentSnapshot,
    ThreadInfo,
)

_DIFF_WITH_MODIFICATION = """\
diff --git a/src/main.py b/src/main.py
index abc..def 100644
--- a/src/main.py
+++ b/src/main.py
@@ -10,3 +10,4 @@ def hello():
     print("hello")
+    print("world")
     return True
"""


class TestVerifyAndResolve:
    """Tests for verify_and_resolve action."""

    def test_dry_run(self):
        """Dry run reports what would be resolved without side effects."""
        threads = (ThreadInfo(comment_id=1, path="src/main.py", start_line=11, is_resolved=False),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            diff_text=_DIFF_WITH_MODIFICATION,
            head_changed_since_review=True,
        )
        provider = MagicMock()

        result = verify_and_resolve(provider, snap, dry_run=True)

        assert result.dry_run is True
        assert result.action_taken == PostAgentAction.verify_and_resolve
        assert result.threads_resolved == 1
        provider.post_comment.assert_not_called()

    def test_failure_when_unverified_threads_remain(self):
        """Do not post sentinel when unverified unresolved threads remain."""
        threads = (
            ThreadInfo(comment_id=1, path="src/main.py", start_line=11, is_resolved=False),
            ThreadInfo(comment_id=2, path="src/other.py", start_line=5, is_resolved=False),
        )
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            diff_text=_DIFF_WITH_MODIFICATION,
            head_changed_since_review=True,
        )
        provider = MagicMock()

        with patch(
            "agentic_devtools.cli.github.resolve_review_threads.resolve_review_threads",
            return_value={
                "threadsResolved": 1,
                "threadsFailed": 0,
                "alreadyResolved": 0,
                "verified": True,
            },
        ) as mock_resolve:
            result = verify_and_resolve(provider, snap, dry_run=False)

        assert result.success is False
        assert result.threads_resolved == 1
        assert result.threads_unresolved == 1
        mock_resolve.assert_called_once_with(pr_number=42, repo="owner/repo", comment_ids=[1])
        provider.post_comment.assert_not_called()

    def test_no_verified_threads(self):
        """When no threads can be verified, resolved count is 0."""
        threads = (ThreadInfo(comment_id=1, path="src/other.py", start_line=5, is_resolved=False),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            diff_text=_DIFF_WITH_MODIFICATION,
            head_changed_since_review=True,
        )
        provider = MagicMock()

        with patch("agentic_devtools.cli.github.resolve_review_threads.resolve_review_threads") as mock_resolve:
            result = verify_and_resolve(provider, snap, dry_run=False)

        assert result.success is False
        assert result.threads_resolved == 0
        assert result.threads_unresolved == 1
        mock_resolve.assert_not_called()
        provider.post_comment.assert_not_called()

    def test_classification_in_result(self):
        """Result has agent_claims_fixed_no_sentinel classification."""
        snap = PostAgentSnapshot(pr_number=42, repo="owner/repo")
        provider = MagicMock()

        result = verify_and_resolve(provider, snap, dry_run=True)

        assert result.classification == PostAgentClassification.agent_claims_fixed_no_sentinel

    def test_marks_unverified_when_thread_has_no_path_or_diff(self):
        """Threads without file path/diff are counted as unverified."""
        threads = (ThreadInfo(comment_id=1, path="", start_line=11, is_resolved=False),)
        snap = PostAgentSnapshot(pr_number=42, repo="owner/repo", threads=threads, diff_text="")
        provider = MagicMock()

        result = verify_and_resolve(provider, snap, dry_run=True)

        assert result.threads_resolved == 0
        assert result.threads_unresolved == 1

    def test_returns_failure_when_thread_resolution_raises(self):
        """Resolution failure returns unsuccessful result with details."""
        threads = (ThreadInfo(comment_id=1, path="src/main.py", start_line=11, is_resolved=False),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            diff_text=_DIFF_WITH_MODIFICATION,
            head_changed_since_review=True,
        )
        provider = MagicMock()

        with patch(
            "agentic_devtools.cli.github.resolve_review_threads.resolve_review_threads",
            side_effect=RuntimeError("boom"),
        ):
            result = verify_and_resolve(provider, snap, dry_run=False)

        assert result.success is False
        assert result.error_details == "boom"

    def test_sentinel_post_failure_is_non_fatal(self):
        """Failure to post sentinel logs warning but still returns success."""
        threads = (ThreadInfo(comment_id=1, path="src/main.py", start_line=11, is_resolved=False),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            diff_text=_DIFF_WITH_MODIFICATION,
            head_changed_since_review=True,
        )
        provider = MagicMock()
        provider.post_comment.side_effect = RuntimeError("comment failed")

        with patch(
            "agentic_devtools.cli.github.resolve_review_threads.resolve_review_threads",
            return_value={
                "threadsResolved": 1,
                "threadsFailed": 0,
                "alreadyResolved": 0,
                "verified": True,
            },
        ):
            result = verify_and_resolve(provider, snap, dry_run=False)

        assert result.success is True

    def test_posts_sentinel_when_all_unresolved_threads_verified(self):
        """Sentinel is posted only when all unresolved threads are resolved."""
        threads = (ThreadInfo(comment_id=1, path="src/main.py", start_line=11, is_resolved=False),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            diff_text=_DIFF_WITH_MODIFICATION,
            head_changed_since_review=True,
        )
        provider = MagicMock()

        with patch(
            "agentic_devtools.cli.github.resolve_review_threads.resolve_review_threads",
            return_value={
                "threadsResolved": 1,
                "threadsFailed": 0,
                "alreadyResolved": 0,
                "verified": True,
            },
        ) as mock_resolve:
            result = verify_and_resolve(provider, snap, dry_run=False)

        assert result.success is True
        assert result.threads_resolved == 1
        assert result.threads_unresolved == 0
        mock_resolve.assert_called_once_with(pr_number=42, repo="owner/repo", comment_ids=[1])
        provider.post_comment.assert_called_once()

    def test_resolution_verification_failure_returns_unsuccessful_result(self):
        """Failed thread-resolution verification must not be reported as success."""
        threads = (ThreadInfo(comment_id=1, path="src/main.py", start_line=11, is_resolved=False),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            diff_text=_DIFF_WITH_MODIFICATION,
            head_changed_since_review=True,
        )
        provider = MagicMock()

        with patch(
            "agentic_devtools.cli.github.resolve_review_threads.resolve_review_threads",
            return_value={
                "threadsResolved": 0,
                "threadsFailed": 1,
                "alreadyResolved": 0,
                "verified": False,
            },
        ):
            result = verify_and_resolve(provider, snap, dry_run=False)

        assert result.success is False
        assert result.threads_resolved == 0
        assert result.threads_unresolved == 1
        provider.post_comment.assert_not_called()

    def test_returns_failure_when_head_has_not_changed_since_review(self):
        """Evaluator must not auto-resolve threads when there are no post-review changes."""
        threads = (ThreadInfo(comment_id=1, path="src/main.py", start_line=11, is_resolved=False),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            diff_text=_DIFF_WITH_MODIFICATION,
            head_changed_since_review=False,
        )
        provider = MagicMock()

        with patch("agentic_devtools.cli.github.resolve_review_threads.resolve_review_threads") as mock_resolve:
            result = verify_and_resolve(provider, snap, dry_run=False)

        assert result.success is False
        assert result.threads_resolved == 0
        assert result.threads_unresolved == 1
        assert result.error_details == "No post-review code changes to verify against"
        mock_resolve.assert_not_called()
        provider.post_comment.assert_not_called()

    def test_returns_failure_when_resolved_count_less_than_verified_ids(self):
        """Sentinel must not be posted when resolved_count < len(verified_ids), even if verified=True."""
        # Both threads point to line 11 (the modified line in the diff),
        # so both end up in verified_ids, but the resolver only resolves 1.
        threads = (
            ThreadInfo(comment_id=1, path="src/main.py", start_line=11, is_resolved=False),
            ThreadInfo(comment_id=2, path="src/main.py", start_line=11, is_resolved=False),
        )
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            diff_text=_DIFF_WITH_MODIFICATION,
            head_changed_since_review=True,
        )
        provider = MagicMock()

        # resolve_review_threads reports verified=True but only resolved 1 out of 2 IDs
        # (e.g., one comment ID could not be mapped to a review thread)
        with patch(
            "agentic_devtools.cli.github.resolve_review_threads.resolve_review_threads",
            return_value={
                "threadsResolved": 1,
                "threadsFailed": 0,
                "alreadyResolved": 0,
                "verified": True,
            },
        ) as mock_resolve:
            result = verify_and_resolve(provider, snap, dry_run=False)

        assert result.success is False
        assert result.threads_resolved == 1
        assert result.threads_unresolved == 1
        assert "Resolved count does not cover all verified thread IDs" in result.error_details
        mock_resolve.assert_called_once()
        provider.post_comment.assert_not_called()
