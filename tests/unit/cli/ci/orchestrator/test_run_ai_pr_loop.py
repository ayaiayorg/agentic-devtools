"""Tests for run_ai_pr_loop() orchestrator state machine."""

import json
from io import StringIO
from typing import cast
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.models import (
    COPILOT_REVIEWER_LOGIN,
    CheckRunStatus,
    EventPayload,
    PRMetadata,
    ReviewInfo,
)
from agentic_devtools.cli.ci.orchestrator import (
    EXIT_GUARD_BLOCKED,
    EXIT_MERGE_BLOCKED,
    EXIT_METADATA_FAILED,
    EXIT_REPAIR_DISPATCHED,
    EXIT_SUCCESS,
    _count_commits_above_merge_base,
    run_ai_pr_loop,
)
from agentic_devtools.cli.ci.provider import CIPlatformProvider


def _make_provider(
    *,
    pr_meta: PRMetadata | None = None,
    files: list[str] | None = None,
    check_runs: list[CheckRunStatus] | None = None,
    reviews: list[ReviewInfo] | None = None,
) -> MagicMock:
    """Create a mock provider with sensible defaults."""
    provider = MagicMock()
    provider.get_pr_metadata.return_value = pr_meta or PRMetadata(
        number=42,
        title="feat: test",
        head_branch="feature/test",
        head_sha="abc123",
        base_branch="main",
        head_repo_full_name="owner/repo",
        base_repo_full_name="owner/repo",
        labels=["ai-auto-merge-allowed"],
    )
    provider.list_pr_files.return_value = files if files is not None else ["src/main.py"]
    provider.list_check_runs.return_value = (
        check_runs
        if check_runs is not None
        else [CheckRunStatus(id=1, name="Tests ✅", status="completed", conclusion="success")]
    )
    provider.list_reviews.return_value = (
        reviews
        if reviews is not None
        else [ReviewInfo(id=1, user="copilot-pull-request-reviewer[bot]", state="APPROVED", body="lgtm")]
    )
    provider.find_comment.return_value = None
    provider.post_comment.return_value = 100
    provider.merge_pr.return_value = None
    provider.count_commits_above_merge_base.return_value = 1
    return provider


def _capture_summary(provider: MagicMock, payload: EventPayload) -> dict:
    """Run the orchestrator and capture the JSON decision summary from stdout."""
    buf = StringIO()
    with (
        patch("agentic_devtools.cli.ci.orchestrator.sys.stdout", buf),
        patch("agentic_devtools.cli.ci.orchestrator._is_github_actions", return_value=False),
    ):
        run_ai_pr_loop(provider, payload)
    return json.loads(buf.getvalue().strip())


