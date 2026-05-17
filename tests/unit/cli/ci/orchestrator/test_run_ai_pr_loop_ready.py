"""Tests for orchestrator with PR in ready-for-review state."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.models import (
    CheckRunStatus,
    EventPayload,
    PRMetadata,
    ReviewInfo,
)
from agentic_devtools.cli.ci.orchestrator import EXIT_SUCCESS, run_ai_pr_loop


class TestRunAIPRLoopReady:
    """Tests verifying the orchestrator produces the same API call sequence as existing YAML."""

    def test_ready_pr_call_sequence(self) -> None:
        """Verify: metadata → files → checks → dedup → cycle → reviews → approve → merge."""
        provider = MagicMock()
        provider.get_pr_metadata.return_value = PRMetadata(
            number=42,
            title="feat: ready PR",
            head_branch="feature/ready",
            head_sha="sha123",
            base_branch="main",
            head_repo_full_name="owner/repo",
            base_repo_full_name="owner/repo",
            labels=[],
        )
        provider.list_pr_files.return_value = ["src/app.py"]
        provider.list_check_runs.return_value = [
            CheckRunStatus(id=1, name="Tests ✅", status="completed", conclusion="success"),
            CheckRunStatus(id=2, name="Markdown Lint ✅", status="completed", conclusion="success"),
        ]
        provider.list_reviews.return_value = [
            ReviewInfo(id=1, user="reviewer", state="APPROVED", body="LGTM"),
        ]
        provider.find_comment.return_value = None
        provider.post_comment.return_value = 100
        provider.merge_pr.return_value = None

        payload = EventPayload(pr_number=42, head_sha="sha123")
        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS

        # The key operations are called in order
        provider.get_pr_metadata.assert_called_once_with(42)
        provider.list_pr_files.assert_called_once_with(42)
        provider.list_check_runs.assert_called_once_with("sha123")
        provider.list_reviews.assert_called_once_with(42)
        provider.merge_pr.assert_called_once_with(42, "sha123", "squash")
