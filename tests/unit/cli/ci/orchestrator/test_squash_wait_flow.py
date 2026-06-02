"""Tests for the squash-wait state machine in run_ai_pr_loop()."""

from typing import Any
from unittest.mock import MagicMock

from agentic_devtools.cli.ci.guards import SQUASH_WAIT_MARKER_PREFIX, SQUASH_WAIT_MAX_ATTEMPTS
from agentic_devtools.cli.ci.models import (
    EventPayload,
    IssueEvent,
    PRMetadata,
    ReviewInfo,
)
from agentic_devtools.cli.ci.orchestrator import (
    EXIT_GUARD_BLOCKED,
    EXIT_MERGE_BLOCKED,
    EXIT_METADATA_FAILED,
    EXIT_SUCCESS,
    run_ai_pr_loop,
)


def _make_pr_meta(**kwargs) -> PRMetadata:
    defaults: dict[str, Any] = dict(
        number=42,
        title="feat: test",
        head_branch="feature/test",
        head_sha="abc123",
        base_branch="main",
        head_repo_full_name="owner/repo",
        base_repo_full_name="owner/repo",
        labels=["ai-auto-merge-allowed"],
    )
    defaults.update(kwargs)
    return PRMetadata(**defaults)


def _make_prior_review(state="CHANGES_REQUESTED", commit_sha="oldsha", review_id=9):
    return ReviewInfo(
        id=review_id,
        user="copilot-pull-request-reviewer[bot]",
        state=state,
        body="fix this",
        commit_sha=commit_sha,
    )


def _make_marker_body(
    *,
    sha="abc123",
    attempt=1,
    head_pushed_at="2026-05-20T06:00:00+00:00",
    copilot_session_terminal=False,
    copilot_session_outcome="pending",
):
    terminal_str = "true" if copilot_session_terminal else "false"
    return (
        f"{SQUASH_WAIT_MARKER_PREFIX}"
        f"sha={sha}\n"
        f"attempt={attempt}\n"
        f"head_pushed_at={head_pushed_at}\n"
        f"ci_passed=true\n"
        f"copilot_session_terminal={terminal_str}\n"
        f"copilot_session_outcome={copilot_session_outcome}\n"
        f"squash_done=false\n"
        f"-->\nSquash wait in progress for PR #42 — last checked 2026-05-20T07:00:00+00:00"
    )


def _make_provider(
    *,
    pr_meta=None,
    reviews=None,
    commit_count=2,
    marker_body=None,
    issue_events=None,
):
    provider = MagicMock()
    provider.get_pr_metadata.return_value = pr_meta or _make_pr_meta()
    provider.list_pr_files.return_value = ["src/main.py"]
    provider.list_check_runs.return_value = []
    provider.list_reviews.return_value = reviews if reviews is not None else [_make_prior_review()]
    provider.list_review_comments.return_value = []
    provider.find_comment.return_value = (99, marker_body) if marker_body is not None else None
    provider.post_comment.return_value = 100
    provider.update_comment.return_value = None
    provider.count_commits_above_merge_base.return_value = commit_count
    provider.squash_post_repair.return_value = None
    provider.list_pr_issue_events.return_value = issue_events if issue_events is not None else []
    return provider


