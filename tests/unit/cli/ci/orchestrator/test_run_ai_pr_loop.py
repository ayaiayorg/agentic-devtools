"""Tests for run_ai_pr_loop() orchestrator state machine."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.models import (
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

    def test_changes_requested_dispatches_repair(self) -> None:
        provider = _make_provider(reviews=[ReviewInfo(id=1, user="reviewer", state="CHANGES_REQUESTED", body="fix")])
        provider.dispatch_repair.return_value = 200
        provider.list_review_comments.return_value = ["fix this"]
        payload = EventPayload(pr_number=42, head_sha="abc123")
        result = run_ai_pr_loop(provider, payload)
        assert result == EXIT_REPAIR_DISPATCHED
        provider.merge_pr.assert_not_called()
        provider.dispatch_repair.assert_called_once()

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
