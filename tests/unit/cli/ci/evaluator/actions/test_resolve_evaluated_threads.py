"""Tests for resolve_evaluated_threads action handler."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.evaluator.actions import resolve_evaluated_threads
from agentic_devtools.cli.ci.evaluator.models import (
    PostAgentAction,
    PostAgentClassification,
    PostAgentSnapshot,
    ThreadInfo,
)
from agentic_devtools.cli.ci.models import ReviewCommentInfo


def _marker_reply(comment_id: int, root_id: int | None = None, author: str = "Copilot") -> ReviewCommentInfo:
    return ReviewCommentInfo(
        id=comment_id,
        path="src/main.py",
        body="<!-- ai-pr-loop:thread-evaluated -->\nNo change warranted.",
        html_url=f"https://example.test/comment/{comment_id}",
        author_login=author,
        in_reply_to_id=root_id,
    )


class TestResolveEvaluatedThreads:
    """Tests for resolve_evaluated_threads action."""

    def test_review_id_mismatch_returns_failure(self):
        """Returns failure when repair-satisfied review-id doesn't match active review."""
        threads = (ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=999,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()

        result = resolve_evaluated_threads(provider, snap)

        assert result.success is False
        assert result.error_details == "review-id mismatch"
        assert result.classification == PostAgentClassification.repair_satisfied_no_changes
        assert result.action_taken == PostAgentAction.resolve_evaluated_threads
        assert result.threads_unresolved == 1

    def test_dry_run_reports_threads_without_resolving(self):
        """Dry run reports what would be resolved without side effects."""
        threads = (
            ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),
            ThreadInfo(comment_id=2, is_resolved=False, has_reply=True),
        )
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.list_review_comments.return_value = [
            _marker_reply(comment_id=11, root_id=1),
            _marker_reply(comment_id=12, root_id=2),
        ]

        result = resolve_evaluated_threads(provider, snap, dry_run=True)

        assert result.dry_run is True
        assert result.success is True
        assert result.threads_resolved == 2
        assert result.threads_unresolved == 0

    def test_threads_missing_marker_go_to_unresolved(self):
        """Threads without a marker reply are counted as unresolved."""
        threads = (
            ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),
            ThreadInfo(comment_id=2, is_resolved=False, has_reply=False),
        )
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.list_review_comments.return_value = [_marker_reply(comment_id=11, root_id=1)]

        result = resolve_evaluated_threads(provider, snap, dry_run=True)

        assert result.threads_resolved == 1
        assert result.threads_unresolved == 1

    @patch("agentic_devtools.cli.github.resolve_review_threads.resolve_review_threads")
    def test_resolves_threads_successfully(self, mock_resolve):
        """Successfully resolves threads with evaluated markers."""
        mock_resolve.return_value = {"threadsResolved": 2, "alreadyResolved": 0, "threadsFailed": 0, "verified": True}
        threads = (
            ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),
            ThreadInfo(comment_id=2, is_resolved=False, has_reply=True),
        )
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.list_review_comments.return_value = [
            _marker_reply(comment_id=11, root_id=1),
            _marker_reply(comment_id=12, root_id=2),
        ]

        result = resolve_evaluated_threads(provider, snap)

        assert result.success is True
        assert result.threads_resolved == 2
        assert result.threads_unresolved == 0
        assert result.dry_run is False
        mock_resolve.assert_called_once_with(
            pr_number=42,
            repo="owner/repo",
            comment_ids=[1, 2],
        )

    @patch("agentic_devtools.cli.github.resolve_review_threads.resolve_review_threads")
    def test_resolution_exception_returns_failure(self, mock_resolve):
        """Returns failure when resolve_review_threads raises."""
        mock_resolve.side_effect = RuntimeError("GraphQL error")
        threads = (ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.list_review_comments.return_value = [_marker_reply(comment_id=11, root_id=1)]

        result = resolve_evaluated_threads(provider, snap)

        assert result.success is False
        assert result.error_details == "GraphQL error"
        assert result.threads_resolved == 0
        assert result.threads_unresolved == 1

    @patch("agentic_devtools.cli.github.resolve_review_threads.resolve_review_threads")
    def test_counts_already_resolved_in_total(self, mock_resolve):
        """Already-resolved threads are counted in resolved total."""
        mock_resolve.return_value = {"threadsResolved": 1, "alreadyResolved": 1, "threadsFailed": 0, "verified": True}
        threads = (
            ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),
            ThreadInfo(comment_id=2, is_resolved=False, has_reply=True),
        )
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.list_review_comments.return_value = [
            _marker_reply(comment_id=11, root_id=1),
            _marker_reply(comment_id=12, root_id=2),
        ]

        result = resolve_evaluated_threads(provider, snap)

        assert result.threads_resolved == 2

    def test_no_threads_to_resolve_succeeds(self):
        """No unresolved threads results in success with zero resolved."""
        threads = (ThreadInfo(comment_id=1, is_resolved=True, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.count_unresolved_review_threads.return_value = 0
        provider.list_review_comments.return_value = []

        result = resolve_evaluated_threads(provider, snap)

        assert result.success is True
        assert result.threads_resolved == 0
        assert result.threads_unresolved == 0
        provider.count_unresolved_review_threads.assert_called_once_with(42)

    def test_no_threads_to_resolve_skips_marker_fetch(self):
        """No unresolved threads succeeds even when marker signals are unavailable."""
        threads = (ThreadInfo(comment_id=1, is_resolved=True, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.count_unresolved_review_threads.return_value = 0
        provider.list_review_comments.side_effect = RuntimeError("unavailable")

        result = resolve_evaluated_threads(provider, snap)

        assert result.success is True
        assert result.threads_resolved == 0
        assert result.threads_unresolved == 0
        provider.list_review_comments.assert_not_called()

    def test_empty_snapshot_threads_fails_closed_when_count_raises(self):
        """Fails closed when count_unresolved_review_threads raises and snapshot threads are empty."""
        threads = (ThreadInfo(comment_id=1, is_resolved=True, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.count_unresolved_review_threads.side_effect = RuntimeError("API timeout")

        result = resolve_evaluated_threads(provider, snap)

        assert result.success is False
        assert result.error_details == "could not verify unresolved thread count"
        assert result.threads_resolved == 0
        assert result.threads_unresolved == 0

    def test_empty_snapshot_threads_fails_when_live_count_positive(self):
        """Fails when snapshot shows no unresolved threads but provider reports some."""
        threads = (ThreadInfo(comment_id=1, is_resolved=True, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.count_unresolved_review_threads.return_value = 3

        result = resolve_evaluated_threads(provider, snap)

        assert result.success is False
        assert result.error_details == "snapshot thread load failed — unresolved threads detected"
        assert result.threads_unresolved == 3
        assert result.threads_resolved == 0

    def test_skips_resolved_threads(self):
        """Already-resolved threads are skipped in the unresolved list."""
        threads = (
            ThreadInfo(comment_id=1, is_resolved=True, has_reply=True),
            ThreadInfo(comment_id=2, is_resolved=False, has_reply=True),
        )
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.list_review_comments.return_value = [_marker_reply(comment_id=11, root_id=2)]

        result = resolve_evaluated_threads(provider, snap, dry_run=True)

        assert result.threads_resolved == 1

    def test_review_id_none_skips_validation(self):
        """When repair_satisfied_review_id is None, validation is skipped."""
        threads = (ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=None,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.list_review_comments.return_value = []

        result = resolve_evaluated_threads(provider, snap, dry_run=True)

        assert result.success is True

    def test_no_active_review_id_uses_repair_satisfied_review_id(self):
        threads = (ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=0,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.list_review_comments.return_value = [_marker_reply(comment_id=11, root_id=1)]

        result = resolve_evaluated_threads(provider, snap, dry_run=True)

        assert result.success is True
        assert result.threads_resolved == 1
        assert result.threads_unresolved == 0
        provider.list_review_comments.assert_called_once_with(42, 100)

    def test_nested_marker_reply_resolves_root_thread(self):
        """Nested marker replies are mapped to the root thread comment ID."""
        threads = (ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.list_review_comments.return_value = [
            ReviewCommentInfo(id=1, path="src/main.py", body="root", html_url="", author_login="reviewer"),
            ReviewCommentInfo(
                id=2,
                path="src/main.py",
                body="intermediate",
                html_url="",
                author_login="reviewer",
                in_reply_to_id=1,
            ),
            _marker_reply(comment_id=3, root_id=2),
        ]

        result = resolve_evaluated_threads(provider, snap, dry_run=True)

        assert result.success is True
        assert result.threads_resolved == 1
        assert result.threads_unresolved == 0

    def test_cycle_in_review_comment_chain_is_ignored(self):
        """Cycle in reply chain is ignored instead of resolving an incorrect ID."""
        threads = (ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.list_review_comments.return_value = [
            ReviewCommentInfo(
                id=10,
                path="src/main.py",
                body="a",
                html_url="",
                author_login="reviewer",
                in_reply_to_id=11,
            ),
            _marker_reply(comment_id=11, root_id=10),
        ]

        result = resolve_evaluated_threads(provider, snap, dry_run=True)

        assert result.success is True
        assert result.threads_resolved == 0
        assert result.threads_unresolved == 1

    def test_nonpositive_parent_in_chain_is_ignored(self):
        """Reply chains with non-positive parent IDs do not resolve any thread."""
        threads = (ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.list_review_comments.return_value = [
            ReviewCommentInfo(
                id=20,
                path="src/main.py",
                body="intermediate",
                html_url="",
                author_login="reviewer",
                in_reply_to_id=-1,
            ),
            _marker_reply(comment_id=21, root_id=20),
        ]

        result = resolve_evaluated_threads(provider, snap, dry_run=True)

        assert result.success is True
        assert result.threads_resolved == 0
        assert result.threads_unresolved == 1

    def test_fails_closed_when_no_review_id_available(self):
        threads = (ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=0,
            repair_satisfied_review_id=None,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()

        result = resolve_evaluated_threads(provider, snap)

        assert result.success is False
        assert result.error_details == "thread marker signals unavailable"

    @patch("agentic_devtools.cli.github.resolve_review_threads.resolve_review_threads")
    def test_resolution_verification_failure_returns_failure(self, mock_resolve):
        mock_resolve.return_value = {"threadsResolved": 1, "alreadyResolved": 0, "threadsFailed": 0, "verified": False}
        threads = (ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.list_review_comments.return_value = [_marker_reply(comment_id=11, root_id=1)]

        result = resolve_evaluated_threads(provider, snap)

        assert result.success is False
        assert result.error_details == "Thread resolution verification failed"

    def test_fails_closed_when_marker_signals_unavailable(self):
        threads = (ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.list_review_comments.side_effect = RuntimeError("unavailable")

        result = resolve_evaluated_threads(provider, snap)

        assert result.success is False
        assert result.error_details == "thread marker signals unavailable"

    def test_ignores_non_marker_unauthorized_and_nonpositive_root(self):
        threads = (ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.list_review_comments.return_value = [
            ReviewCommentInfo(id=2, path="src/main.py", body="no marker", html_url=""),
            _marker_reply(comment_id=3, root_id=1, author="random-user"),
            _marker_reply(comment_id=-1, root_id=None, author="Copilot"),
        ]

        result = resolve_evaluated_threads(provider, snap, dry_run=True)

        assert result.threads_resolved == 0
        assert result.threads_unresolved == 1

    def test_all_unresolved_threads_without_markers_return_failure(self):
        """Unresolved threads without marker replies fail with unresolved remaining."""
        threads = (ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.list_review_comments.return_value = []

        result = resolve_evaluated_threads(provider, snap)

        assert result.success is False
        assert result.threads_resolved == 0
        assert result.threads_unresolved == 1
        assert result.error_details == "Unmarked unresolved threads remain"

    @patch("agentic_devtools.cli.github.resolve_review_threads.resolve_review_threads")
    def test_unmarked_unresolved_threads_return_failure(self, mock_resolve):
        mock_resolve.return_value = {"threadsResolved": 1, "alreadyResolved": 0, "threadsFailed": 0, "verified": True}
        threads = (
            ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),
            ThreadInfo(comment_id=2, is_resolved=False, has_reply=True),
        )
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.list_review_comments.return_value = [_marker_reply(comment_id=11, root_id=1)]

        result = resolve_evaluated_threads(provider, snap)

        assert result.success is False
        assert result.error_details == "Unmarked unresolved threads remain"

    @patch("agentic_devtools.cli.github.resolve_review_threads.resolve_review_threads")
    def test_resolved_count_shortfall_returns_failure(self, mock_resolve):
        mock_resolve.return_value = {"threadsResolved": 1, "alreadyResolved": 0, "threadsFailed": 0, "verified": True}
        threads = (
            ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),
            ThreadInfo(comment_id=2, is_resolved=False, has_reply=True),
        )
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        provider.list_review_comments.return_value = [
            _marker_reply(comment_id=11, root_id=1),
            _marker_reply(comment_id=12, root_id=2),
        ]

        result = resolve_evaluated_threads(provider, snap)

        assert result.success is False
        assert result.error_details == "Resolved count does not cover all targeted thread IDs"

    def test_human_reply_after_marker_prevents_resolution(self):
        """Thread is NOT evaluated when a human reply follows Copilot's marker (most-recent comment wins)."""
        threads = (ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        # comment 11 (Copilot marker) has a lower ID than comment 12 (human reply)
        provider.list_review_comments.return_value = [
            _marker_reply(comment_id=11, root_id=1),  # Copilot posts marker
            ReviewCommentInfo(
                id=12,
                path="src/main.py",
                body="Please reconsider.",
                html_url="https://example.test/comment/12",
                author_login="human-reviewer",
                in_reply_to_id=11,
            ),  # human replies afterward
        ]

        result = resolve_evaluated_threads(provider, snap, dry_run=True)

        assert result.threads_resolved == 0
        assert result.threads_unresolved == 1

    def test_copilot_marker_is_latest_in_thread_resolves(self):
        """Thread IS evaluated when Copilot's marker is the last comment (highest ID)."""
        threads = (ThreadInfo(comment_id=1, is_resolved=False, has_reply=True),)
        snap = PostAgentSnapshot(
            pr_number=42,
            repo="owner/repo",
            threads=threads,
            review_id=100,
            repair_satisfied_review_id=100,
            has_repair_satisfied_marker=True,
        )
        provider = MagicMock()
        # comment 12 (human question) has a lower ID than comment 20 (Copilot marker)
        provider.list_review_comments.return_value = [
            ReviewCommentInfo(
                id=12,
                path="src/main.py",
                body="Is this intentional?",
                html_url="https://example.test/comment/12",
                author_login="human-reviewer",
                in_reply_to_id=1,
            ),
            _marker_reply(comment_id=20, root_id=12),  # Copilot replies with marker last
        ]

        result = resolve_evaluated_threads(provider, snap, dry_run=True)

        assert result.threads_resolved == 1
        assert result.threads_unresolved == 0