class TestSquashWaitFlow:
    """Tests for the squash-wait state machine triggered by workflow_run / workflow_dispatch."""

    def test_first_visit_no_terminal_event_writes_marker_and_exits(self) -> None:
        """First visit with no events → write marker, exit without squash."""
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            # No marker yet, no events
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_not_called()
        # Marker should be written
        provider.post_comment.assert_called()
        marker_body = provider.post_comment.call_args[0][1]
        assert "sha=abc123" in marker_body
        assert "attempt=1" in marker_body
        assert "copilot_session_terminal=false" in marker_body
        assert "copilot_session_outcome=pending" in marker_body

    def test_ci_completion_fork_pr_blocks_before_squash_wait(self) -> None:
        """Fork guard blocks before squash-wait review/event probes run."""
        provider = _make_provider(
            pr_meta=_make_pr_meta(
                head_repo_full_name="fork/repo",
                base_repo_full_name="owner/repo",
            ),
            reviews=[_make_prior_review()],
            commit_count=2,
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_GUARD_BLOCKED
        provider.list_reviews.assert_not_called()
        provider.list_pr_issue_events.assert_not_called()
        provider.squash_post_repair.assert_not_called()

    def test_ci_completion_exclusion_label_blocks_before_squash_wait(self) -> None:
        """Exclusion label guard blocks before squash-wait review/event probes run."""
        provider = _make_provider(
            pr_meta=_make_pr_meta(labels=["ai-pr-loop-ignore"]),
            reviews=[_make_prior_review()],
            commit_count=2,
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_GUARD_BLOCKED
        provider.list_reviews.assert_not_called()
        provider.list_pr_issue_events.assert_not_called()
        provider.squash_post_repair.assert_not_called()

    def test_first_visit_finished_event_found_proceeds_to_squash(self) -> None:
        """First visit with copilot_work_finished event → squash immediately."""
        finished_event = IssueEvent(
            id=1001,
            event="copilot_work_finished",
            created_at="2026-05-20T06:05:00+00:00",
        )
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            issue_events=[finished_event],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_called_once_with(
            pr_number=42,
            base_branch="main",
            head_branch="feature/test",
            head_sha="abc123",
        )

    def test_first_visit_failure_event_found_writes_marker_and_exits(self) -> None:
        """First visit with copilot_work_finished_failure → record failure, defer squash."""
        failure_event = IssueEvent(
            id=1002,
            event="copilot_work_finished_failure",
            created_at="2026-05-20T06:05:00+00:00",
        )
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            issue_events=[failure_event],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_not_called()
        # Marker should be written with terminal=true, outcome=failure
        provider.post_comment.assert_called()
        marker_body = provider.post_comment.call_args[0][1]
        assert "attempt=1" in marker_body
        assert "copilot_session_terminal=true" in marker_body
        assert "copilot_session_outcome=failure" in marker_body

    def test_first_visit_prefers_latest_terminal_event(self) -> None:
        """When multiple terminal events exist, latest event decides the outcome."""
        failure_event = IssueEvent(
            id=1002,
            event="copilot_work_finished_failure",
            created_at="2026-05-20T06:05:00+00:00",
        )
        finished_event = IssueEvent(
            id=1003,
            event="copilot_work_finished",
            created_at="2026-05-20T06:06:00+00:00",
        )
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            issue_events=[failure_event, finished_event],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_called_once()

    def test_subsequent_visit_outcome_success_squashes(self) -> None:
        """Existing marker with outcome=success → squash immediately (catch-up)."""
        marker = _make_marker_body(
            sha="abc123", attempt=2, copilot_session_terminal=True, copilot_session_outcome="success"
        )
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            marker_body=marker,
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_called_once()

    def test_subsequent_visit_outcome_failure_before_attempt_24_waits(self) -> None:
        """Existing marker with outcome=failure at attempt 7 → wait, no squash."""
        marker = _make_marker_body(
            sha="abc123", attempt=7, copilot_session_terminal=True, copilot_session_outcome="failure"
        )
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            marker_body=marker,
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_not_called()
        # Marker should be updated (attempt incremented)
        provider.update_comment.assert_called()

    def test_subsequent_visit_outcome_failure_at_attempt_24_squashes_with_recovery_comment(self) -> None:
        """Existing marker with outcome=failure at attempt 24 → squash with recovery comment."""
        marker = _make_marker_body(
            sha="abc123",
            attempt=SQUASH_WAIT_MAX_ATTEMPTS,
            copilot_session_terminal=True,
            copilot_session_outcome="failure",
        )
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            marker_body=marker,
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_called_once()
        # Recovery comment should be posted before squash
        comment_calls = [
            args[0][1]
            for args in provider.post_comment.call_args_list
            if "recovery" in args[0][1].lower() or "120-minute" in args[0][1].lower()
        ]
        assert len(comment_calls) >= 1

    def test_subsequent_visit_outcome_pending_at_attempt_24_squashes_with_timeout_comment(self) -> None:
        """Existing marker with outcome=pending at attempt 24 → force squash with timeout comment."""
        marker = _make_marker_body(
            sha="abc123",
            attempt=SQUASH_WAIT_MAX_ATTEMPTS,
            copilot_session_terminal=False,
            copilot_session_outcome="pending",
        )
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            marker_body=marker,
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_called_once()
        # Timeout comment should be posted
        comment_calls = [
            args[0][1]
            for args in provider.post_comment.call_args_list
            if "timeout" in args[0][1].lower() or "120-minute" in args[0][1].lower()
        ]
        assert len(comment_calls) >= 1

    def test_subsequent_visit_no_terminal_event_increments_attempt_and_exits(self) -> None:
        """Existing marker with outcome=pending, no new terminal event → increment attempt, wait."""
        marker = _make_marker_body(
            sha="abc123", attempt=3, copilot_session_terminal=False, copilot_session_outcome="pending"
        )
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            marker_body=marker,
            issue_events=[],  # No terminal event
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_not_called()
        # Marker should be updated with incremented attempt
        provider.update_comment.assert_called()
        updated_body = provider.update_comment.call_args[0][1]
        assert "attempt=4" in updated_body

    def test_second_visit_retries_without_time_filter_when_no_scoped_match(self) -> None:
        """Second visit retries unfiltered events to tolerate eventual consistency."""
        marker = _make_marker_body(
            sha="abc123",
            attempt=2,
            head_pushed_at="2026-05-20T07:00:00+00:00",
            copilot_session_terminal=False,
            copilot_session_outcome="pending",
        )
        finished_event = IssueEvent(
            id=1005,
            event="copilot_work_finished",
            created_at="2026-05-20T06:59:00+00:00",
        )
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            marker_body=marker,
            issue_events=[finished_event],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_called_once()

    def test_second_visit_ignores_time_filter_when_head_pushed_at_invalid(self) -> None:
        """Invalid head_pushed_at should skip scoped filtering and still detect terminal events."""
        marker = _make_marker_body(
            sha="abc123",
            attempt=2,
            head_pushed_at="not-a-timestamp",
            copilot_session_terminal=False,
            copilot_session_outcome="pending",
        )
        finished_event = IssueEvent(
            id=1005,
            event="copilot_work_finished",
            created_at="2026-05-20T06:59:00+00:00",
        )
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            marker_body=marker,
            issue_events=[finished_event],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_called_once()

    def test_subsequent_visit_terminal_unknown_outcome_waits(self) -> None:
        """Unknown terminal outcome should defer and keep waiting."""
        marker = _make_marker_body(
            sha="abc123", attempt=5, copilot_session_terminal=True, copilot_session_outcome="unknown"
        )
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            marker_body=marker,
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_not_called()
        provider.update_comment.assert_called()

    def test_subsequent_visit_ignores_terminal_events_before_latest_started(self) -> None:
        """A terminal event before the latest started event must not trigger squash."""
        marker = _make_marker_body(
            sha="abc123", attempt=3, copilot_session_terminal=False, copilot_session_outcome="pending"
        )
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            marker_body=marker,
            issue_events=[
                IssueEvent(id=1001, event="copilot_work_finished", created_at="2026-05-20T06:05:00+00:00"),
                IssueEvent(id=1002, event="copilot_work_started", created_at="2026-05-20T06:06:00+00:00"),
            ],
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_not_called()
        provider.update_comment.assert_called()
        updated_body = provider.update_comment.call_args[0][1]
        assert "attempt=4" in updated_body

    def test_sha_mismatch_resets_marker(self) -> None:
        """If marker sha doesn't match current head_sha → treat as first visit (write new marker)."""
        marker = _make_marker_body(
            sha="oldsha",  # different from payload head_sha
            attempt=5,
            copilot_session_terminal=True,
            copilot_session_outcome="failure",
        )
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            marker_body=marker,
            issue_events=[],  # No terminal event for new SHA
        )
        payload = EventPayload(pr_number=42, head_sha="newsha", action="completed")
        # Update the pr_meta to match the new head_sha
        provider.get_pr_metadata.return_value = _make_pr_meta(head_sha="newsha")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_not_called()
        # The marker is found (sha mismatch → treated as first-visit) and overwritten
        # write_squash_wait_marker calls update_comment because find_comment returns existing
        provider.update_comment.assert_called()
        new_marker_body = provider.update_comment.call_args[0][1]
        assert "sha=newsha" in new_marker_body
        assert "attempt=1" in new_marker_body

    def test_single_commit_skips_squash_wait(self) -> None:
        """With only 1 commit above merge base, the squash-wait path is skipped."""
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=1,  # ≤ 1 → nothing to squash
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_not_called()
        # Should NOT write a squash-wait marker
        # (it falls through to the normal finalization path)

    def test_single_commit_cleans_up_existing_squash_wait_marker(self) -> None:
        """With only 1 commit above merge base, any stale squash-wait marker is finalized."""
        marker = _make_marker_body(sha="abc123", attempt=3)
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=1,
            marker_body=marker,
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_not_called()
        provider.update_comment.assert_called()
        updated_body = provider.update_comment.call_args[0][1]
        assert "squash-wait-completed" in updated_body

    def test_no_prior_review_skips_squash_wait(self) -> None:
        """When no prior actionable Copilot review exists, squash-wait is not entered."""
        provider = _make_provider(
            reviews=[
                ReviewInfo(
                    id=1,
                    user="copilot-pull-request-reviewer[bot]",
                    state="APPROVED",
                    body="lgtm",
                    commit_sha="abc123",  # On HEAD, not prior
                )
            ],
            commit_count=2,
        )
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_not_called()
        # Events API should not be called when no prior review found
        provider.list_pr_issue_events.assert_not_called()

    def test_squash_failure_returns_merge_blocked(self) -> None:
        """When squash fails, return EXIT_MERGE_BLOCKED."""
        finished_event = IssueEvent(id=1001, event="copilot_work_finished", created_at="2026-05-20T06:05:00+00:00")
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            issue_events=[finished_event],
        )
        provider.squash_post_repair.side_effect = RuntimeError("squash failed")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_MERGE_BLOCKED

    def test_list_pr_issue_events_failure_treats_as_no_terminal_event(self) -> None:
        """When list_pr_issue_events raises, fail closed (treat as no terminal event)."""
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
        )
        provider.list_pr_issue_events.side_effect = RuntimeError("API failure")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        # Should still succeed (marker written, waiting for next cron tick)
        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_not_called()

    def test_post_comment_failure_before_squash_is_swallowed(self) -> None:
        """When post_comment raises before squash (for recovery/timeout comment), swallow and proceed."""
        marker = _make_marker_body(
            sha="abc123",
            attempt=SQUASH_WAIT_MAX_ATTEMPTS,
            copilot_session_terminal=True,
            copilot_session_outcome="failure",
        )
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            marker_body=marker,
        )
        provider.post_comment.side_effect = RuntimeError("comment post failed")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        # Squash should still proceed even if comment post fails
        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_called_once()

    def test_write_marker_failure_is_swallowed(self) -> None:
        """When write_squash_wait_marker raises, swallow and still return EXIT_SUCCESS."""
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            issue_events=[],  # No terminal event
        )
        provider.post_comment.side_effect = RuntimeError("marker write failed")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_not_called()

    def test_delete_marker_failure_is_swallowed(self) -> None:
        """When delete_squash_wait_marker raises after squash, swallow and return EXIT_SUCCESS."""
        finished_event = IssueEvent(id=1001, event="copilot_work_finished", created_at="2026-05-20T06:05:00+00:00")
        marker = _make_marker_body(
            sha="abc123",
            attempt=1,
            head_pushed_at="2026-05-20T06:00:00+00:00",
            copilot_session_terminal=True,
            copilot_session_outcome="success",
        )
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
            marker_body=marker,
            issue_events=[finished_event],
        )
        provider.update_comment.side_effect = RuntimeError("delete failed")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        # Squash succeeded even if marker deletion failed
        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_called_once()

    def test_commit_count_probe_failure_returns_metadata_failed(self) -> None:
        """When commit-count probe fails, orchestrator returns EXIT_METADATA_FAILED."""
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=2,
        )
        provider.count_commits_above_merge_base.side_effect = RuntimeError("count failed")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_METADATA_FAILED
        provider.squash_post_repair.assert_not_called()

    def test_cleanup_marker_failure_when_commit_count_le_one_is_swallowed(self) -> None:
        """Marker cleanup failures after commit_count<=1 are swallowed."""
        marker = _make_marker_body(
            sha="abc123",
            attempt=1,
            head_pushed_at="2026-05-20T06:00:00+00:00",
            copilot_session_terminal=False,
            copilot_session_outcome="pending",
        )
        provider = _make_provider(
            reviews=[_make_prior_review()],
            commit_count=1,
            marker_body=marker,
        )
        provider.update_comment.side_effect = RuntimeError("cleanup failed")
        payload = EventPayload(pr_number=42, head_sha="abc123", action="completed")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.squash_post_repair.assert_not_called()
