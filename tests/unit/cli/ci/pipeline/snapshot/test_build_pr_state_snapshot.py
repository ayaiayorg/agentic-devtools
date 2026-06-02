"""Tests for build_pr_state_snapshot."""

from unittest.mock import MagicMock

import pytest

from agentic_devtools.cli.ci.models import CheckRunStatus, PRMetadata, ReviewCommentInfo, ReviewInfo
from agentic_devtools.cli.ci.pipeline.snapshot import (
    _evaluate_ci_status,
    build_pr_state_snapshot,
    get_effective_head_reviews,
    has_non_copilot_changes_requested_on_head,
)


class TestBuildPrStateSnapshot:
    """Tests for build_pr_state_snapshot behavior."""

    def test_ci_status_unknown_for_non_success_non_failure_completed_checks(self) -> None:
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.return_value = [
            CheckRunStatus(
                id=101,
                name="Run Targeted Checks",
                status="completed",
                conclusion="cancelled",
            )
        ]
        provider.list_reviews.return_value = []
        provider.list_pr_issue_events.return_value = []
        provider.count_commits_above_merge_base.return_value = 1

        snapshot = build_pr_state_snapshot(provider, 1)

        assert snapshot.ci_status == "unknown"
        assert snapshot.ci_failed_checks == []

    def test_uses_explicit_actionable_check_names_when_provided(self) -> None:
        """Explicit actionable set should be used without defaulting."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.return_value = [
            CheckRunStatus(id=101, name="Custom Check", status="completed", conclusion="success"),
        ]
        provider.list_reviews.return_value = []
        provider.list_pr_issue_events.return_value = []
        provider.count_commits_above_merge_base.return_value = 1

        snapshot = build_pr_state_snapshot(provider, 1, actionable_check_names=frozenset({"Custom Check"}))

        assert snapshot.ci_status == "passing"

    def test_unresolved_threads_fails_closed_when_review_comments_fetch_fails(self) -> None:
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.return_value = []
        provider.list_reviews.return_value = [
            ReviewInfo(id=10, user="Copilot", state="COMMENTED", commit_sha="old-sha"),
        ]
        provider.list_review_comments.side_effect = RuntimeError("boom")
        provider.list_review_thread_states.return_value = {}
        provider.list_pr_issue_events.return_value = []
        provider.count_commits_above_merge_base.return_value = 1

        snapshot = build_pr_state_snapshot(provider, 1)

        assert snapshot.unresolved_threads == 1

    def test_unresolved_threads_counts_across_all_prior_copilot_reviews(self) -> None:
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.return_value = []
        provider.list_reviews.return_value = [
            ReviewInfo(id=10, user="Copilot", state="COMMENTED", commit_sha="old-sha-1"),
            ReviewInfo(id=11, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old-sha-2"),
        ]
        provider.list_review_comments.side_effect = [
            [
                ReviewCommentInfo(id=101, path="a.py", body="a", html_url=""),
                ReviewCommentInfo(id=102, path="a.py", body="b", html_url=""),
            ],
            [
                ReviewCommentInfo(id=201, path="a.py", body="c", html_url=""),
                ReviewCommentInfo(id=202, path="a.py", body="d", html_url=""),
                ReviewCommentInfo(id=203, path="a.py", body="e", html_url=""),
            ],
        ]
        # All comments are unresolved
        provider.list_review_thread_states.return_value = {
            101: (False, False),
            102: (False, False),
            201: (False, False),
            202: (False, False),
            203: (False, False),
        }
        provider.list_pr_issue_events.return_value = []
        provider.count_commits_above_merge_base.return_value = 1

        snapshot = build_pr_state_snapshot(provider, 1)

        assert snapshot.unresolved_threads == 5
        assert provider.list_review_comments.call_count == 2

    def test_unresolved_threads_fails_closed_after_partial_aggregation(self) -> None:
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.return_value = []
        provider.list_reviews.return_value = [
            ReviewInfo(id=10, user="Copilot", state="COMMENTED", commit_sha="old-sha-1"),
            ReviewInfo(id=11, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old-sha-2"),
        ]
        provider.list_review_comments.side_effect = [
            [
                ReviewCommentInfo(id=101, path="a.py", body="a", html_url=""),
                ReviewCommentInfo(id=102, path="a.py", body="b", html_url=""),
            ],
            RuntimeError("boom"),
        ]
        # Both comments from first review are unresolved
        provider.list_review_thread_states.return_value = {
            101: (False, False),
            102: (False, False),
        }
        provider.list_pr_issue_events.return_value = []
        provider.count_commits_above_merge_base.return_value = 1

        snapshot = build_pr_state_snapshot(provider, 1)

        assert snapshot.unresolved_threads == 3

    def test_unresolved_threads_excludes_resolved_threads(self) -> None:
        """Only threads with isResolved=False should be counted."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.return_value = []
        provider.list_reviews.return_value = [
            ReviewInfo(id=10, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old-sha"),
        ]
        provider.list_review_comments.return_value = [
            ReviewCommentInfo(id=101, path="a.py", body="fix this", html_url=""),
            ReviewCommentInfo(id=102, path="a.py", body="also this", html_url=""),
            ReviewCommentInfo(id=103, path="a.py", body="and this", html_url=""),
        ]
        # 101 is unresolved, 102 is resolved, 103 is unresolved
        provider.list_review_thread_states.return_value = {
            101: (False, False),
            102: (True, False),
            103: (False, True),
        }
        provider.list_pr_issue_events.return_value = []
        provider.count_commits_above_merge_base.return_value = 1

        snapshot = build_pr_state_snapshot(provider, 1)

        assert snapshot.unresolved_threads == 2  # Only 101 and 103

    def test_unresolved_threads_falls_back_when_thread_states_unavailable(self) -> None:
        """When list_review_thread_states raises, fall back to counting all comments."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.return_value = []
        provider.list_reviews.return_value = [
            ReviewInfo(id=10, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old-sha"),
        ]
        provider.list_review_comments.return_value = [
            ReviewCommentInfo(id=101, path="a.py", body="fix", html_url=""),
            ReviewCommentInfo(id=102, path="a.py", body="fix2", html_url=""),
        ]
        provider.list_review_thread_states.side_effect = RuntimeError("API error")
        provider.list_pr_issue_events.return_value = []
        provider.count_commits_above_merge_base.return_value = 1

        snapshot = build_pr_state_snapshot(provider, 1)

        assert snapshot.unresolved_threads == 2  # Falls back to counting all

    def test_unresolved_threads_falls_back_without_thread_state_method(self) -> None:
        """When thread-state lookup is unavailable, count non-synthetic comments."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.return_value = []
        provider.list_reviews.return_value = [
            ReviewInfo(id=10, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old-sha"),
        ]
        provider.list_review_comments.return_value = [
            ReviewCommentInfo(id=-1, path="a.py", body="review body", html_url=""),
            ReviewCommentInfo(id=101, path="a.py", body="fix", html_url=""),
        ]
        provider.list_review_thread_states = None
        provider.list_pr_issue_events.return_value = []
        provider.count_commits_above_merge_base.return_value = 1

        snapshot = build_pr_state_snapshot(provider, 1)

        assert snapshot.unresolved_threads == 1

    def test_unresolved_threads_deduplicates_same_comment_id_across_reviews(self) -> None:
        """Same comment ID appearing in multiple prior reviews is only counted once."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.return_value = []
        provider.list_reviews.return_value = [
            ReviewInfo(id=10, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old-sha-1"),
            ReviewInfo(id=11, user="Copilot", state="COMMENTED", commit_sha="old-sha-2"),
        ]
        # Both reviews return the same comment ID 101 (e.g. a reply appearing in both)
        provider.list_review_comments.side_effect = [
            [ReviewCommentInfo(id=101, path="a.py", body="fix this", html_url="")],
            [ReviewCommentInfo(id=101, path="a.py", body="fix this", html_url="")],
        ]
        provider.list_review_thread_states.return_value = {101: (False, False)}
        provider.list_pr_issue_events.return_value = []
        provider.count_commits_above_merge_base.return_value = 1

        snapshot = build_pr_state_snapshot(provider, 1)

        assert snapshot.unresolved_threads == 1  # Counted once, not twice

    def test_unresolved_threads_skips_comments_not_in_thread_statuses(self) -> None:
        """Comments not found in thread status data are skipped rather than fail-closed."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.return_value = []
        provider.list_reviews.return_value = [
            ReviewInfo(id=10, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old-sha"),
        ]
        provider.list_review_comments.return_value = [
            ReviewCommentInfo(id=101, path="a.py", body="unresolved", html_url=""),
            ReviewCommentInfo(id=102, path="a.py", body="not in thread data", html_url=""),
        ]
        # 102 is absent from thread_statuses (e.g. deleted thread or reply in already-counted thread)
        provider.list_review_thread_states.return_value = {101: (False, False)}
        provider.list_pr_issue_events.return_value = []
        provider.count_commits_above_merge_base.return_value = 1

        snapshot = build_pr_state_snapshot(provider, 1)

        assert snapshot.unresolved_threads == 1  # 102 skipped, not fail-closed

    def test_count_commits_error_propagates_as_metadata_failure(self) -> None:
        """When count_commits_above_merge_base raises, build_pr_state_snapshot raises too.

        This ensures the caller (run_ai_pr_loop_v2) exits with EXIT_METADATA_FAILED
        rather than proceeding with an assumed commit count of 1.
        """
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.return_value = []
        provider.list_reviews.return_value = []
        provider.list_review_comments.return_value = []
        provider.list_pr_issue_events.return_value = []
        provider.count_commits_above_merge_base.side_effect = RuntimeError("git failure")

        with pytest.raises(RuntimeError, match="git failure"):
            build_pr_state_snapshot(provider, 1)

    def test_count_commits_provider_without_support_defaults_to_1(self) -> None:
        """When the provider lacks count_commits_above_merge_base, default to 1."""
        provider = MagicMock(
            spec=[
                "get_pr_metadata",
                "list_pr_files",
                "list_check_runs",
                "list_reviews",
                "list_review_comments",
                "list_pr_issue_events",
            ]
        )
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.return_value = []
        provider.list_reviews.return_value = []
        provider.list_pr_issue_events.return_value = []

        snapshot = build_pr_state_snapshot(provider, 1)

        assert snapshot.commit_count == 1

    def test_list_check_runs_error_propagates_as_metadata_failure(self) -> None:
        """When list_check_runs raises, build_pr_state_snapshot raises too.

        This ensures the caller (run_ai_pr_loop_v2) exits with EXIT_METADATA_FAILED
        rather than proceeding with an empty check list that silently drives
        ci_status to 'pending' and allows readiness evaluation against stale data.
        """
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.side_effect = RuntimeError("API outage")

        with pytest.raises(RuntimeError, match="API outage"):
            build_pr_state_snapshot(provider, 1)

    def test_list_pr_files_error_propagates_as_metadata_failure(self) -> None:
        """When list_pr_files raises, build_pr_state_snapshot raises too.

        This ensures the caller (run_ai_pr_loop_v2) exits with EXIT_METADATA_FAILED
        rather than proceeding with an empty file list that bypasses guard checks
        (privileged-path / Dockerfile checks rely on snapshot.files).
        """
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.side_effect = RuntimeError("network failure")

        with pytest.raises(RuntimeError, match="network failure"):
            build_pr_state_snapshot(provider, 1)

    def test_list_reviews_error_propagates_as_metadata_failure(self) -> None:
        """When list_reviews raises, build_pr_state_snapshot raises too."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.return_value = []
        provider.list_reviews.side_effect = RuntimeError("reviews unavailable")

        with pytest.raises(RuntimeError, match="reviews unavailable"):
            build_pr_state_snapshot(provider, 1)

    def test_has_approval_on_head_uses_effective_latest_review_per_reviewer(self) -> None:
        """A superseded approval should not count as current approval on HEAD."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.return_value = []
        provider.list_reviews.return_value = [
            ReviewInfo(id=10, user="alice", state="APPROVED", commit_sha="head-sha"),
            ReviewInfo(id=11, user="alice", state="CHANGES_REQUESTED", commit_sha="head-sha"),
            ReviewInfo(id=12, user="Copilot", state="APPROVED", commit_sha="head-sha"),
        ]
        provider.list_pr_issue_events.return_value = []
        provider.count_commits_above_merge_base.return_value = 1

        snapshot = build_pr_state_snapshot(provider, 1)

        assert snapshot.has_approval_on_head is True
        assert snapshot.review_state == "APPROVED"
        assert snapshot.copilot_review_id == 12

    def test_has_approval_on_head_false_when_reviewer_latest_state_is_changes_requested(self) -> None:
        """If latest effective HEAD review is CHANGES_REQUESTED, approval should be false."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.return_value = []
        provider.list_reviews.return_value = [
            ReviewInfo(id=10, user="alice", state="APPROVED", commit_sha="head-sha"),
            ReviewInfo(id=11, user="alice", state="CHANGES_REQUESTED", commit_sha="head-sha"),
        ]
        provider.list_pr_issue_events.return_value = []
        provider.count_commits_above_merge_base.return_value = 1

        snapshot = build_pr_state_snapshot(provider, 1)

        assert snapshot.has_approval_on_head is False

    def test_inline_count_unknown_when_head_commented_review_comments_fetch_fails(self) -> None:
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.return_value = []
        provider.list_reviews.return_value = [
            ReviewInfo(id=12, user="Copilot", state="COMMENTED", commit_sha="head-sha"),
        ]
        provider.list_review_comments.side_effect = RuntimeError("comments unavailable")
        provider.list_pr_issue_events.return_value = []
        provider.count_commits_above_merge_base.return_value = 1

        snapshot = build_pr_state_snapshot(provider, 1)

        assert snapshot.review_state == "COMMENTED"
        assert snapshot.copilot_review_id == 12
        assert snapshot.copilot_review_inline_count == -1

    def test_evaluate_ci_status_pending_when_actionable_pending(self) -> None:
        status, failed = _evaluate_ci_status(
            [
                CheckRunStatus(id=1, name="Targeted Checks ✅", status="in_progress", conclusion=""),
            ],
            frozenset({"Targeted Checks ✅"}),
        )
        assert status == "pending"
        assert failed == []

    def test_evaluate_ci_status_failing_with_actionable_failed_checks(self) -> None:
        status, failed = _evaluate_ci_status(
            [
                CheckRunStatus(id=1, name="Targeted Checks ✅", status="completed", conclusion="failure"),
            ],
            frozenset({"Targeted Checks ✅"}),
        )
        assert status == "failing"
        assert failed == ["Targeted Checks ✅"]

    def test_evaluate_ci_status_pending_takes_priority_over_failed(self) -> None:
        status, failed = _evaluate_ci_status(
            [
                CheckRunStatus(id=1, name="Targeted Checks ✅", status="completed", conclusion="failure"),
                CheckRunStatus(id=2, name="Smart Module Tests ✅", status="queued", conclusion=""),
            ],
            frozenset({"Targeted Checks ✅", "Smart Module Tests ✅"}),
        )
        assert status == "pending"
        assert failed == ["Targeted Checks ✅"]

    def test_evaluate_ci_status_passing_when_actionable_checks_succeed(self) -> None:
        status, failed = _evaluate_ci_status(
            [
                CheckRunStatus(id=1, name="Targeted Checks ✅", status="completed", conclusion="success"),
                CheckRunStatus(id=2, name="non-actionable", status="completed", conclusion="failure"),
            ],
            frozenset({"Targeted Checks ✅"}),
        )
        assert status == "passing"
        assert failed == []

    def test_head_commented_review_inline_count_is_comment_count(self) -> None:
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=1,
            title="Test PR",
            head_branch="feature",
            head_sha="head-sha",
            base_branch="main",
            requested_reviewers=[],
        )
        provider.list_pr_files.return_value = ["a.py"]
        provider.list_check_runs.return_value = []
        provider.list_reviews.return_value = [
            ReviewInfo(id=12, user="Copilot", state="COMMENTED", commit_sha="head-sha"),
        ]
        provider.list_review_comments.return_value = [MagicMock(), MagicMock(), MagicMock()]
        provider.list_pr_issue_events.return_value = []
        provider.count_commits_above_merge_base.return_value = 1

        snapshot = build_pr_state_snapshot(provider, 1)

        assert snapshot.copilot_review_inline_count == 3

    def test_get_effective_head_reviews_ignores_older_duplicate_review(self) -> None:
        """Lower review.id for same reviewer should not replace the latest review."""
        reviews = [
            ReviewInfo(id=20, user="alice", state="APPROVED", commit_sha="head-sha"),
            ReviewInfo(id=19, user="alice", state="CHANGES_REQUESTED", commit_sha="head-sha"),
        ]

        effective = get_effective_head_reviews(reviews, "head-sha")

        assert len(effective) == 1
        assert effective[0].id == 20
        assert effective[0].state == "APPROVED"

    def test_has_non_copilot_changes_requested_on_head_false_when_none(self) -> None:
        assert has_non_copilot_changes_requested_on_head([], "head-sha") is False
