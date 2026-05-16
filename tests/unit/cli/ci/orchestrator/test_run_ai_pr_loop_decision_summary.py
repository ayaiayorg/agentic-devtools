"""Tests verifying run_ai_pr_loop() emits a structured decision summary."""

import json
from io import StringIO
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.models import (
    CheckRunStatus,
    EventPayload,
    PRMetadata,
    ReviewInfo,
)
from agentic_devtools.cli.ci.orchestrator import (
    EXIT_GUARD_BLOCKED,
    EXIT_MERGE_BLOCKED,
    EXIT_METADATA_FAILED,
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


def _capture_summary(provider: MagicMock, payload: EventPayload) -> dict:
    """Run the orchestrator and capture the JSON decision summary from stdout."""
    buf = StringIO()
    with (
        patch("agentic_devtools.cli.ci.orchestrator.sys.stdout", buf),
        patch("agentic_devtools.cli.ci.orchestrator._is_github_actions", return_value=False),
    ):
        run_ai_pr_loop(provider, payload)
    # Parse the last JSON object from output (summary is at the end)
    output = buf.getvalue().strip()
    return json.loads(output)


class TestDecisionSummaryEmission:
    """Verify structured decision summary is emitted in key scenarios."""

    def test_merged_pr_emits_summary(self) -> None:
        """Happy path: merged PR emits summary with decision='merged'."""
        provider = _make_provider()
        payload = EventPayload(pr_number=42, head_sha="abc123")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "merged"
        assert summary["exit_code"] == EXIT_SUCCESS
        assert summary["event"]["pr_number"] == 42
        assert summary["reviews"]["has_approval"] is True
        assert summary["ci"]["pending"] is False
        assert summary["repair"]["needed"] is False

    def test_guard_blocked_emits_summary(self) -> None:
        """Fork PR guard emits summary with decision='blocked'."""
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
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "blocked"
        assert summary["reason"] == "fork_pr"
        assert summary["exit_code"] == EXIT_GUARD_BLOCKED

    def test_pending_checks_emits_wait_summary(self) -> None:
        """Pending CI checks emit summary with decision='wait'."""
        provider = _make_provider(check_runs=[CheckRunStatus(id=1, name="ci", status="in_progress")])
        payload = EventPayload(pr_number=42, head_sha="abc123")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "wait"
        assert summary["reason"] == "checks_pending"
        assert summary["ci"]["pending"] is True

    def test_repair_dispatched_emits_summary(self) -> None:
        """Repair dispatch emits summary with repair details."""
        provider = _make_provider(
            check_runs=[
                CheckRunStatus(id=1, name="ci/build", status="completed", conclusion="success"),
                CheckRunStatus(id=2, name="ci/test", status="completed", conclusion="failure"),
            ],
            reviews=[],
        )
        provider.dispatch_repair.return_value = 200
        payload = EventPayload(pr_number=42, head_sha="abc123")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "repair_dispatched"
        assert summary["exit_code"] == EXIT_REPAIR_DISPATCHED
        assert summary["repair"]["needed"] is True
        assert summary["repair"]["type"] == "ci"
        assert "ci/test" in summary["repair"]["failed_checks"]

    def test_no_pr_number_emits_summary(self) -> None:
        """No PR number emits summary with decision='skip'."""
        provider = MagicMock()
        payload = EventPayload(pr_number=0)
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "skip"
        assert summary["reason"] == "no_pr_number"

    def test_do_not_merge_emits_summary(self) -> None:
        """do-not-auto-merge label emits summary with decision='skip_merge'."""
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
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "skip_merge"
        assert summary["reason"] == "do_not_auto_merge_label"

    def test_summary_includes_ci_failed_check_names(self) -> None:
        """CI summary includes the names of failed checks."""
        provider = _make_provider(
            check_runs=[
                CheckRunStatus(id=1, name="ci/build", status="completed", conclusion="failure"),
                CheckRunStatus(id=2, name="ci/lint", status="completed", conclusion="success"),
            ],
            reviews=[],
        )
        provider.dispatch_repair.return_value = 200
        payload = EventPayload(pr_number=42, head_sha="abc123")
        summary = _capture_summary(provider, payload)

        assert "ci/build" in summary["ci"]["failed"]
        assert "ci/lint" not in summary["ci"]["failed"]

    def test_pr_files_error_emits_error_summary(self) -> None:
        """File listing failure emits an error decision summary with reason."""
        provider = _make_provider()
        provider.list_pr_files.side_effect = RuntimeError("api unavailable")
        payload = EventPayload(pr_number=42, head_sha="abc123")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "error"
        assert summary["reason"] == "pr_files_listing_failed"
        assert summary["error"] == "api unavailable"
        assert summary["exit_code"] == EXIT_METADATA_FAILED

    def test_repair_dispatch_failure_emits_failure_reason(self) -> None:
        """Repair dispatch failure summary includes a human-readable reason."""
        provider = _make_provider(
            check_runs=[CheckRunStatus(id=2, name="ci/test", status="completed", conclusion="failure")],
            reviews=[],
        )
        provider.dispatch_repair.side_effect = RuntimeError("dispatch endpoint timeout")
        payload = EventPayload(pr_number=42, head_sha="abc123")
        summary = _capture_summary(provider, payload)

        assert summary["decision"] == "repair_failed"
        assert summary["reason"] == "dispatch endpoint timeout"
        assert summary["exit_code"] == EXIT_MERGE_BLOCKED
