"""Tests for build_pr_state_snapshot."""

from unittest.mock import MagicMock

import pytest

from agentic_devtools.cli.ci.models import CheckRunStatus, PRMetadata, ReviewInfo
from agentic_devtools.cli.ci.pipeline.snapshot import build_pr_state_snapshot


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
                name="Targeted Checks ✅",
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
            [MagicMock(), MagicMock()],
            [MagicMock(), MagicMock(), MagicMock()],
        ]
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
            [MagicMock(), MagicMock()],
            RuntimeError("boom"),
        ]
        provider.list_pr_issue_events.return_value = []
        provider.count_commits_above_merge_base.return_value = 1

        snapshot = build_pr_state_snapshot(provider, 1)

        assert snapshot.unresolved_threads == 3

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
