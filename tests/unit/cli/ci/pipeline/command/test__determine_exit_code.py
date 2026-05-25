"""Tests for _determine_exit_code."""

from agentic_devtools.cli.ci.pipeline.command import (
    EXIT_GUARD_BLOCKED,
    EXIT_MERGE_BLOCKED,
    EXIT_REPAIR_DISPATCHED,
    EXIT_SUCCESS,
    _determine_exit_code,
)
from agentic_devtools.cli.ci.pipeline.models import ActionDecision, ActionResult
from agentic_devtools.cli.ci.pipeline.snapshot import PRStateSnapshot


class TestDetermineExitCode:
    """Tests for pipeline exit code mapping."""

    def test_returns_guard_blocked_for_blocked_result(self) -> None:
        results = [ActionResult(name="guards", decision=ActionDecision.BLOCKED)]
        assert _determine_exit_code(results) == EXIT_GUARD_BLOCKED

    def test_returns_repair_dispatched_when_dispatch_repair_executes(self) -> None:
        results = [ActionResult(name="dispatch_repair", decision=ActionDecision.EXECUTE)]
        assert _determine_exit_code(results) == EXIT_REPAIR_DISPATCHED

    def test_returns_merge_blocked_when_side_effect_action_fails(self) -> None:
        results = [ActionResult(name="approve", decision=ActionDecision.FAILED)]
        assert _determine_exit_code(results) == EXIT_MERGE_BLOCKED

    def test_returns_success_when_no_blocking_or_failures(self) -> None:
        results = [ActionResult(name="publish", decision=ActionDecision.SKIP)]
        assert _determine_exit_code(results) == EXIT_SUCCESS

    def test_dispatch_repair_dedup_limit_skip_returns_guard_blocked(self) -> None:
        results = [
            ActionResult(
                name="dispatch_repair",
                decision=ActionDecision.SKIP,
                details="Dedup limit reached (count=3)",
                limit_reached=True,
            )
        ]
        assert _determine_exit_code(results) == EXIT_GUARD_BLOCKED

    def test_dispatch_repair_cycle_limit_skip_returns_guard_blocked(self) -> None:
        results = [
            ActionResult(
                name="dispatch_repair",
                decision=ActionDecision.SKIP,
                details="Cycle limit reached (count=5)",
                limit_reached=True,
            )
        ]
        assert _determine_exit_code(results) == EXIT_GUARD_BLOCKED

    def test_dispatch_repair_other_skip_returns_success(self) -> None:
        """SKIP for other reasons (e.g. no repair needed) should not be guard-blocked."""
        results = [
            ActionResult(
                name="dispatch_repair",
                decision=ActionDecision.SKIP,
                details="No repair needed (ci_status=passing, review_actionable=False)",
            )
        ]
        assert _determine_exit_code(results) == EXIT_SUCCESS

    def test_returns_merge_blocked_when_ci_status_unknown(self) -> None:
        results = [ActionResult(name="merge", decision=ActionDecision.SKIP, details="CI is unknown")]
        snapshot = PRStateSnapshot(pr_number=1, ci_status="unknown")
        assert _determine_exit_code(results, snapshot=snapshot) == EXIT_MERGE_BLOCKED

    def test_approve_skip_missing_token_returns_merge_blocked(self) -> None:
        """approve=SKIP with approver_token_available=False must block merge (legacy parity)."""
        results = [
            ActionResult(
                name="approve",
                decision=ActionDecision.SKIP,
                preconditions={"approver_token_available": False},
                details="Provider skipped approval (missing approver token?)",
            )
        ]
        assert _determine_exit_code(results) == EXIT_MERGE_BLOCKED

    def test_approve_skip_other_reason_returns_success(self) -> None:
        """approve=SKIP for normal reasons (already approved, CI not passing, etc.) returns success."""
        results = [
            ActionResult(
                name="approve",
                decision=ActionDecision.SKIP,
                preconditions={"no_approval_on_head": False},
                details="Already approved on current HEAD",
            )
        ]
        assert _determine_exit_code(results) == EXIT_SUCCESS

    def test_approve_skip_no_preconditions_returns_success(self) -> None:
        """approve=SKIP with no preconditions (approver_token_available absent) returns success."""
        results = [
            ActionResult(
                name="approve",
                decision=ActionDecision.SKIP,
                preconditions={},
                details="No preconditions set",
            )
        ]
        assert _determine_exit_code(results) == EXIT_SUCCESS
