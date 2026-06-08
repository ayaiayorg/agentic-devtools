"""Tests for the reconciliation engine."""

from unittest.mock import MagicMock

import pytest

from agentic_devtools.cli.ci.exceptions import ProviderRateLimitError
from agentic_devtools.cli.ci.reconciliation.engine import reconcile
from agentic_devtools.cli.ci.reconciliation.models import (
    ReconciliationAction,
    WorkflowRun,
)


def _make_run(
    id: int = 1,
    conclusion: str = "failure",
    run_attempt: int = 1,
    created_at: str = "2024-01-15T10:00:00Z",
    event: str = "push",
    head_branch: str = "main",
    **kwargs,
) -> WorkflowRun:
    return WorkflowRun(
        id=id,
        name="speckit-pipeline",
        conclusion=conclusion,
        run_attempt=run_attempt,
        created_at=created_at,
        event=event,
        head_branch=head_branch,
        repository_full_name="owner/repo",
        **kwargs,
    )


class TestReconcileNoEligibleRuns:
    """Tests for reconcile() when no eligible runs exist."""

    def test_no_runs_returns_no_action(self) -> None:
        """No runs found returns NO_ACTION."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = []

        result = reconcile(provider, "ci.yml")

        assert result.action == ReconciliationAction.NO_ACTION
        assert result.run is None
        assert "No retriable runs" in result.message

    def test_only_success_runs_returns_no_action(self) -> None:
        """Runs with success conclusion are not eligible."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(conclusion="success"),
        ]

        result = reconcile(provider, "ci.yml")

        assert result.action == ReconciliationAction.NO_ACTION

    def test_skipped_runs_not_eligible(self) -> None:
        """Runs with 'skipped' conclusion are not eligible."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(conclusion="skipped"),
        ]

        result = reconcile(provider, "ci.yml")

        assert result.action == ReconciliationAction.NO_ACTION


class TestReconcileRetry:
    """Tests for reconcile() retrying a run."""

    def test_oldest_run_retried(self) -> None:
        """Oldest eligible run is retried."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(id=2, created_at="2024-01-15T11:00:00Z"),
            _make_run(id=1, created_at="2024-01-15T10:00:00Z"),
        ]

        result = reconcile(provider, "ci.yml", max_run_attempts=3)

        assert result.action == ReconciliationAction.RETRIED
        assert result.run is not None
        assert result.run.id == 1  # oldest
        provider.rerun_workflow.assert_called_once_with(1)

    def test_single_run_per_invocation(self) -> None:
        """Only one run is retried per invocation."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(id=1, created_at="2024-01-15T10:00:00Z"),
            _make_run(id=2, created_at="2024-01-15T11:00:00Z"),
            _make_run(id=3, created_at="2024-01-15T12:00:00Z"),
        ]

        reconcile(provider, "ci.yml", max_run_attempts=3)

        provider.rerun_workflow.assert_called_once()

    def test_maxed_oldest_run_does_not_block_retryable_newer_run(self) -> None:
        """A maxed-out older run should not block retries for newer eligible runs."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(id=1, run_attempt=3, created_at="2024-01-15T10:00:00Z"),
            _make_run(id=2, run_attempt=2, created_at="2024-01-15T11:00:00Z"),
        ]

        result = reconcile(provider, "ci.yml", max_run_attempts=3)

        assert result.action == ReconciliationAction.RETRIED
        assert result.run is not None
        assert result.run.id == 2
        provider.rerun_workflow.assert_called_once_with(2)
        provider.post_comment.assert_not_called()

    def test_retriable_conclusions_accepted(self) -> None:
        """All retriable conclusions are eligible."""
        for conclusion in ("cancelled", "failure", "timed_out", "startup_failure"):
            provider = MagicMock()
            provider.list_workflow_runs.return_value = [
                _make_run(conclusion=conclusion),
            ]

            result = reconcile(provider, "ci.yml", max_run_attempts=3)

            assert result.action == ReconciliationAction.RETRIED

    def test_invalid_created_at_sorts_after_valid_runs(self) -> None:
        """Invalid timestamps do not outrank valid older runs."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(id=2, created_at="not-a-timestamp"),
            _make_run(id=1, created_at="2024-01-15T10:00:00Z"),
        ]

        result = reconcile(provider, "ci.yml", max_run_attempts=3)

        assert result.action == ReconciliationAction.RETRIED
        assert result.run is not None
        assert result.run.id == 1
        provider.rerun_workflow.assert_called_once_with(1)

    def test_missing_created_at_sorts_after_valid_runs(self) -> None:
        """Empty timestamps sort last, after valid runs."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(id=2, created_at=""),
            _make_run(id=1, created_at="2024-01-15T10:00:00Z"),
        ]

        result = reconcile(provider, "ci.yml", max_run_attempts=3)

        assert result.action == ReconciliationAction.RETRIED
        assert result.run is not None
        assert result.run.id == 1
        provider.rerun_workflow.assert_called_once_with(1)

    def test_naive_created_at_is_treated_as_utc(self) -> None:
        """Naive timestamps are normalized to UTC for ordering."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(id=2, created_at="2024-01-15T11:00:00Z"),
            _make_run(id=1, created_at="2024-01-15T10:00:00"),
        ]

        result = reconcile(provider, "ci.yml", max_run_attempts=3)

        assert result.action == ReconciliationAction.RETRIED
        assert result.run is not None
        assert result.run.id == 1
        provider.rerun_workflow.assert_called_once_with(1)


class TestReconcileEscalation:
    """Tests for reconcile() escalation path."""

    def test_max_attempts_reached_escalates(self) -> None:
        """Run at max attempts triggers escalation."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(id=1, run_attempt=3, event="issue_comment", head_branch="fix-42"),
        ]

        result = reconcile(provider, "ci.yml", max_run_attempts=3)

        assert result.action == ReconciliationAction.ESCALATED
        assert result.run is not None
        assert result.run.id == 1
        provider.rerun_workflow.assert_not_called()

    def test_escalation_posts_comment_to_pr(self) -> None:
        """Escalation posts a comment when context resolves to a PR."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(
                id=10,
                run_attempt=3,
                event="pull_request",
                head_branch="refs/pull/55/merge",
            ),
        ]

        result = reconcile(provider, "ci.yml", max_run_attempts=3)

        assert result.action == ReconciliationAction.ESCALATED
        provider.post_comment.assert_called_once()
        call_args = provider.post_comment.call_args
        assert call_args[0][0] == 55  # PR number
        assert "Escalation" in call_args[0][1]

    def test_escalation_issue_comment_with_explicit_pr_number_posts_comment(self) -> None:
        """issue_comment runs with explicit PR context still escalate to the PR."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(
                id=11,
                run_attempt=3,
                event="issue_comment",
                head_branch="feature/my-branch",
                pr_number=55,
            ),
        ]

        result = reconcile(provider, "ci.yml", max_run_attempts=3)

        assert result.action == ReconciliationAction.ESCALATED
        provider.post_comment.assert_called_once()
        assert provider.post_comment.call_args[0][0] == 55

    def test_escalation_branch_context_no_comment_posted(self) -> None:
        """Escalation with branch-only context does not post a comment."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(
                id=20,
                run_attempt=3,
                event="push",
                head_branch="main",
            ),
        ]

        result = reconcile(provider, "ci.yml", max_run_attempts=3)

        assert result.action == ReconciliationAction.ESCALATED
        provider.post_comment.assert_not_called()

    def test_escalation_issue_context_no_comment_posted(self) -> None:
        """Escalation with issue context does not post a comment."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(
                id=21,
                run_attempt=3,
                event="issue_comment",
                head_branch="issue-42",
            ),
        ]

        result = reconcile(provider, "ci.yml", max_run_attempts=3)

        assert result.action == ReconciliationAction.ESCALATED
        provider.post_comment.assert_not_called()
        assert "no pull-request target or post failed" in result.message

    def test_escalation_body_uses_markdown_link_when_html_url_present(self) -> None:
        """Escalation comment body uses a Markdown link when html_url is set."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(
                id=10,
                run_attempt=3,
                event="pull_request",
                head_branch="refs/pull/55/merge",
                html_url="https://github.com/owner/repo/actions/runs/10",
            ),
        ]

        reconcile(provider, "ci.yml", max_run_attempts=3)

        body = provider.post_comment.call_args[0][1]
        assert "[speckit-pipeline #10](https://github.com/owner/repo/actions/runs/10)" in body

    def test_escalation_body_uses_plain_text_when_html_url_empty(self) -> None:
        """Escalation comment body uses plain text reference when html_url is empty."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(
                id=10,
                run_attempt=3,
                event="pull_request",
                head_branch="refs/pull/55/merge",
                html_url="",
            ),
        ]

        reconcile(provider, "ci.yml", max_run_attempts=3)

        body = provider.post_comment.call_args[0][1]
        # Should not have a Markdown link with empty URL
        assert "]()" not in body
        assert "speckit-pipeline #10" in body


