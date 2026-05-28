"""Tests for run_ai_pr_loop_v2 command."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.models import EventPayload
from agentic_devtools.cli.ci.pipeline.command import (
    EXIT_GUARD_BLOCKED,
    EXIT_METADATA_FAILED,
    EXIT_SUCCESS,
    run_ai_pr_loop_v2,
)


class TestRunAiPrLoopV2:
    """Tests for the pipeline v2 command entry point."""

    def test_returns_success_when_no_pr_number(self) -> None:
        provider = MagicMock()
        event = EventPayload(pr_number=0)
        result = run_ai_pr_loop_v2(provider, event)
        assert result == EXIT_SUCCESS

    def test_returns_metadata_failed_on_snapshot_error(self) -> None:
        """Snapshot build failure after lock acquisition returns EXIT_METADATA_FAILED."""
        provider = MagicMock()
        provider.get_pr_metadata.side_effect = RuntimeError("API error")
        event = EventPayload(pr_number=1)
        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.command.acquire_lock",
                return_value="token-abc",
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.command.release_lock",
            ),
        ):
            result = run_ai_pr_loop_v2(provider, event)
            assert result == EXIT_METADATA_FAILED

    def test_lock_acquired_before_snapshot(self) -> None:
        """Lock must be acquired before building the snapshot to save API quota on races."""
        call_order: list[str] = []
        provider = MagicMock()

        def _acquire(p, pr):
            call_order.append("acquire_lock")
            return "tok"

        def _get_meta(pr):
            call_order.append("get_pr_metadata")
            raise RuntimeError("stop here")

        provider.get_pr_metadata.side_effect = _get_meta
        event = EventPayload(pr_number=1)

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.command.acquire_lock",
                side_effect=_acquire,
            ),
            patch("agentic_devtools.cli.ci.pipeline.command.release_lock"),
        ):
            run_ai_pr_loop_v2(provider, event)

        assert call_order == ["acquire_lock", "get_pr_metadata"], "Lock must be acquired before building the snapshot"

    def test_snapshot_not_built_when_lock_not_acquired(self) -> None:
        """When lock returns None (already held), snapshot API calls are never made."""
        provider = MagicMock()
        event = EventPayload(pr_number=1)

        with patch(
            "agentic_devtools.cli.ci.pipeline.command.acquire_lock",
            return_value=None,
        ):
            result = run_ai_pr_loop_v2(provider, event)
            assert result == EXIT_SUCCESS
            provider.get_pr_metadata.assert_not_called()

    def test_guard_blocked_returns_guard_exit_code(self) -> None:
        provider = MagicMock()
        provider.get_pr_metadata.return_value = MagicMock(
            head_sha="abc",
            base_branch="main",
            head_branch="feat",
            labels=["ai-pr-loop-ignore"],
            requested_reviewers=[],
            is_draft=False,
            mergeable=True,
            title="test",
            head_repo_full_name="o/r",
            base_repo_full_name="o/r",
            number=1,
        )
        provider.list_pr_files.return_value = ["src/main.py"]
        provider.list_check_runs.return_value = []
        provider.list_reviews.return_value = []
        provider.list_pr_issue_events.return_value = []
        provider.count_commits_above_merge_base.return_value = 1
        provider.find_comment.return_value = None

        event = EventPayload(pr_number=1)

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.command.acquire_lock",
                return_value="token-123",
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.command.release_lock",
            ),
        ):
            result = run_ai_pr_loop_v2(provider, event)
            assert result == EXIT_GUARD_BLOCKED

    def test_pipeline_runs_resolve_threads_before_request_review(self) -> None:
        """Thread resolution must run before review requests in the same pipeline pass."""
        provider = MagicMock()
        event = EventPayload(pr_number=1)

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.command.acquire_lock",
                return_value="token-123",
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.command.release_lock",
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.command.build_pr_state_snapshot",
                return_value=MagicMock(),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.command.run_pipeline",
            ) as mock_run_pipeline,
            patch(
                "agentic_devtools.cli.ci.pipeline.command.post_summary_comment",
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.command._determine_exit_code",
                return_value=EXIT_SUCCESS,
            ),
        ):
            run_ai_pr_loop_v2(provider, event)

        actions = mock_run_pipeline.call_args.args[2]
        action_names = [action.name for action in actions]
        assert action_names.index("resolve_threads") < action_names.index("request_review")
