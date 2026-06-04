"""Tests for _dispatch_repair() in the orchestrator."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.models import CheckRunStatus, RepairDecision, ReviewCommentInfo
from agentic_devtools.cli.ci.orchestrator import (
    EXIT_GUARD_BLOCKED,
    EXIT_MERGE_BLOCKED,
    EXIT_REPAIR_DISPATCHED,
    _dispatch_repair,
)

_COMMENT = ReviewCommentInfo(id=1, path="foo.py", body="Fix the null check", html_url="https://github.com/r/p#1")
_PREFETCHED = ReviewCommentInfo(id=2, path="bar.py", body="pre-fetched comment", html_url="https://github.com/r/p#2")


class TestDispatchRepair:
    """Tests for the repair dispatch function."""

    def test_dispatches_review_repair(self) -> None:
        """FR-001: Posts @copilot comment for review repair."""
        provider = MagicMock()
        provider.find_comment.return_value = None
        provider.list_review_comments.return_value = [_COMMENT]
        provider.dispatch_repair.return_value = 300

        decision = RepairDecision(
            repair_needed=True,
            repair_type="review",
            review_id=100,
            failed_checks=(),
        )
        result = _dispatch_repair(
            provider=provider,
            pr_number=42,
            head_sha="abc123",
            decision=decision,
        )
        assert result == EXIT_REPAIR_DISPATCHED
        # review_comments is empty (CHANGES_REQUESTED path) — fetched lazily
        provider.list_review_comments.assert_called_once_with(42, 100)
        provider.dispatch_repair.assert_called_once_with(
            pr_number=42,
            head_sha="abc123",
            repair_type="review",
            failed_checks=[],
            review_comments=[_COMMENT],
            review_id=100,
        )

    def test_pre_fetched_review_comments_not_refetched(self) -> None:
        """When decision already has review_comments, list_review_comments is not called."""
        provider = MagicMock()
        provider.find_comment.return_value = None
        provider.dispatch_repair.return_value = 304

        decision = RepairDecision(
            repair_needed=True,
            repair_type="review",
            review_id=100,
            review_comments=(_PREFETCHED,),
            failed_checks=(),
        )
        result = _dispatch_repair(
            provider=provider,
            pr_number=42,
            head_sha="abc123",
            decision=decision,
        )
        assert result == EXIT_REPAIR_DISPATCHED
        provider.list_review_comments.assert_not_called()
        provider.dispatch_repair.assert_called_once_with(
            pr_number=42,
            head_sha="abc123",
            repair_type="review",
            failed_checks=[],
            review_comments=[_PREFETCHED],
            review_id=100,
        )

    def test_dispatches_ci_repair_without_review_comments(self) -> None:
        """FR-002: CI repair doesn't fetch review comments."""
        provider = MagicMock()
        provider.dispatch_repair.return_value = 301

        failed = (CheckRunStatus(id=1, name="lint", status="completed", conclusion="failure"),)
        decision = RepairDecision(
            repair_needed=True,
            repair_type="ci",
            review_id=0,
            failed_checks=failed,
        )
        result = _dispatch_repair(
            provider=provider,
            pr_number=42,
            head_sha="abc123",
            decision=decision,
        )
        assert result == EXIT_REPAIR_DISPATCHED
        provider.list_review_comments.assert_not_called()
        provider.dispatch_repair.assert_called_once()

    def test_dispatches_both_repair_with_review_and_ci(self) -> None:
        """Combined review + CI repair dispatches with both contexts."""
        provider = MagicMock()
        provider.find_comment.return_value = None
        provider.list_review_comments.return_value = [_COMMENT]
        provider.dispatch_repair.return_value = 302

        failed = (CheckRunStatus(id=2, name="test", status="completed", conclusion="failure"),)
        decision = RepairDecision(
            repair_needed=True,
            repair_type="both",
            review_id=200,
            failed_checks=failed,
        )
        result = _dispatch_repair(
            provider=provider,
            pr_number=42,
            head_sha="abc123",
            decision=decision,
        )
        assert result == EXIT_REPAIR_DISPATCHED
        provider.list_review_comments.assert_called_once_with(42, 200)

    def test_dispatch_failure_returns_merge_blocked(self) -> None:
        """When dispatch fails, returns EXIT_MERGE_BLOCKED."""
        provider = MagicMock()
        provider.dispatch_repair.side_effect = RuntimeError("API error")

        decision = RepairDecision(
            repair_needed=True,
            repair_type="ci",
            review_id=0,
            failed_checks=(),
        )
        result = _dispatch_repair(
            provider=provider,
            pr_number=42,
            head_sha="abc123",
            decision=decision,
        )
        assert result == EXIT_MERGE_BLOCKED

    def test_review_comment_fetch_failure_still_dispatches(self) -> None:
        """If review comment fetch fails, repair is still dispatched with empty comments."""
        provider = MagicMock()
        provider.find_comment.return_value = None
        provider.list_review_comments.side_effect = RuntimeError("timeout")
        provider.dispatch_repair.return_value = 303

        decision = RepairDecision(
            repair_needed=True,
            repair_type="review",
            review_id=100,
            failed_checks=(),
        )
        result = _dispatch_repair(
            provider=provider,
            pr_number=42,
            head_sha="abc123",
            decision=decision,
        )
        assert result == EXIT_REPAIR_DISPATCHED
        # dispatch_repair called with empty review_comments due to fetch failure
        provider.dispatch_repair.assert_called_once_with(
            pr_number=42,
            head_sha="abc123",
            repair_type="review",
            failed_checks=[],
            review_comments=[],
            review_id=100,
        )

    def test_dedup_recheck_blocks_dispatch_when_marker_advanced(self) -> None:
        """A dedup count increase before dispatch blocks duplicate repair comments."""
        provider = MagicMock()
        provider.find_comment.return_value = (100, "<!-- repair-dispatch:abc123:2 -->\nDispatch tracking")

        decision = RepairDecision(
            repair_needed=True,
            repair_type="ci",
            review_id=0,
            failed_checks=(),
        )
        result = _dispatch_repair(
            provider=provider,
            pr_number=42,
            head_sha="abc123",
            decision=decision,
            dedup_count_before_dispatch=1,
        )
        assert result == EXIT_GUARD_BLOCKED
        provider.dispatch_repair.assert_not_called()

    def test_dedup_recheck_blocks_dispatch_when_marker_token_changes(self) -> None:
        """A marker token mismatch blocks duplicate dispatch even if count is unchanged."""
        provider = MagicMock()
        provider.find_comment.return_value = (100, "<!-- repair-dispatch:abc123:1:other-run -->\nDispatch tracking")

        decision = RepairDecision(
            repair_needed=True,
            repair_type="ci",
            review_id=0,
            failed_checks=(),
        )
        result = _dispatch_repair(
            provider=provider,
            pr_number=42,
            head_sha="abc123",
            decision=decision,
            dedup_count_before_dispatch=1,
            dedup_writer_token="this-run",
        )
        assert result == EXIT_GUARD_BLOCKED
        provider.dispatch_repair.assert_not_called()

    def test_dedup_recheck_exception_still_dispatches(self) -> None:
        """Exception during dedup marker refresh is non-fatal and dispatch proceeds."""
        provider = MagicMock()
        provider.find_comment.side_effect = RuntimeError("API timeout")
        provider.dispatch_repair.return_value = 999

        decision = RepairDecision(
            repair_needed=True,
            repair_type="ci",
            review_id=0,
            failed_checks=(),
        )
        result = _dispatch_repair(
            provider=provider,
            pr_number=42,
            head_sha="abc123",
            decision=decision,
            dedup_count_before_dispatch=1,
        )
        assert result == EXIT_REPAIR_DISPATCHED
        provider.dispatch_repair.assert_called_once()

    def test_ci_only_dedup_limit_blocks_when_count_already_above_one(self) -> None:
        """CI-only repairs are blocked when pre-dispatch dedup count exceeds 1."""
        provider = MagicMock()
        provider.dispatch_repair.return_value = 999
        decision = RepairDecision(
            repair_needed=True,
            repair_type="ci",
            review_id=0,
            failed_checks=(),
        )
        failure_reason_out: list[str] = []

        result = _dispatch_repair(
            provider=provider,
            pr_number=42,
            head_sha="abc123",
            decision=decision,
            dedup_count_before_dispatch=2,
            failure_reason_out=failure_reason_out,
        )

        assert result == EXIT_GUARD_BLOCKED
        assert "dedup_limit_ci_only" in failure_reason_out
        provider.dispatch_repair.assert_not_called()
        provider.find_comment.assert_not_called()

    def test_dedup_recheck_allows_dispatch_when_marker_unchanged(self) -> None:
        """Unchanged marker should not be treated as a dedup race."""
        provider = MagicMock()
        provider.find_comment.return_value = (100, "<!-- repair-dispatch:abc123:1:this-run -->\nDispatch tracking")
        provider.dispatch_repair.return_value = 1001

        decision = RepairDecision(
            repair_needed=True,
            repair_type="ci",
            review_id=0,
            failed_checks=(),
        )
        result = _dispatch_repair(
            provider=provider,
            pr_number=42,
            head_sha="abc123",
            decision=decision,
            dedup_count_before_dispatch=1,
            dedup_writer_token="this-run",
        )
        assert result == EXIT_REPAIR_DISPATCHED
        provider.dispatch_repair.assert_called_once()

    def test_dedup_recheck_ignores_non_matching_marker_body(self) -> None:
        """A comment without dedup marker format should not block dispatch."""
        provider = MagicMock()
        provider.find_comment.return_value = (100, "Dispatch tracking without marker")
        provider.dispatch_repair.return_value = 1002

        decision = RepairDecision(
            repair_needed=True,
            repair_type="ci",
            review_id=0,
            failed_checks=(),
        )
        result = _dispatch_repair(
            provider=provider,
            pr_number=42,
            head_sha="abc123",
            decision=decision,
            dedup_count_before_dispatch=1,
        )
        assert result == EXIT_REPAIR_DISPATCHED
        provider.dispatch_repair.assert_called_once()

    def test_review_id_dedup_blocks_dispatch(self) -> None:
        """FR-012: Existing trigger comment for same review_id blocks dispatch."""
        provider = MagicMock()
        provider.find_comment.return_value = (
            500,
            "@copilot\n\n<!-- copilot-trigger:100 -->\n",
        )

        decision = RepairDecision(
            repair_needed=True,
            repair_type="review",
            review_id=100,
            failed_checks=(),
        )
        result = _dispatch_repair(
            provider=provider,
            pr_number=42,
            head_sha="abc123",
            decision=decision,
        )
        assert result == EXIT_GUARD_BLOCKED
        provider.list_review_comments.assert_not_called()
        provider.dispatch_repair.assert_not_called()

    def test_review_id_dedup_populates_failure_reason_out(self) -> None:
        """FR-012: Duplicate trigger appends reason to failure_reason_out."""
        provider = MagicMock()
        provider.find_comment.return_value = (
            500,
            "@copilot\n\n<!-- copilot-trigger:100 -->\n",
        )

        decision = RepairDecision(
            repair_needed=True,
            repair_type="review",
            review_id=100,
            failed_checks=(),
        )
        failure_reason_out: list[str] = []
        result = _dispatch_repair(
            provider=provider,
            pr_number=42,
            head_sha="abc123",
            decision=decision,
            failure_reason_out=failure_reason_out,
        )
        assert result == EXIT_GUARD_BLOCKED
        assert "duplicate_trigger_review_id" in failure_reason_out

    def test_review_id_dedup_exception_proceeds_fail_open(self) -> None:
        """Exception from is_duplicate_trigger fails open — dispatch still proceeds."""
        provider = MagicMock()
        # find_comment raises, simulating is_duplicate_trigger failing.
        # dedup_count_before_dispatch defaults to None so the SHA-level recheck
        # block is skipped, meaning find_comment is only called once (for is_duplicate_trigger).
        provider.find_comment.side_effect = RuntimeError("API timeout")
        provider.list_review_comments.return_value = []
        provider.dispatch_repair.return_value = 100

        decision = RepairDecision(
            repair_needed=True,
            repair_type="review",
            review_id=100,
            failed_checks=(),
        )
        failure_reason_out: list[str] = []
        result = _dispatch_repair(
            provider=provider,
            pr_number=42,
            head_sha="abc123",
            decision=decision,
            failure_reason_out=failure_reason_out,
            dedup_count_before_dispatch=None,
        )
        assert result == EXIT_REPAIR_DISPATCHED
        assert "duplicate_trigger_guard_failed" not in failure_reason_out
        provider.dispatch_repair.assert_called_once()

    def test_review_id_dedup_exception_proceeds_fail_open_without_reason_out(self) -> None:
        """Exception from is_duplicate_trigger fails open when reason list not provided."""
        provider = MagicMock()
        provider.find_comment.side_effect = RuntimeError("API timeout")
        provider.list_review_comments.return_value = []
        provider.dispatch_repair.return_value = 100

        decision = RepairDecision(
            repair_needed=True,
            repair_type="review",
            review_id=100,
            failed_checks=(),
        )
        result = _dispatch_repair(
            provider=provider,
            pr_number=42,
            head_sha="abc123",
            decision=decision,
        )
        assert result == EXIT_REPAIR_DISPATCHED
        provider.dispatch_repair.assert_called_once()