class TestReconcileApiError:
    """Tests for reconcile() API error handling."""

    def test_rerun_api_error_surfaces(self) -> None:
        """API error during rerun is not swallowed."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(id=1),
        ]
        provider.rerun_workflow.side_effect = RuntimeError("API 500")

        with pytest.raises(RuntimeError, match="API 500"):
            reconcile(provider, "ci.yml", max_run_attempts=3)

    def test_list_workflow_runs_not_implemented(self) -> None:
        """NotImplementedError from provider surfaces."""
        provider = MagicMock()
        provider.list_workflow_runs.side_effect = NotImplementedError("not supported")

        with pytest.raises(NotImplementedError):
            reconcile(provider, "ci.yml")

    def test_unmappable_context_continues_without_error(self) -> None:
        """UnmappableContextError in context mapping does not block retry."""
        provider = MagicMock()
        # Use an unsupported event type to trigger UnmappableContextError
        provider.list_workflow_runs.return_value = [
            _make_run(id=1, event="dynamic"),
        ]

        result = reconcile(provider, "ci.yml", max_run_attempts=3)

        assert result.action == ReconciliationAction.RETRIED
        assert result.context is None
        provider.rerun_workflow.assert_called_once_with(1)

    def test_escalation_post_comment_failure_does_not_raise(self) -> None:
        """Escalation proceeds even when post_comment fails."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(
                id=10,
                run_attempt=3,
                event="pull_request",
                head_branch="refs/pull/77/merge",
            ),
        ]
        provider.post_comment.side_effect = RuntimeError("API timeout")

        result = reconcile(provider, "ci.yml", max_run_attempts=3)

        # Should still escalate even though posting failed
        assert result.action == ReconciliationAction.ESCALATED
        provider.post_comment.assert_called_once()

    def test_escalation_unexpected_post_comment_error_does_not_raise(self) -> None:
        """Escalation proceeds even when post_comment raises rate-limit errors."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(
                id=11,
                run_attempt=3,
                event="pull_request",
                head_branch="refs/pull/88/merge",
            ),
        ]
        provider.post_comment.side_effect = ProviderRateLimitError()

        result = reconcile(provider, "ci.yml", max_run_attempts=3)

        assert result.action == ReconciliationAction.ESCALATED
        provider.post_comment.assert_called_once()

    def test_escalation_arbitrary_post_comment_error_does_not_raise(self) -> None:
        """Escalation treats unexpected provider errors as best-effort failures."""
        provider = MagicMock()
        provider.list_workflow_runs.return_value = [
            _make_run(
                id=12,
                run_attempt=3,
                event="pull_request",
                head_branch="refs/pull/99/merge",
            ),
        ]
        provider.post_comment.side_effect = ValueError("bad payload")

        result = reconcile(provider, "ci.yml", max_run_attempts=3)

        assert result.action == ReconciliationAction.ESCALATED
        provider.post_comment.assert_called_once()
