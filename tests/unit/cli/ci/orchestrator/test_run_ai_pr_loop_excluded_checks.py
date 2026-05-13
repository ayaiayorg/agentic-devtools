"""Tests for run_ai_pr_loop excluded check names handling."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.models import (
    CheckRunStatus,
    EventPayload,
    PRMetadata,
    ReviewInfo,
)
from agentic_devtools.cli.ci.orchestrator import EXIT_SUCCESS, run_ai_pr_loop


def _make_provider(
    *,
    check_runs: list[CheckRunStatus] | None = None,
) -> MagicMock:
    """Create a mock provider with sensible defaults."""
    provider = MagicMock()
    provider.get_pr_metadata.return_value = PRMetadata(
        number=42,
        title="feat: test",
        head_branch="feature/test",
        head_sha="abc123",
        base_branch="main",
        head_repo_full_name="owner/repo",
        base_repo_full_name="owner/repo",
        labels=[],
    )
    provider.list_pr_files.return_value = ["src/main.py"]
    provider.list_check_runs.return_value = (
        check_runs
        if check_runs is not None
        else []
    )
    provider.list_reviews.return_value = [
        ReviewInfo(id=1, user="reviewer", state="APPROVED"),
    ]
    provider.find_comment.return_value = None
    provider.post_comment.return_value = 100
    provider.merge_pr.return_value = None
    return provider


class TestExcludedCheckNames:
    """Tests that excluded check run names are skipped during CI gating."""

    def test_excluded_check_name_is_skipped(self) -> None:
        """A check whose name is in excluded_check_names should not block merge."""
        excluded = CheckRunStatus(
            id=10,
            name="AI PR Loop",
            status="completed",
            conclusion="failure",
        )
        passing = CheckRunStatus(
            id=11,
            name="Tests",
            status="completed",
            conclusion="success",
        )
        provider = _make_provider(check_runs=[excluded, passing])
        payload = EventPayload(pr_number=42, head_sha="abc123")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.merge_pr.assert_called_once()