class TestRunAIPRLoop:
    """Tests for the run_ai_pr_loop orchestrator."""

    def test_no_pr_number_returns_success(self) -> None:
        provider = MagicMock()
        payload = EventPayload(pr_number=0)
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.get_pr_metadata.assert_not_called()

    def test_full_happy_path_merges(self) -> None:
        """PR with passing checks and approval gets merged."""
        provider = _make_provider()
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.merge_pr.assert_called_once_with(42, "abc123", "squash")

    def test_fork_pr_blocked(self) -> None:
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="t",
                head_branch="b",
                head_sha="s",
                base_branch="main",
                head_repo_full_name="fork/repo",
                base_repo_full_name="owner/repo",
            )
        )
        payload = EventPayload(pr_number=42, head_sha="s")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_GUARD_BLOCKED

    def test_privileged_paths_blocked(self) -> None:
        provider = _make_provider(files=[".github/workflows/ci.yml"])
        payload = EventPayload(pr_number=42, head_sha="abc123", action="synchronize")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_GUARD_BLOCKED

    def test_docker_files_blocked(self) -> None:
        provider = _make_provider(files=["Dockerfile"])
        payload = EventPayload(pr_number=42, head_sha="abc123", action="synchronize")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_GUARD_BLOCKED

    def test_exclusion_label_skips(self) -> None:
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="t",
                head_branch="b",
                head_sha="s",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                labels=["ai-pr-loop-ignore"],
            )
        )
        payload = EventPayload(pr_number=42, head_sha="s")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_GUARD_BLOCKED

    def test_missing_auto_merge_allowed_label_prevents_merge(self) -> None:
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="t",
                head_branch="b",
                head_sha="s",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                labels=[],
            )
        )
        payload = EventPayload(pr_number=42, head_sha="s")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.merge_pr.assert_not_called()

    def test_pending_checks_waits(self) -> None:
        provider = _make_provider(check_runs=[CheckRunStatus(id=1, name="Tests ✅", status="in_progress")])
        payload = EventPayload(pr_number=42, head_sha="abc123", action="synchronize")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.merge_pr.assert_not_called()

    def test_ci_completion_with_failed_checks_and_actionable_review_dispatches_both_repair(self) -> None:
        """CI-completion dispatches combined repair when CI fails and Copilot is actionable."""
        provider = _make_provider(
            check_runs=[CheckRunStatus(id=2, name="Workflow Tests ✅", status="completed", conclusion="failure")],
            reviews=[
                ReviewInfo(id=1, user="copilot-pull-request-reviewer[bot]", state="CHANGES_REQUESTED", body="fix")
            ],
        )
        provider.dispatch_repair.return_value = 200
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_REPAIR_DISPATCHED
        provider.dispatch_repair.assert_called_once()
        assert provider.post_comment.call_count == 2
        dispatched = provider.dispatch_repair.call_args.kwargs
        assert dispatched["repair_type"] == "both"

    def test_ci_completion_failed_checks_waits_for_pending_copilot_review(self) -> None:
        """CI-completion with failed checks waits while Copilot review is still pending."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="feat: test",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                requested_reviewers=[COPILOT_REVIEWER_LOGIN],
            ),
            check_runs=[CheckRunStatus(id=2, name="Workflow Tests ✅", status="completed", conclusion="failure")],
            reviews=[ReviewInfo(id=10, user="human-reviewer", state="APPROVED", body="looks good")],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        summary = _capture_summary(provider, payload)
        assert summary["decision"] == "wait"
        assert summary["reason"] == "awaiting_copilot_review_before_ci_repair"
        assert summary["exit_code"] == EXIT_SUCCESS
        provider.dispatch_repair.assert_not_called()
        provider.find_comment.assert_not_called()

    def test_ci_completion_failed_checks_with_dismissed_copilot_review_still_waits(self) -> None:
        """Dismissed Copilot review does not count as effective HEAD review for CI-completion."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="feat: test",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                requested_reviewers=[COPILOT_REVIEWER_LOGIN],
            ),
            check_runs=[CheckRunStatus(id=2, name="Workflow Tests ✅", status="completed", conclusion="failure")],
            reviews=[
                ReviewInfo(
                    id=12,
                    user="copilot-pull-request-reviewer[bot]",
                    state="DISMISSED",
                    body="dismissed",
                )
            ],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        summary = _capture_summary(provider, payload)
        assert summary["decision"] == "wait"
        assert summary["reason"] == "awaiting_copilot_review_before_ci_repair"
        assert summary["exit_code"] == EXIT_SUCCESS
        provider.dispatch_repair.assert_not_called()
        provider.find_comment.assert_not_called()

    def test_ci_completion_failed_checks_and_non_actionable_copilot_dispatches_ci_repair(self) -> None:
        """CI-completion dispatches CI-only repair when Copilot already reviewed non-actionably."""
        provider = _make_provider(
            check_runs=[CheckRunStatus(id=2, name="Workflow Tests ✅", status="completed", conclusion="failure")],
            reviews=[ReviewInfo(id=11, user="copilot-pull-request-reviewer[bot]", state="COMMENTED", body="lgtm")],
        )
        provider.list_review_comments.return_value = []
        provider.dispatch_repair.return_value = 200
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_REPAIR_DISPATCHED
        provider.dispatch_repair.assert_called_once()
        dispatched = provider.dispatch_repair.call_args.kwargs
        assert dispatched["repair_type"] == "ci"

    def test_ci_completion_failed_checks_dispatch_failure_returns_reason(self) -> None:
        """CI-completion repair dispatch failures surface failure reason in summary path."""
        provider = _make_provider(
            check_runs=[CheckRunStatus(id=2, name="Workflow Tests ✅", status="completed", conclusion="failure")],
            reviews=[],
        )
        provider.dispatch_repair.side_effect = RuntimeError("ci dispatch failed")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_MERGE_BLOCKED
        assert provider.post_comment.call_count == 1

    def test_auto_approves_when_no_approval(self) -> None:
        """Auto-approves when Copilot reviewed non-actionably but no APPROVED review exists."""
        provider = _make_provider(
            reviews=[ReviewInfo(id=1, user="copilot-pull-request-reviewer[bot]", state="COMMENTED", body="lgtm")]
        )
        provider.list_review_comments.return_value = []
        provider.approve_pr.return_value = True
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.approve_pr.assert_called_once()
        provider.merge_pr.assert_called_once()

    def test_submitted_event_approval_skipped_blocks_merge(self) -> None:
        """Submitted path blocks merge when auto-approval is skipped."""
        provider = _make_provider(
            reviews=[ReviewInfo(id=1, user="copilot-pull-request-reviewer[bot]", state="COMMENTED", body="lgtm")]
        )
        provider.list_review_comments.return_value = []
        provider.approve_pr.return_value = False
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_MERGE_BLOCKED
        provider.approve_pr.assert_called_once()
        provider.merge_pr.assert_not_called()

    def test_deduplication_limit_blocks(self) -> None:
        """When dedup limit is exceeded, guard blocks."""
        provider = _make_provider()
        # Simulate existing marker with count at max
        provider.find_comment.return_value = (
            100,
            "<!-- repair-dispatch:abc123:3 -->\nTracking",
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="synchronize")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_GUARD_BLOCKED

    def test_ci_completion_dedup_race_recheck_blocks_duplicate_dispatch(self) -> None:
        """A dedup marker increase before dispatch blocks duplicate repair comments."""
        provider = _make_provider(
            check_runs=[CheckRunStatus(id=2, name="Workflow Tests ✅", status="completed", conclusion="failure")],
            reviews=[ReviewInfo(id=11, user="copilot-pull-request-reviewer[bot]", state="COMMENTED", body="lgtm")],
        )
        provider.list_review_comments.return_value = []
        provider.find_comment.side_effect = [
            None,  # Initial dedup check creates marker count=1
            None,  # Cycle guard (no tracker yet)
            (101, "<!-- repair-dispatch:abc123:2 -->\nDispatch tracking"),  # Race re-check before dispatch
        ]
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_GUARD_BLOCKED
        provider.dispatch_repair.assert_not_called()

    def test_cycle_limit_blocks(self) -> None:
        """When cycle limit is reached, guard blocks."""
        provider = _make_provider()
        # First find_comment (dedup) returns None, second (cycle) returns at-limit
        provider.find_comment.side_effect = [
            None,  # dedup: no marker
            (200, "<!-- ai-pr-loop-cycle-tracker --> cycle:50"),  # cycle: at limit
        ]
        payload = EventPayload(pr_number=42, head_sha="abc123", action="synchronize")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_GUARD_BLOCKED

    def test_copilot_changes_requested_dispatches_repair(self) -> None:
        """Copilot CHANGES_REQUESTED triggers repair dispatch."""
        provider = _make_provider(
            reviews=[ReviewInfo(id=1, user="copilot-pull-request-reviewer[bot]", state="CHANGES_REQUESTED", body="fix")]
        )
        provider.dispatch_repair.return_value = 200
        provider.list_review_comments.return_value = ["fix this"]
        payload = EventPayload(pr_number=42, head_sha="abc123", action="synchronize")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_REPAIR_DISPATCHED
        provider.merge_pr.assert_not_called()
        provider.dispatch_repair.assert_called_once()
        assert provider.post_comment.call_count == 2

    def test_human_changes_requested_does_not_dispatch_repair(self) -> None:
        """Human CHANGES_REQUESTED blocks merge but does NOT trigger repair."""
        provider = _make_provider(reviews=[ReviewInfo(id=1, user="reviewer", state="CHANGES_REQUESTED", body="fix")])
        payload = EventPayload(pr_number=42, head_sha="abc123", action="synchronize")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.merge_pr.assert_not_called()
        provider.dispatch_repair.assert_not_called()
        assert provider.post_comment.call_count == 1

    def test_merge_failure_returns_blocked(self) -> None:
        from agentic_devtools.cli.ci.orchestrator import EXIT_MERGE_BLOCKED

        provider = _make_provider()
        provider.merge_pr.side_effect = RuntimeError("merge conflict")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_MERGE_BLOCKED

    def test_checks_not_all_passing_blocks_merge(self) -> None:
        """Checks with non-success conclusion (e.g., cancelled) block merge."""
        from agentic_devtools.cli.ci.orchestrator import EXIT_MERGE_BLOCKED

        provider = _make_provider(
            check_runs=[
                CheckRunStatus(id=1, name="Tests ✅", status="completed", conclusion="cancelled"),
            ]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_MERGE_BLOCKED

    def test_copilot_older_changes_requested_superseded_by_approval(self) -> None:
        """Older Copilot CHANGES_REQUESTED is superseded by a later APPROVED from same user."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(id=1, user="copilot-pull-request-reviewer[bot]", state="CHANGES_REQUESTED", body="fix"),
                ReviewInfo(id=5, user="copilot-pull-request-reviewer[bot]", state="APPROVED", body="lgtm"),
            ]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.dispatch_repair.assert_not_called()
        provider.merge_pr.assert_called_once()

    def test_human_older_changes_requested_superseded_by_approval(self) -> None:
        """Older human CHANGES_REQUESTED is superseded by a later APPROVED from same user."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(id=2, user="reviewer", state="CHANGES_REQUESTED", body="fix"),
                ReviewInfo(id=7, user="reviewer", state="APPROVED", body="lgtm"),
                ReviewInfo(id=9, user="copilot-pull-request-reviewer[bot]", state="APPROVED", body="lgtm"),
            ]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.merge_pr.assert_called_once()

    def test_latest_copilot_changes_requested_still_triggers_repair(self) -> None:
        """Latest Copilot review is CHANGES_REQUESTED — repair still dispatched."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(id=1, user="copilot-pull-request-reviewer[bot]", state="APPROVED", body="ok"),
                ReviewInfo(id=9, user="copilot-pull-request-reviewer[bot]", state="CHANGES_REQUESTED", body="fix"),
            ]
        )
        provider.dispatch_repair.return_value = 200
        provider.list_review_comments.return_value = ["fix this"]
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_REPAIR_DISPATCHED
        provider.dispatch_repair.assert_called_once()

    def test_copilot_commented_with_inline_comments_dispatches_repair(self) -> None:
        """Copilot COMMENTED review with inline comments triggers repair dispatch."""
        provider = _make_provider(
            reviews=[ReviewInfo(id=3, user="copilot-pull-request-reviewer[bot]", state="COMMENTED", body="")]
        )
        provider.dispatch_repair.return_value = 200
        provider.list_review_comments.return_value = ["suggestion: use const"]
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_REPAIR_DISPATCHED
        provider.dispatch_repair.assert_called_once()
        # Comments fetched exactly once during detection; _dispatch_repair reuses the cache
        provider.list_review_comments.assert_called_once()

    def test_ci_completion_with_actionable_review_triggers_post_repair_finalization(self) -> None:
        """CI completion with actionable Copilot review finalizes post-repair actions."""
        provider = _make_provider(
            reviews=[ReviewInfo(id=3, user="copilot-pull-request-reviewer[bot]", state="COMMENTED", body="")]
        )
        provider.list_review_comments.return_value = ["suggestion: use const"]
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.finalize_post_repair.assert_called_once_with(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123",
            review_id=3,
        )
        provider.dispatch_repair.assert_not_called()

    def test_ci_completion_finalization_failure_blocks(self) -> None:
        provider = _make_provider(
            reviews=[ReviewInfo(id=3, user="copilot-pull-request-reviewer[bot]", state="COMMENTED", body="")]
        )
        provider.list_review_comments.return_value = ["suggestion: use const"]
        provider.finalize_post_repair.side_effect = RuntimeError("finalization failed")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_MERGE_BLOCKED

    def test_ci_completion_prior_commit_changes_requested_triggers_finalization(self) -> None:
        """CI completion + CHANGES_REQUESTED on prior commit → post_repair_soft_finalized."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=5,
                    user="copilot-pull-request-reviewer[bot]",
                    state="CHANGES_REQUESTED",
                    body="fix this",
                    commit_sha="oldsha",
                )
            ]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.finalize_post_repair.assert_called_once_with(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123",
            review_id=5,
        )
        provider.dispatch_repair.assert_not_called()

    def test_ci_completion_prior_commit_commented_with_inline_comments_triggers_finalization(self) -> None:
        """CI completion + COMMENTED with inline comments on prior commit → post_repair_soft_finalized."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=7,
                    user="copilot-pull-request-reviewer[bot]",
                    state="COMMENTED",
                    body="",
                    commit_sha="oldsha",
                )
            ]
        )
        provider.list_review_comments.return_value = ["suggestion: use const"]
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.finalize_post_repair.assert_called_once_with(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123",
            review_id=7,
        )
        provider.dispatch_repair.assert_not_called()

    def test_comment_event_returns_immediately_with_no_squash(self) -> None:
        """All issue_comment events now return EXIT_SUCCESS immediately — squash is via workflow_run."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=9,
                    user="copilot-pull-request-reviewer[bot]",
                    state="CHANGES_REQUESTED",
                    body="fix this",
                    commit_sha="oldsha",
                )
            ]
        )
        provider.count_commits_above_merge_base.return_value = 2
        payload = EventPayload(
            pr_number=42,
            head_sha="abc123",
            action="comment_created",
            sender_login="copilot[bot]",
        )

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        # Squash no longer happens from issue_comment events.
        provider.squash_post_repair.assert_not_called()
        provider.finalize_post_repair.assert_not_called()
        # No reviews listed — we exit before any review logic.
        provider.list_reviews.assert_not_called()

    def test_comment_event_skips_when_branch_is_already_squashed(self) -> None:
        """issue_comment events return EXIT_SUCCESS immediately regardless of commit count."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=9,
                    user="copilot-pull-request-reviewer[bot]",
                    state="CHANGES_REQUESTED",
                    body="fix this",
                    commit_sha="oldsha",
                )
            ]
        )
        provider.count_commits_above_merge_base.return_value = 1
        payload = EventPayload(
            pr_number=42,
            head_sha="abc123",
            action="comment_created",
            sender_login="copilot[bot]",
        )

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_not_called()
        provider.finalize_post_repair.assert_not_called()

    def test_comment_event_skips_when_no_prior_actionable_review(self) -> None:
        """issue_comment events return EXIT_SUCCESS immediately regardless of review state."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=9,
                    user="copilot-pull-request-reviewer[bot]",
                    state="APPROVED",
                    body="lgtm",
                    commit_sha="oldsha",
                )
            ]
        )
        payload = EventPayload(
            pr_number=42,
            head_sha="abc123",
            action="comment_created",
            sender_login="copilot[bot]",
        )

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.count_commits_above_merge_base.assert_not_called()
        provider.squash_post_repair.assert_not_called()

    def test_comment_event_skips_for_non_copilot_sender(self) -> None:
        provider = _make_provider()
        payload = EventPayload(
            pr_number=42,
            head_sha="abc123",
            action="comment_created",
            sender_login="human-reviewer",
        )
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.list_reviews.assert_not_called()

    def test_comment_event_skips_for_missing_sender(self) -> None:
        provider = _make_provider()
        payload = EventPayload(pr_number=42, head_sha="abc123", action="comment_created", sender_login="")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.list_reviews.assert_not_called()

    def test_comment_event_fork_pr_returns_success_immediately(self) -> None:
        """Fork PR guard no longer applies to issue_comment — all return EXIT_SUCCESS immediately."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="t",
                head_branch="b",
                head_sha="s",
                base_branch="main",
                head_repo_full_name="fork/repo",
                base_repo_full_name="owner/repo",
            ),
            reviews=[
                ReviewInfo(
                    id=9,
                    user="copilot-pull-request-reviewer[bot]",
                    state="CHANGES_REQUESTED",
                    body="fix this",
                    commit_sha="oldsha",
                )
            ],
        )
        payload = EventPayload(pr_number=42, head_sha="s", action="comment_created", sender_login="copilot[bot]")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.list_reviews.assert_not_called()
        provider.squash_post_repair.assert_not_called()

    def test_comment_event_ignore_label_returns_success_immediately(self) -> None:
        """Exclusion label guard no longer applies to issue_comment — all return EXIT_SUCCESS immediately."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="t",
                head_branch="b",
                head_sha="s",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                labels=["ai-pr-loop-ignore"],
            ),
            reviews=[
                ReviewInfo(
                    id=9,
                    user="copilot-pull-request-reviewer[bot]",
                    state="CHANGES_REQUESTED",
                    body="fix this",
                    commit_sha="oldsha",
                )
            ],
        )
        payload = EventPayload(pr_number=42, head_sha="s", action="comment_created", sender_login="copilot[bot]")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.list_reviews.assert_not_called()
        provider.squash_post_repair.assert_not_called()

    def test_comment_event_missing_auto_merge_allowed_returns_success_immediately(self) -> None:
        """Missing ai-auto-merge-allowed no longer has any effect on issue_comment events."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="t",
                head_branch="b",
                head_sha="s",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                labels=[],  # ai-auto-merge-allowed absent
            ),
            reviews=[
                ReviewInfo(
                    id=9,
                    user="copilot-pull-request-reviewer[bot]",
                    state="CHANGES_REQUESTED",
                    body="fix this",
                    commit_sha="oldsha",
                )
            ],
        )
        payload = EventPayload(pr_number=42, head_sha="s", action="comment_created", sender_login="copilot[bot]")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.list_reviews.assert_not_called()
        provider.squash_post_repair.assert_not_called()

    def test_comment_event_no_metadata_error_even_if_reviews_would_fail(self) -> None:
        """issue_comment events exit before listing reviews — API failures are irrelevant."""
        provider = _make_provider()
        provider.list_reviews.side_effect = RuntimeError("reviews api unavailable")
        payload = EventPayload(
            pr_number=42,
            head_sha="abc123",
            action="comment_created",
            sender_login="copilot[bot]",
        )
        result = run_ai_pr_loop(provider, payload)
        # Returns EXIT_SUCCESS immediately — does NOT error on list_reviews failure.
        assert result == EXIT_SUCCESS
        provider.list_reviews.assert_not_called()

    def test_comment_event_prior_commented_no_squash(self) -> None:
        """issue_comment events no longer squash even when prior COMMENTED review exists."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=9,
                    user="copilot-pull-request-reviewer[bot]",
                    state="COMMENTED",
                    body="",
                    commit_sha="oldsha",
                )
            ]
        )
        provider.count_commits_above_merge_base.return_value = 2
        payload = EventPayload(
            pr_number=42,
            head_sha="abc123",
            action="comment_created",
            sender_login="copilot[bot]",
        )
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_not_called()

    def test_comment_event_no_commit_count_failure(self) -> None:
        """issue_comment events exit before checking commit count."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=9,
                    user="copilot-pull-request-reviewer[bot]",
                    state="CHANGES_REQUESTED",
                    body="fix this",
                    commit_sha="oldsha",
                )
            ]
        )
        provider.count_commits_above_merge_base.side_effect = RuntimeError("git failure")
        payload = EventPayload(
            pr_number=42,
            head_sha="abc123",
            action="comment_created",
            sender_login="copilot[bot]",
        )
        result = run_ai_pr_loop(provider, payload)
        # Does NOT call count_commits_above_merge_base — exits immediately.
        assert result == EXIT_SUCCESS
        provider.count_commits_above_merge_base.assert_not_called()

    def test_comment_event_no_squash_failure(self) -> None:
        """issue_comment events no longer trigger squash — squash failure cannot occur."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=9,
                    user="copilot-pull-request-reviewer[bot]",
                    state="CHANGES_REQUESTED",
                    body="fix this",
                    commit_sha="oldsha",
                )
            ]
        )
        provider.count_commits_above_merge_base.return_value = 2
        provider.squash_post_repair.side_effect = RuntimeError("squash failed")
        payload = EventPayload(
            pr_number=42,
            head_sha="abc123",
            action="comment_created",
            sender_login="copilot[bot]",
        )
        result = run_ai_pr_loop(provider, payload)
        # No longer EXIT_MERGE_BLOCKED — issue_comment returns EXIT_SUCCESS immediately.
        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_not_called()

    def test_ci_completion_prior_commit_commented_with_zero_inline_comments_waits(self) -> None:
        """CI completion + COMMENTED with 0 inline comments on prior commit → requests review."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=7,
                    user="copilot-pull-request-reviewer[bot]",
                    state="COMMENTED",
                    body="lgtm",
                    commit_sha="oldsha",
                )
            ]
        )
        provider.list_review_comments.return_value = []
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.finalize_post_repair.assert_not_called()
        provider.dispatch_repair.assert_not_called()
        provider.request_reviewer.assert_called_once_with(42, COPILOT_REVIEWER_LOGIN)

    def test_ci_completion_prior_commit_list_review_comments_raises_treated_as_actionable(self) -> None:
        """list_review_comments error on prior-commit COMMENTED review → fail-closed, finalize."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=7,
                    user="copilot-pull-request-reviewer[bot]",
                    state="COMMENTED",
                    body="",
                    commit_sha="oldsha",
                )
            ]
        )
        provider.list_review_comments.side_effect = RuntimeError("api failure")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.finalize_post_repair.assert_called_once_with(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123",
            review_id=7,
        )

    def test_ci_completion_prior_commit_finalization_failure_blocks(self) -> None:
        """finalize_post_repair failure for prior-commit review returns EXIT_MERGE_BLOCKED."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=7,
                    user="copilot-pull-request-reviewer[bot]",
                    state="CHANGES_REQUESTED",
                    body="fix this",
                    commit_sha="oldsha",
                )
            ]
        )
        provider.finalize_post_repair.side_effect = RuntimeError("finalization failed")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_MERGE_BLOCKED

    def test_ci_completion_no_copilot_review_anywhere_requests_review(self) -> None:
        """CI completion + no Copilot review on any commit → requests review to unblock gate."""
        provider = _make_provider(
            reviews=[ReviewInfo(id=1, user="human-reviewer", state="APPROVED", body="looks good")]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.finalize_post_repair.assert_not_called()
        provider.dispatch_repair.assert_not_called()
        provider.request_reviewer.assert_called_once_with(42, COPILOT_REVIEWER_LOGIN)

    def test_ci_completion_no_copilot_review_request_reviewer_failure_is_non_blocking(self) -> None:
        """request_reviewer failure in awaiting_copilot_review_after_ci path is non-blocking."""
        provider = _make_provider(
            reviews=[ReviewInfo(id=1, user="human-reviewer", state="APPROVED", body="looks good")]
        )
        provider.request_reviewer.side_effect = RuntimeError("API error")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.request_reviewer.assert_called_once_with(42, COPILOT_REVIEWER_LOGIN)

    def test_ci_completion_wip_title_does_not_request_review(self) -> None:
        """CI completion bails early for non-draft [WIP] PRs instead of requesting review."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="[WIP] feat: test",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
            ),
            reviews=[ReviewInfo(id=1, user="human-reviewer", state="APPROVED", body="looks good")],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.request_reviewer.assert_not_called()
        provider.finalize_post_repair.assert_not_called()
        provider.dispatch_repair.assert_not_called()

    def test_ci_completion_green_without_actionable_review_requests_review(self) -> None:
        """CI completion with green checks and no actionable Copilot feedback requests review."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=3, user="copilot-pull-request-reviewer[bot]", state="COMMENTED", body="lgtm", commit_sha="oldsha"
                )
            ]
        )
        provider.list_review_comments.return_value = []
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.dispatch_repair.assert_not_called()
        provider.finalize_post_repair.assert_not_called()
        provider.approve_pr.assert_not_called()
        provider.merge_pr.assert_not_called()
        provider.request_reviewer.assert_called_once_with(42, COPILOT_REVIEWER_LOGIN)

    def test_ci_completion_green_with_clean_copilot_review_on_head_auto_approves(self) -> None:
        """CI completion + clean Copilot review on current HEAD auto-approves to re-run review gate."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=3,
                    user="copilot-pull-request-reviewer[bot]",
                    state="COMMENTED",
                    body="lgtm",
                    commit_sha="abc123",
                )
            ]
        )
        provider.list_review_comments.return_value = []
        provider.approve_pr.return_value = True
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.approve_pr.assert_called_once_with(42, "abc123", "Auto-approved by AI PR loop")
        provider.request_reviewer.assert_not_called()
        provider.finalize_post_repair.assert_not_called()
        provider.merge_pr.assert_not_called()

    def test_ci_completion_empty_commit_sha_review_treated_as_on_head(self) -> None:
        """Copilot review with empty commit_sha is treated as applying to HEAD (auto-approves)."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=3,
                    user="copilot-pull-request-reviewer[bot]",
                    state="COMMENTED",
                    body="lgtm",
                    commit_sha="",
                )
            ]
        )
        provider.list_review_comments.return_value = []
        provider.approve_pr.return_value = True
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.approve_pr.assert_called_once_with(42, "abc123", "Auto-approved by AI PR loop")

    def test_ci_completion_clean_copilot_review_on_head_approval_skipped_short_circuits(self) -> None:
        """Skipped approval in clean-review CI path short-circuits without requesting another review."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=3,
                    user="copilot-pull-request-reviewer[bot]",
                    state="COMMENTED",
                    body="lgtm",
                    commit_sha="abc123",
                )
            ]
        )
        provider.list_review_comments.return_value = []
        provider.approve_pr.return_value = False
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.approve_pr.assert_called_once_with(42, "abc123", "Auto-approved by AI PR loop")
        provider.request_reviewer.assert_not_called()
        provider.finalize_post_repair.assert_not_called()
        provider.merge_pr.assert_not_called()

    def test_ci_completion_clean_copilot_review_on_head_approval_failure_blocks(self) -> None:
        """Approval errors in CI completion clean-review path return EXIT_MERGE_BLOCKED."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=3,
                    user="copilot-pull-request-reviewer[bot]",
                    state="APPROVED",
                    body="lgtm",
                    commit_sha="abc123",
                )
            ]
        )
        provider.approve_pr.side_effect = RuntimeError("approval failed")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_MERGE_BLOCKED
        provider.request_reviewer.assert_not_called()
        provider.merge_pr.assert_not_called()

    def test_copilot_commented_without_inline_comments_does_not_dispatch(self) -> None:
        """Copilot COMMENTED review without inline comments is not actionable."""
        provider = _make_provider(
            reviews=[ReviewInfo(id=3, user="copilot-pull-request-reviewer[bot]", state="COMMENTED", body="lgtm")]
        )
        provider.list_review_comments.return_value = []
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.dispatch_repair.assert_not_called()
        provider.merge_pr.assert_called_once()

    def test_copilot_commented_superseded_by_approval(self) -> None:
        """Older Copilot COMMENTED is superseded by a later APPROVED from same user."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(id=2, user="copilot-pull-request-reviewer[bot]", state="COMMENTED", body="fix"),
                ReviewInfo(id=8, user="copilot-pull-request-reviewer[bot]", state="APPROVED", body="lgtm"),
            ]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.dispatch_repair.assert_not_called()
        provider.merge_pr.assert_called_once()

    def test_copilot_commented_with_copilot_login_alias(self) -> None:
        """COMMENTED review from 'Copilot' login (alias) with comments triggers repair."""
        provider = _make_provider(reviews=[ReviewInfo(id=4, user="Copilot", state="COMMENTED", body="")])
        provider.dispatch_repair.return_value = 200
        provider.list_review_comments.return_value = ["please fix this"]
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_REPAIR_DISPATCHED
        provider.dispatch_repair.assert_called_once()

    def test_copilot_alias_commented_superseded_by_different_alias_approval(self) -> None:
        """COMMENTED from one Copilot alias is superseded by APPROVED from a different alias."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(id=1, user="Copilot", state="COMMENTED", body="check this"),
                ReviewInfo(id=5, user="copilot-pull-request-reviewer[bot]", state="APPROVED", body="lgtm"),
            ]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.dispatch_repair.assert_not_called()
        provider.merge_pr.assert_called_once()

    def test_copilot_commented_list_review_comments_raises_treated_as_actionable(self) -> None:
        """list_review_comments() raising for a COMMENTED review is treated as actionable (fail closed)."""
        provider = _make_provider(
            reviews=[ReviewInfo(id=3, user="copilot-pull-request-reviewer[bot]", state="COMMENTED", body="")]
        )
        provider.list_review_comments.side_effect = RuntimeError("network error")
        provider.dispatch_repair.return_value = 200
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_REPAIR_DISPATCHED
        provider.dispatch_repair.assert_called_once()
        provider.merge_pr.assert_not_called()

    def test_copilot_alias_changes_requested_superseded_by_different_alias_approval(self) -> None:
        """CHANGES_REQUESTED from one Copilot alias is superseded by APPROVED from a different alias."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(id=2, user="Copilot", state="CHANGES_REQUESTED", body="fix it"),
                ReviewInfo(id=8, user="copilot-pull-request-reviewer[bot]", state="APPROVED", body="lgtm"),
            ]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.dispatch_repair.assert_not_called()
        provider.merge_pr.assert_called_once()

    def test_draft_pr_publishes_and_awaits_review(self) -> None:
        """Draft PRs with non-WIP title and code changes are published and Copilot is requested."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="feat: test",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                is_draft=True,
                labels=["ai-auto-merge-allowed"],
            ),
            files=["src/main.py"],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        # Draft review requests must only happen after squash + publish so the
        # first explicit request cannot race ahead of the ready-for-review flow.
        relevant_calls = [
            call
            for call in provider.mock_calls
            if call[0] in {"squash_before_publish", "publish_pr", "request_reviewer"}
        ]
        assert [call[0] for call in relevant_calls] == [
            "squash_before_publish",
            "publish_pr",
            "request_reviewer",
        ]
        provider.squash_before_publish.assert_called_once_with(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123",
        )
        provider.publish_pr.assert_called_once_with(42)
        provider.request_reviewer.assert_called_once_with(42, COPILOT_REVIEWER_LOGIN)
        provider.approve_pr.assert_not_called()
        provider.merge_pr.assert_not_called()

    def test_draft_pr_with_wip_title_not_published(self) -> None:
        """Draft PRs with [WIP] title are not published — they are not ready yet."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="[WIP] feat: work in progress",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                is_draft=True,
                labels=["ai-auto-merge-allowed"],
            ),
            files=["src/main.py"],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.publish_pr.assert_not_called()
        provider.approve_pr.assert_not_called()
        provider.merge_pr.assert_not_called()

    def test_draft_pr_with_wip_title_case_insensitive(self) -> None:
        """[wip] prefix (any case) blocks publishing."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="[wip] feat: lowercase wip",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                is_draft=True,
                labels=["ai-auto-merge-allowed"],
            ),
            files=["src/main.py"],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.publish_pr.assert_not_called()
        provider.merge_pr.assert_not_called()

    def test_draft_pr_with_no_files_not_published(self) -> None:
        """Draft PRs with no changed files are not published — no code changes yet."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="feat: test",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                is_draft=True,
                labels=["ai-auto-merge-allowed"],
            ),
            files=[],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.publish_pr.assert_not_called()
        provider.approve_pr.assert_not_called()
        provider.merge_pr.assert_not_called()

    def test_non_draft_pr_with_wip_title_does_not_request_review(self) -> None:
        """Non-draft [WIP] PRs are treated as not ready and do not request review."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="[WIP] feat: work in progress",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
            ),
            reviews=[],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.request_reviewer.assert_not_called()
        provider.approve_pr.assert_not_called()
        provider.merge_pr.assert_not_called()

    def test_non_draft_pr_with_no_files_does_not_request_review(self) -> None:
        """Non-draft PRs with no changed files are treated as not ready."""
        provider = _make_provider(files=[], reviews=[])
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.request_reviewer.assert_not_called()
        provider.approve_pr.assert_not_called()
        provider.merge_pr.assert_not_called()

    def test_draft_pr_publish_failure_blocks(self) -> None:
        """Failure to publish a draft PR returns EXIT_MERGE_BLOCKED."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="feat: test",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                is_draft=True,
                labels=["ai-auto-merge-allowed"],
            ),
            files=["src/main.py"],
        )
        provider.publish_pr.side_effect = RuntimeError("gh pr ready failed")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_MERGE_BLOCKED
        provider.approve_pr.assert_not_called()
        provider.merge_pr.assert_not_called()

    def test_draft_pr_review_request_failure_still_waits(self) -> None:
        """After publish succeeds, review-request failures are non-blocking for draft flow."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="feat: test",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                is_draft=True,
                labels=["ai-auto-merge-allowed"],
            ),
            files=["src/main.py"],
        )
        provider.request_reviewer.side_effect = RuntimeError("request failed")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.squash_before_publish.assert_called_once()
        provider.publish_pr.assert_called_once_with(42)
        provider.approve_pr.assert_not_called()
        provider.merge_pr.assert_not_called()

    def test_draft_pr_publish_skips_duplicate_request_when_already_requested(self) -> None:
        """Draft publish keeps squash/publish flow but skips redundant safety-net requests."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="feat: test",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                requested_reviewers=[COPILOT_REVIEWER_LOGIN],
                is_draft=True,
                labels=["ai-auto-merge-allowed"],
            ),
            files=["src/main.py"],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.squash_before_publish.assert_called_once()
        provider.publish_pr.assert_called_once_with(42)
        provider.request_reviewer.assert_not_called()
        provider.approve_pr.assert_not_called()
        provider.merge_pr.assert_not_called()

    def test_draft_pr_squash_failure_blocks_publish(self) -> None:
        """Squash errors before publish block draft publication."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="feat: test",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                is_draft=True,
                labels=["ai-auto-merge-allowed"],
            ),
            files=["src/main.py"],
        )
        provider.squash_before_publish.side_effect = RuntimeError("squash failed")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_MERGE_BLOCKED
        provider.publish_pr.assert_not_called()
        provider.request_reviewer.assert_not_called()

    def test_draft_pr_squash_failure_recorded_in_summary(self) -> None:
        """When squash fails, summary reports the blocked publish and squash error."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="feat: test",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                is_draft=True,
                labels=["ai-auto-merge-allowed"],
            ),
            files=["src/main.py"],
        )
        provider.squash_before_publish.side_effect = RuntimeError("squash boom")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)
        assert summary.get("squash_error") == "squash boom"
        assert summary.get("decision") == "error"
        assert summary.get("reason") == "squash_before_publish_failed"
        assert summary.get("exit_code") == EXIT_MERGE_BLOCKED

    def test_no_copilot_review_requests_review_and_waits(self) -> None:
        """When no Copilot review exists, requests one and returns SUCCESS without merging."""
        provider = _make_provider(reviews=[])
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.request_reviewer.assert_called_once_with(42, COPILOT_REVIEWER_LOGIN)
        provider.approve_pr.assert_not_called()
        provider.merge_pr.assert_not_called()

    def test_no_copilot_review_skips_duplicate_request_when_already_requested(self) -> None:
        """Pending requested_reviewers entry suppresses redundant Copilot review requests."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="feat: test",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                requested_reviewers=[COPILOT_REVIEWER_LOGIN],
            ),
            reviews=[],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.request_reviewer.assert_not_called()
        provider.approve_pr.assert_not_called()
        provider.merge_pr.assert_not_called()

    def test_ci_completion_no_reviewable_files_comment_does_not_rerequest(self) -> None:
        """A prior 'wasn't able to review any files' Copilot review should not be re-requested."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=3,
                    user="copilot-pull-request-reviewer[bot]",
                    state="COMMENTED",
                    body="Copilot wasn't able to review any files in this pull request.",
                    commit_sha="abc123",
                )
            ]
        )
        provider.list_review_comments.return_value = []
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.request_reviewer.assert_not_called()
        provider.dispatch_repair.assert_not_called()
        provider.finalize_post_repair.assert_not_called()

    def test_copilot_review_on_previous_sha_requests_fresh_review(self) -> None:
        """Copilot review on previous commit does not satisfy current-head review requirement."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=1,
                    user="copilot-pull-request-reviewer[bot]",
                    state="APPROVED",
                    body="lgtm",
                    commit_sha="oldsha",
                )
            ]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.request_reviewer.assert_called_once_with(42, COPILOT_REVIEWER_LOGIN)
        provider.merge_pr.assert_not_called()

    def test_no_copilot_review_with_human_approval_still_waits(self) -> None:
        """Even with a human approval, no Copilot review means the loop waits for one."""
        provider = _make_provider(reviews=[ReviewInfo(id=1, user="reviewer", state="APPROVED", body="lgtm")])
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.request_reviewer.assert_called_once_with(42, COPILOT_REVIEWER_LOGIN)
        provider.merge_pr.assert_not_called()

    def test_no_copilot_review_request_failure_still_waits(self) -> None:
        """Review-request failures are non-blocking while waiting for initial Copilot review."""
        provider = _make_provider(reviews=[])
        provider.request_reviewer.side_effect = RuntimeError("request failed")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.approve_pr.assert_not_called()
        provider.merge_pr.assert_not_called()

    def test_copilot_approved_proceeds_to_merge(self) -> None:
        """Copilot APPROVED review allows the orchestrator to proceed to merge."""
        provider = _make_provider(
            reviews=[ReviewInfo(id=1, user="copilot-pull-request-reviewer[bot]", state="APPROVED", body="lgtm")]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.merge_pr.assert_called_once()
        provider.dispatch_repair.assert_not_called()

    def test_ready_pr_non_review_event_waits_for_review_trigger(self) -> None:
        """Even when green, non-review events wait for pull_request_review before merging."""
        provider = _make_provider(
            reviews=[ReviewInfo(id=1, user="copilot-pull-request-reviewer[bot]", state="APPROVED", body="lgtm")]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="opened")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.merge_pr.assert_not_called()

    def test_dismissed_copilot_review_treated_as_no_review(self) -> None:
        """A DISMISSED Copilot review is not an effective review — the loop requests a new one."""
        provider = _make_provider(
            reviews=[ReviewInfo(id=1, user="copilot-pull-request-reviewer[bot]", state="DISMISSED", body="")]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.request_reviewer.assert_called_once_with(42, COPILOT_REVIEWER_LOGIN)
        provider.approve_pr.assert_not_called()
        provider.merge_pr.assert_not_called()

    def test_pending_copilot_review_treated_as_no_review(self) -> None:
        """A PENDING Copilot review is not an effective review — the loop requests a new one."""
        provider = _make_provider(
            reviews=[ReviewInfo(id=1, user="copilot-pull-request-reviewer[bot]", state="PENDING", body="")]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.request_reviewer.assert_called_once_with(42, COPILOT_REVIEWER_LOGIN)
        provider.approve_pr.assert_not_called()
        provider.merge_pr.assert_not_called()


class TestRunAIPRLoopDecisionSummary:
    """Verify structured decision summary is emitted in key scenarios."""

    def test_merged_pr_emits_summary(self) -> None:
        provider = _make_provider()
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "merged"
        assert summary["exit_code"] == EXIT_SUCCESS
        assert summary["event"]["pr_number"] == 42
        assert summary["reviews"]["has_approval"] is True
        assert summary["ci"]["pending"] is False
        assert summary["repair"]["needed"] is False

    def test_guard_blocked_emits_summary(self) -> None:
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="t",
                head_branch="b",
                head_sha="s",
                base_branch="main",
                head_repo_full_name="fork/repo",
                base_repo_full_name="owner/repo",
            )
        )
        payload = EventPayload(pr_number=42, head_sha="s")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "blocked"
        assert summary["reason"] == "fork_pr"
        assert summary["exit_code"] == EXIT_GUARD_BLOCKED

    def test_pending_checks_emits_wait_summary(self) -> None:
        provider = _make_provider(check_runs=[CheckRunStatus(id=1, name="Tests ✅", status="in_progress")])
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "wait"
        assert summary["reason"] == "checks_pending"
        assert summary["ci"]["pending"] is True

    def test_repair_dispatched_emits_summary(self) -> None:
        provider = _make_provider(
            check_runs=[
                CheckRunStatus(id=1, name="Tests ✅", status="completed", conclusion="success"),
                CheckRunStatus(id=2, name="Workflow Tests ✅", status="completed", conclusion="failure"),
            ],
            reviews=[],
        )
        provider.dispatch_repair.return_value = 200
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "repair_dispatched"
        assert summary["exit_code"] == EXIT_REPAIR_DISPATCHED
        assert summary["repair"]["needed"] is True
        assert summary["repair"]["type"] == "ci"
        assert "Workflow Tests ✅" in summary["repair"]["failed_checks"]
        assert summary["repair_cycle"]["count"] == 1

    def test_repair_dispatched_summary_survives_cycle_increment_failure(self) -> None:
        """Repair dispatch still succeeds when cycle tracking update fails."""
        provider = _make_provider(
            check_runs=[
                CheckRunStatus(id=1, name="Tests ✅", status="completed", conclusion="success"),
                CheckRunStatus(id=2, name="Workflow Tests ✅", status="completed", conclusion="failure"),
            ],
            reviews=[],
        )
        provider.dispatch_repair.return_value = 200
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")

        with patch(
            "agentic_devtools.cli.ci.orchestrator.increment_cycle_count",
            side_effect=RuntimeError("cycle store failed"),
        ):
            summary = _capture_summary(provider, payload)

        assert summary["decision"] == "repair_dispatched"
        assert summary["exit_code"] == EXIT_REPAIR_DISPATCHED
        assert "repair_cycle" not in summary

    def test_post_repair_soft_finalized_emits_summary(self) -> None:
        provider = _make_provider(
            reviews=[ReviewInfo(id=8, user="copilot-pull-request-reviewer[bot]", state="CHANGES_REQUESTED", body="fix")]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "post_repair_soft_finalized"
        assert summary["exit_code"] == EXIT_SUCCESS
        assert summary["post_repair"]["finalized"] is True

    def test_comment_event_post_repair_squash_not_needed_via_workflow_run_emits_summary(self) -> None:
        """All issue_comment events now emit squash_via_workflow_run reason."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=8,
                    user="copilot-pull-request-reviewer[bot]",
                    state="CHANGES_REQUESTED",
                    body="fix",
                    commit_sha="oldsha",
                )
            ]
        )
        provider.count_commits_above_merge_base.return_value = 3
        payload = EventPayload(
            pr_number=42,
            head_sha="abc123",
            action="comment_created",
            sender_login="copilot[bot]",
        )
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "post_repair_squash_not_needed"
        assert summary["reason"] == "squash_via_workflow_run"
        assert summary["post_repair"]["phase"] == "comment_noop"
        assert summary["exit_code"] == EXIT_SUCCESS

    def test_comment_event_post_repair_squash_not_needed_emits_summary(self) -> None:
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=8,
                    user="copilot-pull-request-reviewer[bot]",
                    state="CHANGES_REQUESTED",
                    body="fix",
                    commit_sha="oldsha",
                )
            ]
        )
        provider.count_commits_above_merge_base.return_value = 1
        payload = EventPayload(
            pr_number=42,
            head_sha="abc123",
            action="comment_created",
            sender_login="copilot[bot]",
        )
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "post_repair_squash_not_needed"
        assert summary["reason"] == "squash_via_workflow_run"
        assert summary["post_repair"]["phase"] == "comment_noop"
        assert summary["exit_code"] == EXIT_SUCCESS


