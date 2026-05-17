"""Tests for run_ai_pr_loop() orchestrator state machine."""

import json
from io import StringIO
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.models import (
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
    run_ai_pr_loop,
)


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
        labels=[],
    )
    provider.list_pr_files.return_value = files if files is not None else ["src/main.py"]
    provider.list_check_runs.return_value = (
        check_runs
        if check_runs is not None
        else [CheckRunStatus(id=1, name="ci", status="completed", conclusion="success")]
    )
    provider.list_reviews.return_value = (
        reviews if reviews is not None else [ReviewInfo(id=1, user="reviewer", state="APPROVED")]
    )
    provider.find_comment.return_value = None
    provider.post_comment.return_value = 100
    provider.merge_pr.return_value = None
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
        payload = EventPayload(pr_number=42, head_sha="abc123")

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
        payload = EventPayload(pr_number=42, head_sha="abc123")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_GUARD_BLOCKED

    def test_docker_files_blocked(self) -> None:
        provider = _make_provider(files=["Dockerfile"])
        payload = EventPayload(pr_number=42, head_sha="abc123")
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

    def test_do_not_merge_label_prevents_merge(self) -> None:
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="t",
                head_branch="b",
                head_sha="s",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                labels=["do-not-auto-merge"],
            )
        )
        payload = EventPayload(pr_number=42, head_sha="s")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.merge_pr.assert_not_called()

    def test_pending_checks_waits(self) -> None:
        provider = _make_provider(check_runs=[CheckRunStatus(id=1, name="ci", status="in_progress")])
        payload = EventPayload(pr_number=42, head_sha="abc123")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.merge_pr.assert_not_called()

    def test_auto_approves_when_no_approval(self) -> None:
        provider = _make_provider(reviews=[])
        payload = EventPayload(pr_number=42, head_sha="abc123")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.approve_pr.assert_called_once()
        provider.merge_pr.assert_called_once()

    def test_deduplication_limit_blocks(self) -> None:
        """When dedup limit is exceeded, guard blocks."""
        provider = _make_provider()
        # Simulate existing marker with count at max
        provider.find_comment.return_value = (
            100,
            "<!-- repair-dispatch:abc123:3 -->\nTracking",
        )
        payload = EventPayload(pr_number=42, head_sha="abc123")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_GUARD_BLOCKED

    def test_cycle_limit_blocks(self) -> None:
        """When cycle limit is reached, guard blocks."""
        provider = _make_provider()
        # First find_comment (dedup) returns None, second (cycle) returns at-limit
        provider.find_comment.side_effect = [
            None,  # dedup: no marker
            (200, "<!-- ai-pr-loop-cycle-tracker --> cycle:50"),  # cycle: at limit
        ]
        payload = EventPayload(pr_number=42, head_sha="abc123")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_GUARD_BLOCKED

    def test_copilot_changes_requested_dispatches_repair(self) -> None:
        """Copilot CHANGES_REQUESTED triggers repair dispatch."""
        provider = _make_provider(
            reviews=[ReviewInfo(id=1, user="copilot-pull-request-reviewer[bot]", state="CHANGES_REQUESTED", body="fix")]
        )
        provider.dispatch_repair.return_value = 200
        provider.list_review_comments.return_value = ["fix this"]
        payload = EventPayload(pr_number=42, head_sha="abc123")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_REPAIR_DISPATCHED
        provider.merge_pr.assert_not_called()
        provider.dispatch_repair.assert_called_once()

    def test_human_changes_requested_does_not_dispatch_repair(self) -> None:
        """Human CHANGES_REQUESTED blocks merge but does NOT trigger repair."""
        provider = _make_provider(reviews=[ReviewInfo(id=1, user="reviewer", state="CHANGES_REQUESTED", body="fix")])
        payload = EventPayload(pr_number=42, head_sha="abc123")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.merge_pr.assert_not_called()
        provider.dispatch_repair.assert_not_called()

    def test_merge_failure_returns_blocked(self) -> None:
        from agentic_devtools.cli.ci.orchestrator import EXIT_MERGE_BLOCKED

        provider = _make_provider()
        provider.merge_pr.side_effect = RuntimeError("merge conflict")
        payload = EventPayload(pr_number=42, head_sha="abc123")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_MERGE_BLOCKED

    def test_checks_not_all_passing_blocks_merge(self) -> None:
        """Checks with non-success conclusion (e.g., cancelled) block merge."""
        from agentic_devtools.cli.ci.orchestrator import EXIT_MERGE_BLOCKED

        provider = _make_provider(
            check_runs=[
                CheckRunStatus(id=1, name="ci/build", status="completed", conclusion="cancelled"),
            ]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123")
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
        payload = EventPayload(pr_number=42, head_sha="abc123")
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
            ]
        )
        payload = EventPayload(pr_number=42, head_sha="abc123")
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
        payload = EventPayload(pr_number=42, head_sha="abc123")
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
        payload = EventPayload(pr_number=42, head_sha="abc123")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_REPAIR_DISPATCHED
        provider.dispatch_repair.assert_called_once()
        # Comments fetched exactly once during detection; _dispatch_repair reuses the cache
        provider.list_review_comments.assert_called_once()

    def test_copilot_commented_without_inline_comments_does_not_dispatch(self) -> None:
        """Copilot COMMENTED review without inline comments is not actionable."""
        provider = _make_provider(
            reviews=[ReviewInfo(id=3, user="copilot-pull-request-reviewer[bot]", state="COMMENTED", body="lgtm")]
        )
        provider.list_review_comments.return_value = []
        payload = EventPayload(pr_number=42, head_sha="abc123")
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
        payload = EventPayload(pr_number=42, head_sha="abc123")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.dispatch_repair.assert_not_called()
        provider.merge_pr.assert_called_once()

    def test_copilot_commented_with_copilot_login_alias(self) -> None:
        """COMMENTED review from 'Copilot' login (alias) with comments triggers repair."""
        provider = _make_provider(reviews=[ReviewInfo(id=4, user="Copilot", state="COMMENTED", body="")])
        provider.dispatch_repair.return_value = 200
        provider.list_review_comments.return_value = ["please fix this"]
        payload = EventPayload(pr_number=42, head_sha="abc123")
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
        payload = EventPayload(pr_number=42, head_sha="abc123")
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
        payload = EventPayload(pr_number=42, head_sha="abc123")
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
        payload = EventPayload(pr_number=42, head_sha="abc123")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_SUCCESS
        provider.dispatch_repair.assert_not_called()
        provider.merge_pr.assert_called_once()


