"""Tests for orchestrator with PR having no linked issue."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.models import (
    CheckRunStatus,
    EventPayload,
    PRMetadata,
    ReviewInfo,
)
from agentic_devtools.cli.ci.orchestrator import EXIT_SUCCESS, run_ai_pr_loop


class TestRunAIPRLoopNoIssue:
    """Tests for PRs with no linked issue — should still process."""

    def test_pr_without_linked_issue_still_processes(self) -> None:
        """Processing continues even without a linked issue."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=99,
            title="chore: cleanup",  # No issue reference in title
            head_branch="chore/cleanup",
            head_sha="nnn999",
            base_branch="main",
            head_repo_full_name="owner/repo",
            base_repo_full_name="owner/repo",
            labels=[],
        )
        provider.list_pr_files.return_value = ["src/cleanup.py"]
        provider.list_check_runs.return_value = [
            CheckRunStatus(id=1, name="Tests ✅", status="completed", conclusion="success")
        ]
        provider.list_reviews.return_value = [
            ReviewInfo(id=1, user="copilot-pull-request-reviewer[bot]", state="APPROVED", body="lgtm")
        ]
        provider.find_comment.return_value = None
        provider.post_comment.return_value = 100

        payload = EventPayload(pr_number=99, head_sha="nnn999")
        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.merge_pr.assert_called_once()