class TestCountCommitsAboveMergeBase:
    def test_returns_one_when_provider_has_no_commit_counter(self) -> None:
        provider = cast(CIPlatformProvider, object())

        count = _count_commits_above_merge_base(
            provider,
            base_branch="main",
            head_sha="abc123",
        )
        assert count == 1

    def test_delegates_to_provider_commit_counter(self) -> None:
        class _CounterProvider:
            def count_commits_above_merge_base(self, *, base_branch: str, head_sha: str) -> int:
                assert base_branch == "main"
                assert head_sha == "abc123"
                return 5

        count = _count_commits_above_merge_base(
            cast(CIPlatformProvider, _CounterProvider()),
            base_branch="main",
            head_sha="abc123",
        )
        assert count == 5

    def test_ci_completion_repair_summary_survives_cycle_increment_failure(self) -> None:
        """CI-completion repair dispatch still succeeds when cycle tracking update fails."""
        provider = _make_provider(
            check_runs=[CheckRunStatus(id=2, name="Workflow Tests ✅", status="completed", conclusion="failure")],
            reviews=[],
        )
        provider.dispatch_repair.return_value = 200
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        with patch(
            "agentic_devtools.cli.ci.orchestrator.increment_cycle_count",
            side_effect=RuntimeError("cycle store failed"),
        ):
            summary = _capture_summary(provider, payload)

        assert summary["decision"] == "repair_dispatched"
        assert summary["exit_code"] == EXIT_REPAIR_DISPATCHED
        assert "repair_cycle" not in summary

    def test_ci_completion_without_actionable_review_emits_awaiting_copilot_review_after_ci_summary(self) -> None:
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=8, user="copilot-pull-request-reviewer[bot]", state="COMMENTED", body="lgtm", commit_sha="oldsha"
                )
            ]
        )
        provider.list_review_comments.return_value = []
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "awaiting_copilot_review_after_ci"
        assert summary["exit_code"] == EXIT_SUCCESS

    def test_ci_completion_clean_review_on_head_emits_approved_awaiting_review_gate_summary(self) -> None:
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=8,
                    user="copilot-pull-request-reviewer[bot]",
                    state="COMMENTED",
                    body="lgtm",
                    commit_sha="abc123",
                )
            ]
        )
        provider.list_review_comments.return_value = []
        provider.approve_pr.return_value = True
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "approved_awaiting_review_gate"
        assert summary["exit_code"] == EXIT_SUCCESS
        assert summary["auto_approved"] is True

    def test_ci_completion_clean_review_on_head_skipped_approval_emits_approval_skipped_reason(self) -> None:
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=8,
                    user="copilot-pull-request-reviewer[bot]",
                    state="COMMENTED",
                    body="lgtm",
                    commit_sha="abc123",
                )
            ]
        )
        provider.list_review_comments.return_value = []
        provider.approve_pr.return_value = False
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "awaiting_copilot_review_after_ci"
        assert summary["reason"] == "approval_skipped"
        assert summary["exit_code"] == EXIT_SUCCESS
        assert "auto_approved" not in summary

    def test_no_pr_number_emits_summary(self) -> None:
        provider = MagicMock()
        payload = EventPayload(pr_number=0)
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "skip"
        assert summary["reason"] == "no_pr_number"

    def test_missing_auto_merge_allowed_label_emits_skip_merge_summary(self) -> None:
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="t",
                head_branch="b",
                head_sha="s",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                labels=[],
            )
        )
        payload = EventPayload(pr_number=42, head_sha="s")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "skip_merge"
        assert summary["reason"] == "missing_auto_merge_allowed_label"

    def test_summary_includes_ci_failed_check_names(self) -> None:
        provider = _make_provider(
            check_runs=[
                CheckRunStatus(id=1, name="Tests ✅", status="completed", conclusion="failure"),
                CheckRunStatus(id=2, name="Markdown Lint ✅", status="completed", conclusion="success"),
                CheckRunStatus(id=3, name="Copilot Review ✅", status="completed", conclusion="failure"),
            ],
            reviews=[],
        )
        provider.dispatch_repair.return_value = 200
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)

        assert "Tests ✅" in summary["ci"]["failed"]
        assert "Markdown Lint ✅" not in summary["ci"]["failed"]
        assert "Copilot Review ✅" not in summary["ci"]["failed"]
        assert summary["ci"]["ignored"] == 1

    def test_unknown_check_conclusion_emits_blocked_summary(self) -> None:
        provider = _make_provider(
            check_runs=[
                CheckRunStatus(id=1, name="Tests ✅", status="completed", conclusion="cancelled"),
            ]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "blocked"
        assert summary["reason"] == "unknown_check_conclusions"
        assert summary["exit_code"] == EXIT_MERGE_BLOCKED

    def test_pr_files_error_emits_error_summary(self) -> None:
        provider = _make_provider()
        provider.list_pr_files.side_effect = RuntimeError("api unavailable")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "error"
        assert summary["reason"] == "pr_files_listing_failed"
        assert summary["error"] == "api unavailable"
        assert summary["exit_code"] == EXIT_METADATA_FAILED

    def test_repair_dispatch_failure_emits_failure_reason(self) -> None:
        provider = _make_provider(
            check_runs=[CheckRunStatus(id=2, name="Workflow Tests ✅", status="completed", conclusion="failure")],
            reviews=[],
        )
        provider.dispatch_repair.side_effect = RuntimeError("dispatch endpoint timeout")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "repair_failed"
        assert summary["reason"] == "dispatch endpoint timeout"
        assert summary["exit_code"] == EXIT_MERGE_BLOCKED

    def test_check_runs_error_emits_error_summary(self) -> None:
        provider = _make_provider()
        provider.list_check_runs.side_effect = RuntimeError("checks api unavailable")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "error"
        assert summary["reason"] == "check_runs_listing_failed"
        assert summary["error"] == "checks api unavailable"
        assert summary["exit_code"] == EXIT_METADATA_FAILED

    def test_list_reviews_error_emits_error_summary(self) -> None:
        provider = _make_provider()
        provider.list_reviews.side_effect = RuntimeError("reviews api unavailable")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "error"
        assert summary["reason"] == "reviews_listing_failed"
        assert summary["error"] == "reviews api unavailable"
        assert summary["exit_code"] == EXIT_METADATA_FAILED

    def test_approval_error_emits_error_summary(self) -> None:
        provider = _make_provider(
            reviews=[ReviewInfo(id=1, user="copilot-pull-request-reviewer[bot]", state="COMMENTED", body="lgtm")]
        )
        provider.list_review_comments.return_value = []
        provider.approve_pr.side_effect = RuntimeError("approval endpoint unavailable")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "error"
        assert summary["reason"] == "approval_failed"
        assert summary["error"] == "approval endpoint unavailable"
        assert summary["exit_code"] == EXIT_MERGE_BLOCKED

    def test_approval_skipped_emits_blocked_summary(self) -> None:
        provider = _make_provider(
            reviews=[ReviewInfo(id=1, user="copilot-pull-request-reviewer[bot]", state="COMMENTED", body="lgtm")]
        )
        provider.list_review_comments.return_value = []
        provider.approve_pr.return_value = False
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "blocked"
        assert summary["reason"] == "approval_skipped"
        assert summary["auto_approved"] is False
        assert summary["exit_code"] == EXIT_MERGE_BLOCKED

    def test_merge_error_emits_error_summary(self) -> None:
        provider = _make_provider()
        provider.merge_pr.side_effect = RuntimeError("merge conflict")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "error"
        assert summary["reason"] == "merge_failed"
        assert summary["error"] == "merge conflict"
        assert summary["exit_code"] == EXIT_MERGE_BLOCKED

    def test_deduplication_check_error_emits_error_summary(self) -> None:
        provider = _make_provider()
        provider.find_comment.side_effect = RuntimeError("dedup api unavailable")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="synchronize")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "error"
        assert summary["reason"] == "deduplication_failed"
        assert summary["error"] == "dedup api unavailable"
        assert summary["exit_code"] == EXIT_METADATA_FAILED

    def test_cycle_limit_check_error_emits_error_summary(self) -> None:
        provider = _make_provider()
        # First find_comment (dedup) returns None so dedup succeeds, second (cycle) raises
        provider.find_comment.side_effect = [
            None,  # dedup: no existing marker → calls post_comment; succeeds
            RuntimeError("cycle api unavailable"),  # cycle: raises
        ]
        payload = EventPayload(pr_number=42, head_sha="abc123", action="synchronize")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "error"
        assert summary["reason"] == "cycle_limit_check_failed"
        assert summary["error"] == "cycle api unavailable"
        assert summary["exit_code"] == EXIT_METADATA_FAILED

    def test_draft_pr_emits_published_awaiting_review_summary(self) -> None:
        """Draft PR publish emits 'published_awaiting_review' decision in summary."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="feat: test",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                is_draft=True,
                labels=["ai-auto-merge-allowed"],
            ),
            files=["src/main.py"],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "published_awaiting_review"
        assert summary["exit_code"] == EXIT_SUCCESS

    def test_wip_draft_pr_emits_draft_not_ready_summary(self) -> None:
        """[WIP] draft PR emits 'draft_not_ready' with reason 'wip_title'."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="[WIP] feat: work in progress",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                is_draft=True,
                labels=["ai-auto-merge-allowed"],
            ),
            files=["src/main.py"],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "draft_not_ready"
        assert summary["reason"] == "wip_title"
        assert summary["exit_code"] == EXIT_SUCCESS

    def test_no_files_draft_pr_emits_draft_not_ready_summary(self) -> None:
        """Draft PR with no changed files emits 'draft_not_ready' with reason 'no_changes'."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="feat: test",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                is_draft=True,
                labels=["ai-auto-merge-allowed"],
            ),
            files=[],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "draft_not_ready"
        assert summary["reason"] == "no_changes"
        assert summary["exit_code"] == EXIT_SUCCESS

    def test_no_copilot_review_emits_awaiting_copilot_review_summary(self) -> None:
        """No Copilot review emits 'awaiting_copilot_review' decision in summary."""
        provider = _make_provider(reviews=[])
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "awaiting_copilot_review"
        assert summary["exit_code"] == EXIT_SUCCESS

    def test_ci_completion_no_review_emits_awaiting_copilot_review_after_ci_summary(self) -> None:
        """CI completion with no Copilot review emits 'awaiting_copilot_review_after_ci' decision."""
        provider = _make_provider(
            reviews=[ReviewInfo(id=1, user="human-reviewer", state="APPROVED", body="looks good")]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "awaiting_copilot_review_after_ci"
        assert summary["exit_code"] == EXIT_SUCCESS

    def test_ci_completion_draft_pr_waits_for_publish_without_requesting_review(self) -> None:
        """CI completion does not request Copilot review while the PR is still draft."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="feat: draft",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                is_draft=True,
            ),
            reviews=[ReviewInfo(id=1, user="human-reviewer", state="APPROVED", body="looks good")],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "draft_not_ready"
        assert summary["reason"] == "awaiting_publish"
        assert summary["exit_code"] == EXIT_SUCCESS
        provider.request_reviewer.assert_not_called()

    def test_ci_completion_copilot_already_requested_emits_skip_reason(self) -> None:
        """CI completion path emits skip reason when Copilot is already requested."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="feat: test",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                labels=["ai-auto-merge-allowed"],
                requested_reviewers=[COPILOT_REVIEWER_LOGIN],
            ),
            reviews=[ReviewInfo(id=1, user="human-reviewer", state="APPROVED", body="looks good")],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "awaiting_copilot_review_after_ci"
        assert summary["reason"] == "copilot_already_requested"
        assert summary["exit_code"] == EXIT_SUCCESS

    def test_no_copilot_review_copilot_already_requested_emits_skip_reason(self) -> None:
        """Step 7b emits skip reason when Copilot is already a requested reviewer."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="feat: test",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                labels=["ai-auto-merge-allowed"],
                requested_reviewers=[COPILOT_REVIEWER_LOGIN],
            ),
            reviews=[ReviewInfo(id=1, user="human-reviewer", state="APPROVED", body="looks good")],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "awaiting_copilot_review"
        assert summary["reason"] == "copilot_already_requested"
        assert summary["exit_code"] == EXIT_SUCCESS

    def test_ci_completion_pre_dedup_list_reviews_failure(self) -> None:
        """CI completion with failed checks errors when pre-dedup list_reviews fails."""
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="feat: test",
                head_branch="feature/test",
                head_sha="abc123",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                labels=["ai-auto-merge-allowed"],
                requested_reviewers=[COPILOT_REVIEWER_LOGIN],
            ),
            check_runs=[CheckRunStatus(id=1, name="Tests ✅", status="completed", conclusion="failure")],
            reviews=[],
        )
        # The pre-dedup list_reviews call (line 630) throws
        provider.list_reviews.side_effect = RuntimeError("API timeout")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "error"
        assert summary["reason"] == "reviews_listing_failed"
        assert summary["exit_code"] == EXIT_METADATA_FAILED