class TestRunAIPRLoopDecisionSummary:
    """Verify structured decision summary is emitted in key scenarios."""

    def test_merged_pr_emits_summary(self) -> None:
        provider = _make_provider()
        payload = EventPayload(pr_number=42, head_sha="abc123")
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
        provider = _make_provider(check_runs=[CheckRunStatus(id=1, name="ci", status="in_progress")])
        payload = EventPayload(pr_number=42, head_sha="abc123")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "wait"
        assert summary["reason"] == "checks_pending"
        assert summary["ci"]["pending"] is True

    def test_repair_dispatched_emits_summary(self) -> None:
        provider = _make_provider(
            check_runs=[
                CheckRunStatus(id=1, name="ci/build", status="completed", conclusion="success"),
                CheckRunStatus(id=2, name="ci/test", status="completed", conclusion="failure"),
            ],
            reviews=[],
        )
        provider.dispatch_repair.return_value = 200
        payload = EventPayload(pr_number=42, head_sha="abc123")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "repair_dispatched"
        assert summary["exit_code"] == EXIT_REPAIR_DISPATCHED
        assert summary["repair"]["needed"] is True
        assert summary["repair"]["type"] == "ci"
        assert "ci/test" in summary["repair"]["failed_checks"]

    def test_no_pr_number_emits_summary(self) -> None:
        provider = MagicMock()
        payload = EventPayload(pr_number=0)
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "skip"
        assert summary["reason"] == "no_pr_number"

    def test_do_not_merge_emits_summary(self) -> None:
        provider = _make_provider(
            pr_meta=PRMetadata(
                number=42,
                title="t",
                head_branch="b",
                head_sha="s",
                base_branch="main",
                head_repo_full_name="owner/repo",
                base_repo_full_name="owner/repo",
                labels=["do-not-auto-merge"],
            )
        )
        payload = EventPayload(pr_number=42, head_sha="s")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "skip_merge"
        assert summary["reason"] == "do_not_auto_merge_label"

    def test_summary_includes_ci_failed_check_names(self) -> None:
        provider = _make_provider(
            check_runs=[
                CheckRunStatus(id=1, name="ci/build", status="completed", conclusion="failure"),
                CheckRunStatus(id=2, name="ci/lint", status="completed", conclusion="success"),
            ],
            reviews=[],
        )
        provider.dispatch_repair.return_value = 200
        payload = EventPayload(pr_number=42, head_sha="abc123")
        summary = _capture_summary(provider, payload)

        assert "ci/build" in summary["ci"]["failed"]
        assert "ci/lint" not in summary["ci"]["failed"]

    def test_pr_files_error_emits_error_summary(self) -> None:
        provider = _make_provider()
        provider.list_pr_files.side_effect = RuntimeError("api unavailable")
        payload = EventPayload(pr_number=42, head_sha="abc123")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "error"
        assert summary["reason"] == "pr_files_listing_failed"
        assert summary["error"] == "api unavailable"
        assert summary["exit_code"] == EXIT_METADATA_FAILED

    def test_repair_dispatch_failure_emits_failure_reason(self) -> None:
        provider = _make_provider(
            check_runs=[CheckRunStatus(id=2, name="ci/test", status="completed", conclusion="failure")],
            reviews=[],
        )
        provider.dispatch_repair.side_effect = RuntimeError("dispatch endpoint timeout")
        payload = EventPayload(pr_number=42, head_sha="abc123")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "repair_failed"
        assert summary["reason"] == "dispatch endpoint timeout"
        assert summary["exit_code"] == EXIT_MERGE_BLOCKED

    def test_check_runs_error_emits_error_summary(self) -> None:
        provider = _make_provider()
        provider.list_check_runs.side_effect = RuntimeError("checks api unavailable")
        payload = EventPayload(pr_number=42, head_sha="abc123")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "error"
        assert summary["reason"] == "check_runs_listing_failed"
        assert summary["error"] == "checks api unavailable"
        assert summary["exit_code"] == EXIT_METADATA_FAILED

    def test_list_reviews_error_emits_error_summary(self) -> None:
        provider = _make_provider()
        provider.list_reviews.side_effect = RuntimeError("reviews api unavailable")
        payload = EventPayload(pr_number=42, head_sha="abc123")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "error"
        assert summary["reason"] == "reviews_listing_failed"
        assert summary["error"] == "reviews api unavailable"
        assert summary["exit_code"] == EXIT_METADATA_FAILED

    def test_approval_error_emits_error_summary(self) -> None:
        provider = _make_provider(reviews=[])
        provider.approve_pr.side_effect = RuntimeError("approval endpoint unavailable")
        payload = EventPayload(pr_number=42, head_sha="abc123")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "error"
        assert summary["reason"] == "approval_failed"
        assert summary["error"] == "approval endpoint unavailable"
        assert summary["exit_code"] == EXIT_MERGE_BLOCKED
