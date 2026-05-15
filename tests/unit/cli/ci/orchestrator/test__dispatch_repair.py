"""Tests for _dispatch_repair() in the orchestrator."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.models import CheckRunStatus, RepairDecision
from agentic_devtools.cli.ci.orchestrator import (
    EXIT_MERGE_BLOCKED,
    EXIT_REPAIR_DISPATCHED,
    _dispatch_repair,
)


class TestDispatchRepair:
    """Tests for the repair dispatch function."""

    def test_dispatches_review_repair(self) -> None:
        """FR-001: Posts @copilot comment for review repair."""
        provider = MagicMock()
        provider.list_review_comments.return_value = ["Fix the null check"]
        provider.dispatch_repair.return_value = 300

        decision = RepairDecision(
            repair_needed=True,
            repair_type="review",
            review_id=100,
            failed_checks=[],
        )
        result = _dispatch_repair(
            provider=provider,
            pr_number=42,
            head_sha="abc123",
            decision=decision,
        )
        assert result == EXIT_REPAIR_DISPATCHED
        provider.list_review_comments.assert_called_once_with(42, 100)
        provider.dispatch_repair.assert_called_once_with(
            pr_number=42,
            head_sha="abc123",
            repair_type="review",
            failed_checks=[],
            review_comments=["Fix the null check"],
        )

    def test_dispatches_ci_repair_without_review_comments(self) -> None:
        """FR-002: CI repair doesn't fetch review comments."""
        provider = MagicMock()
        provider.dispatch_repair.return_value = 301

        failed = [CheckRunStatus(id=1, name="lint", status="completed", conclusion="failure")]
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
        provider.list_review_comments.return_value = ["Use better names"]
        provider.dispatch_repair.return_value = 302

        failed = [CheckRunStatus(id=2, name="test", status="completed", conclusion="failure")]
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
            failed_checks=[],
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
        provider.list_review_comments.side_effect = RuntimeError("timeout")
        provider.dispatch_repair.return_value = 303

        decision = RepairDecision(
            repair_needed=True,
            repair_type="review",
            review_id=100,
            failed_checks=[],
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
        )
