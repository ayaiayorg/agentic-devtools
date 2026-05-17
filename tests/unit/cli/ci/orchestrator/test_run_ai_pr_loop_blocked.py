"""Tests for orchestrator with failing CI checks."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.models import (
    CheckRunStatus,
    EventPayload,
    PRMetadata,
)
from agentic_devtools.cli.ci.orchestrator import EXIT_REPAIR_DISPATCHED, run_ai_pr_loop


class TestRunAIPRLoopRepairDispatch:
    """Tests verifying orchestrator dispatches repair on failed checks."""

    def test_failed_checks_dispatches_repair(self) -> None:
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="feat: failing",
            head_branch="feature/fail",
            head_sha="sha456",
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

        payload = EventPayload(pr_number=42, head_sha="sha456")
        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_REPAIR_DISPATCHED
        provider.merge_pr.assert_not_called()
        provider.approve_pr.assert_not_called()
        provider.dispatch_repair.assert_called_once()
