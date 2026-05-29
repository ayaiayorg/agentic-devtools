"""Tests for run_ai_pr_loop actionable check names handling."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.actionable_checks import DEFAULT_ACTIONABLE_CHECK_NAMES
from agentic_devtools.cli.ci.models import (
    CheckRunStatus,
    EventPayload,
    PRMetadata,
    ReviewInfo,
)
from agentic_devtools.cli.ci.orchestrator import EXIT_REPAIR_DISPATCHED, EXIT_SUCCESS, run_ai_pr_loop


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
        labels=["ai-auto-merge-allowed"],
    )
    provider.list_pr_files.return_value = ["src/main.py"]
    provider.list_check_runs.return_value = check_runs if check_runs is not None else []
    provider.list_reviews.return_value = [
        ReviewInfo(id=1, user="copilot-pull-request-reviewer[bot]", state="APPROVED", body="lgtm"),
    ]
    provider.find_comment.return_value = None
    provider.post_comment.return_value = 100
    provider.merge_pr.return_value = None
    return provider


class TestActionableCheckNames:
    """Tests that only actionable check run names are evaluated during CI gating."""

    def test_non_actionable_check_name_is_ignored(self) -> None:
        """A check outside actionable_check_names should not block merge."""
        ignored = CheckRunStatus(
            id=10,
            name="copilot-pull-request-reviewer",
            status="completed",
            conclusion="failure",
        )
        passing = CheckRunStatus(
            id=11,
            name="Targeted Checks ✅",
            status="completed",
            conclusion="success",
        )
        provider = _make_provider(check_runs=[ignored, passing])
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.merge_pr.assert_called_once()

    def test_no_actionable_checks_observed_treats_as_pending(self) -> None:
        """When no check runs match actionable_check_names, treat as pending.

        This guards against the early-lifecycle case where only non-actionable
        checks (e.g. the workflow's own orchestrator check) exist before the
        gate jobs have been created, preventing premature approve/merge.
        """
        non_actionable_only = CheckRunStatus(
            id=20,
            name="copilot-pull-request-reviewer",
            status="completed",
            conclusion="success",
        )
        provider = _make_provider(check_runs=[non_actionable_only])
        payload = EventPayload(pr_number=42, head_sha="abc123")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.merge_pr.assert_not_called()

    def test_empty_check_runs_treats_as_pending(self) -> None:
        """When check_runs is empty, treat as pending (no actionable checks yet)."""
        provider = _make_provider(check_runs=[])
        payload = EventPayload(pr_number=42, head_sha="abc123")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_SUCCESS
        provider.merge_pr.assert_not_called()

    def test_codeql_failure_triggers_repair(self) -> None:
        """A failing CodeQL check run should trigger repair dispatch."""
        provider = _make_provider(
            check_runs=[
                CheckRunStatus(
                    id=10,
                    name="Code scanning results / CodeQL",
                    status="completed",
                    conclusion="failure",
                    html_url="https://github.com/ayaiayorg/agentic-devtools/runs/123",
                ),
                CheckRunStatus(id=11, name="Targeted Checks ✅", status="completed", conclusion="success"),
            ]
        )
        provider.dispatch_repair.return_value = 200
        payload = EventPayload(pr_number=42, head_sha="abc123", action="submitted")

        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_REPAIR_DISPATCHED
        provider.dispatch_repair.assert_called_once()
        call_kwargs = provider.dispatch_repair.call_args[1]
        failed_check_names = [cr.name for cr in call_kwargs["failed_checks"]]
        assert "Code scanning results / CodeQL" in failed_check_names

    def test_codeql_is_in_default_actionable_check_names(self) -> None:
        from agentic_devtools.cli.ci.orchestrator import _DEFAULT_ACTIONABLE_CHECK_NAMES

        assert "Code scanning results / CodeQL" in _DEFAULT_ACTIONABLE_CHECK_NAMES
        assert _DEFAULT_ACTIONABLE_CHECK_NAMES is DEFAULT_ACTIONABLE_CHECK_NAMES
