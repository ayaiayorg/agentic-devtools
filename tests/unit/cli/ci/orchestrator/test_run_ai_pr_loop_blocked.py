"""Tests for orchestrator with failing CI checks."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.models import (
    COPILOT_REVIEWER_LOGIN,
    CheckRunStatus,
    EventPayload,
    PRMetadata,
    ReviewInfo,
)
from agentic_devtools.cli.ci.orchestrator import (
    EXIT_GUARD_BLOCKED,
    EXIT_REPAIR_DISPATCHED,
    EXIT_SUCCESS,
    run_ai_pr_loop,
)


def _base_pr_meta(head_sha: str = "abc456def789") -> PRMetadata:
    return PRMetadata(
        number=42,
        title="feat: test",
        head_branch="feature/test",
        head_sha=head_sha,
        base_branch="main",
        head_repo_full_name="owner/repo",
        base_repo_full_name="owner/repo",
        labels=["ai-auto-merge-allowed"],
    )


class TestRunAIPRLoopRepairDispatch:
    """Tests verifying orchestrator dispatches repair on failed checks."""

    def test_failed_checks_dispatches_repair(self) -> None:
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="feat: failing",
            head_branch="feature/fail",
            head_sha="abc456def789",
            base_branch="main",
            head_repo_full_name="owner/repo",
            base_repo_full_name="owner/repo",
            labels=[],
        )
        provider.list_pr_files.return_value = ["src/app.py"]
        provider.list_check_runs.return_value = [
            CheckRunStatus(id=1, name="Tests ✅", status="completed", conclusion="success"),
            CheckRunStatus(id=2, name="Workflow Tests ✅", status="completed", conclusion="failure"),
        ]
        provider.list_reviews.return_value = []
        provider.find_comment.return_value = None
        provider.post_comment.return_value = 100
        provider.dispatch_repair.return_value = 200

        payload = EventPayload(pr_number=42, head_sha="abc456def789")
        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_REPAIR_DISPATCHED
        provider.merge_pr.assert_not_called()
        provider.approve_pr.assert_not_called()
        provider.dispatch_repair.assert_called_once()

    def test_dedup_blocks_non_review_submission_when_limit_exceeded(self) -> None:
        """Non-review-submission events (e.g. push/synchronize) are blocked by dedup."""
        _SHA = "abc456def789"
        provider = MagicMock()
        provider.get_pr_metadata.return_value = _base_pr_meta(_SHA)
        provider.list_pr_files.return_value = ["src/app.py"]
        provider.list_check_runs.return_value = [
            CheckRunStatus(id=1, name="Tests ✅", status="completed", conclusion="success"),
        ]
        # Simulate dedup counter already at max (count=3, so next increment → 4 > 3)
        provider.find_comment.return_value = (
            99,
            f"<!-- repair-dispatch:{_SHA}:3 -->\nDispatch tracking for `{_SHA[:8]}`",
        )

        payload = EventPayload(pr_number=42, head_sha=_SHA, action="synchronize")
        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_GUARD_BLOCKED

    def test_review_submission_bypasses_dedup_when_limit_exceeded(self) -> None:
        """Review submission events bypass deduplication even when the dispatch limit is exceeded."""
        _SHA = "abc456def789"
        provider = MagicMock()
        provider.get_pr_metadata.return_value = _base_pr_meta(_SHA)
        provider.list_pr_files.return_value = ["src/app.py"]
        provider.list_check_runs.return_value = [
            CheckRunStatus(id=1, name="Tests ✅", status="completed", conclusion="success"),
        ]

        # Dedup counter well above limit — should be ignored for "submitted" events.
        # Keep the mock realistic by only returning a dedup comment when the dedup
        # marker is explicitly requested; cycle-tracker lookups should not receive a
        # comment body for a different marker.
        def _find_comment_side_effect(_pr_number: int, marker: str):
            if marker == "<!-- repair-dispatch:":
                return (
                    99,
                    f"<!-- repair-dispatch:{_SHA}:99 -->\nDispatch tracking for `{_SHA[:8]}`",
                )
            return None

        provider.find_comment.side_effect = _find_comment_side_effect
        provider.list_reviews.return_value = [
            ReviewInfo(id=1, user=COPILOT_REVIEWER_LOGIN, state="APPROVED", body="lgtm"),
        ]
        provider.merge_pr.return_value = None

        payload = EventPayload(pr_number=42, head_sha=_SHA, action="submitted")
        result = run_ai_pr_loop(provider, payload)

        # Should bypass dedup and continue down the success/merge path.
        assert result == EXIT_SUCCESS
        provider.merge_pr.assert_called_once()
        provider.dispatch_repair.assert_not_called()
        # check_deduplication should never have been called (find_comment only for cycle check)
        dedup_calls = [c for c in provider.find_comment.call_args_list if c.args[1] == "<!-- repair-dispatch:"]
        assert dedup_calls == [], f"dedup find_comment was called unexpectedly: {dedup_calls}"

    def test_missing_action_does_not_bypass_dedup_when_limit_exceeded(self) -> None:
        """Missing action should not be treated as a review submission for dedup bypass."""
        _SHA = "abc456def789"
        provider = MagicMock()
        provider.get_pr_metadata.return_value = _base_pr_meta(_SHA)
        provider.list_pr_files.return_value = ["src/app.py"]
        provider.list_check_runs.return_value = [
            CheckRunStatus(id=1, name="Tests ✅", status="completed", conclusion="success"),
        ]
        provider.find_comment.return_value = (
            99,
            f"<!-- repair-dispatch:{_SHA}:99 -->\nDispatch tracking for `{_SHA[:8]}`",
        )

        payload = EventPayload(pr_number=42, head_sha=_SHA)
        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_GUARD_BLOCKED
