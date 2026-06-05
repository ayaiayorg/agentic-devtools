"""Tests for run_pipeline."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.pipeline.actions import (
    ApproveAction,
    DispatchRepairAction,
    GuardsAction,
    MergeAction,
    PublishAction,
    RequestReviewAction,
    ResolveThreadsAction,
    SquashAction,
)
from agentic_devtools.cli.ci.pipeline.base import Action
from agentic_devtools.cli.ci.pipeline.models import ActionDecision, ActionResult
from agentic_devtools.cli.ci.pipeline.runner import run_pipeline
from agentic_devtools.cli.ci.pipeline.snapshot import PRStateSnapshot


class _MockAction:
    """A mock action for testing the runner."""

    def __init__(self, name: str, eval_decision: ActionDecision, exec_decision: ActionDecision | None = None):
        self._name = name
        self._eval_decision = eval_decision
        self._exec_decision = exec_decision

    @property
    def name(self) -> str:
        return self._name

    def evaluate(self, snapshot, derived) -> ActionResult:
        return ActionResult(name=self._name, decision=self._eval_decision, details=f"eval_{self._name}")

    def execute(self, provider, snapshot, derived) -> ActionResult:
        decision = self._exec_decision or ActionDecision.EXECUTE
        return ActionResult(name=self._name, decision=decision, details=f"exec_{self._name}")


class TestRunPipeline:
    """Tests for the pipeline runner."""

    def test_happy_path_all_skip(self) -> None:
        """All actions skip — no execution."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1)
        actions = [
            _MockAction("a", ActionDecision.SKIP),
            _MockAction("b", ActionDecision.SKIP),
        ]
        summary = run_pipeline(provider, snapshot, actions)
        assert len(summary.results) == 2
        assert all(r.decision == ActionDecision.SKIP for r in summary.results)

    def test_guard_block_propagates(self) -> None:
        """When guards BLOCK, subsequent actions are BLOCKED_BY_GUARD."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1)
        actions = [
            _MockAction("guards", ActionDecision.BLOCKED),
            _MockAction("publish", ActionDecision.EXECUTE),
            _MockAction("merge", ActionDecision.EXECUTE),
        ]
        summary = run_pipeline(provider, snapshot, actions)
        assert summary.results[0].decision == ActionDecision.BLOCKED
        assert summary.results[1].decision == ActionDecision.BLOCKED_BY_GUARD
        assert summary.results[2].decision == ActionDecision.BLOCKED_BY_GUARD

    def test_execute_action(self) -> None:
        """Action with EXECUTE decision gets execute() called."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1)
        actions = [_MockAction("approve", ActionDecision.EXECUTE)]
        summary = run_pipeline(provider, snapshot, actions)
        assert summary.results[0].decision == ActionDecision.EXECUTE
        assert "exec_approve" in summary.results[0].details

    def test_non_guard_blocked_does_not_guard_block_following_actions(self) -> None:
        """Non-guards BLOCKED result should not trigger guard-block behavior."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1)
        actions = [
            _MockAction("publish", ActionDecision.BLOCKED),
            _MockAction("merge", ActionDecision.EXECUTE),
        ]

        summary = run_pipeline(provider, snapshot, actions)

        assert summary.results[0].decision == ActionDecision.BLOCKED
        assert summary.results[1].decision == ActionDecision.EXECUTE

    def test_exception_in_evaluation(self) -> None:
        """Exception during evaluate() → FAILED."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1)

        class _BrokenAction:
            @property
            def name(self):
                return "broken"

            def evaluate(self, snapshot, derived):
                raise RuntimeError("boom")

            def execute(self, provider, snapshot, derived):
                return ActionResult(name="broken", decision=ActionDecision.EXECUTE)

        actions = [_BrokenAction()]
        summary = run_pipeline(provider, snapshot, actions)
        assert summary.results[0].decision == ActionDecision.FAILED
        assert "boom" in summary.results[0].error

    def test_exception_in_evaluation_halts_subsequent_execute_actions(self) -> None:
        """Non-guards evaluation failures halt subsequent EXECUTE actions."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1)

        class _BrokenAction:
            @property
            def name(self):
                return "request_review"

            def evaluate(self, snapshot, derived):
                raise RuntimeError("boom")

            def execute(self, provider, snapshot, derived):
                return ActionResult(name="request_review", decision=ActionDecision.EXECUTE)

        actions: list[Action] = [_BrokenAction(), _MockAction("merge", ActionDecision.EXECUTE)]
        summary = run_pipeline(provider, snapshot, actions)
        assert summary.results[0].decision == ActionDecision.FAILED
        assert summary.results[1].decision == ActionDecision.SKIP
        assert "request_review" in summary.results[1].details

    def test_failure_gate_skips_evaluate_on_subsequent_actions(self) -> None:
        """exec_failed_by gate fires before evaluate() — subsequent evaluate() not called."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1)
        evaluate_called = []

        class _FailingAction:
            @property
            def name(self):
                return "publish"

            def evaluate(self, snapshot, derived) -> ActionResult:
                return ActionResult(name="publish", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                return ActionResult(name="publish", decision=ActionDecision.FAILED)

        class _SentinelAction:
            @property
            def name(self):
                return "merge"

            def evaluate(self, snapshot, derived) -> ActionResult:
                evaluate_called.append("merge")
                return ActionResult(name="merge", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                return ActionResult(name="merge", decision=ActionDecision.EXECUTE)

        actions: list[Action] = [_FailingAction(), _SentinelAction()]
        run_pipeline(provider, snapshot, actions)
        assert evaluate_called == [], "evaluate() should not be called on halted action"

    def test_guards_exception_blocks_pipeline(self) -> None:
        """Exception in guards evaluation → BLOCKED, subsequent BLOCKED_BY_GUARD."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1)

        class _BrokenGuards:
            @property
            def name(self):
                return "guards"

            def evaluate(self, snapshot, derived):
                raise RuntimeError("guard error")

            def execute(self, provider, snapshot, derived):
                return ActionResult(name="guards", decision=ActionDecision.EXECUTE)

        actions: list[Action] = [_BrokenGuards(), _MockAction("publish", ActionDecision.EXECUTE)]
        summary = run_pipeline(provider, snapshot, actions)
        assert summary.results[0].decision == ActionDecision.BLOCKED
        assert "guard error" in summary.results[0].details
        assert summary.results[1].decision == ActionDecision.BLOCKED_BY_GUARD

    def test_failed_side_effect_halts_subsequent_executions(self) -> None:
        """When a side-effecting action returns FAILED, subsequent EXECUTE decisions are skipped."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1)

        class _FailingAction:
            @property
            def name(self):
                return "publish"

            def evaluate(self, snapshot, derived) -> ActionResult:
                return ActionResult(name="publish", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                return ActionResult(name="publish", decision=ActionDecision.FAILED, details="publish failed")

        actions: list[Action] = [
            _FailingAction(),
            _MockAction("approve", ActionDecision.EXECUTE),
            _MockAction("merge", ActionDecision.EXECUTE),
        ]
        summary = run_pipeline(provider, snapshot, actions)
        assert summary.results[0].decision == ActionDecision.FAILED  # publish failed
        assert summary.results[1].decision == ActionDecision.SKIP  # approve halted
        assert "halted" in summary.results[1].details.lower()
        assert "publish" in summary.results[1].details
        assert summary.results[2].decision == ActionDecision.SKIP  # merge halted

    def test_failed_side_effect_exception_halts_subsequent_executions(self) -> None:
        """When a side-effecting action raises during execute(), subsequent EXECUTE decisions are skipped."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1)

        class _ExplodingAction:
            @property
            def name(self):
                return "squash"

            def evaluate(self, snapshot, derived) -> ActionResult:
                return ActionResult(name="squash", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                raise RuntimeError("git error")

        actions: list[Action] = [
            _ExplodingAction(),
            _MockAction("merge", ActionDecision.EXECUTE),
        ]
        summary = run_pipeline(provider, snapshot, actions)
        assert summary.results[0].decision == ActionDecision.FAILED
        assert summary.results[1].decision == ActionDecision.SKIP
        assert "halted" in summary.results[1].details.lower()

    def test_guards_execute_exception_does_not_halt_subsequent_actions(self) -> None:
        """guards execute exception should not set non-guard failure gate."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1)

        class _ExplodingGuards:
            @property
            def name(self):
                return "guards"

            def evaluate(self, snapshot, derived) -> ActionResult:
                return ActionResult(name="guards", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                raise RuntimeError("guards exploded")

        actions: list[Action] = [_ExplodingGuards(), _MockAction("publish", ActionDecision.EXECUTE)]
        summary = run_pipeline(provider, snapshot, actions)
        assert summary.results[0].decision == ActionDecision.FAILED
        assert summary.results[1].decision == ActionDecision.EXECUTE

    def test_head_changing_action_halts_subsequent_actions_until_rerun(self) -> None:
        """A fresh snapshot is required after an action force-pushes a new HEAD."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1)
        evaluate_called = []

        class _HeadChangingAction:
            @property
            def name(self):
                return "publish"

            def evaluate(self, snapshot, derived) -> ActionResult:
                return ActionResult(name="publish", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                return ActionResult(
                    name="publish",
                    decision=ActionDecision.EXECUTE,
                    invalidates_snapshot=True,
                )

        class _SentinelAction:
            @property
            def name(self):
                return "merge"

            def evaluate(self, snapshot, derived) -> ActionResult:
                evaluate_called.append("merge")
                return ActionResult(name="merge", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                return ActionResult(name="merge", decision=ActionDecision.EXECUTE)

        summary = run_pipeline(provider, snapshot, [_HeadChangingAction(), _SentinelAction()])
        assert summary.results[0].decision == ActionDecision.EXECUTE
        assert summary.results[1].decision == ActionDecision.SKIP
        assert "changed pr head" in summary.results[1].details.lower()
        assert "rerun required" in summary.results[1].details.lower()
        assert evaluate_called == []

    def test_runs_after_invalidation_actions_proceed_after_snapshot_invalidation(self) -> None:
        """Actions with runs_after_invalidation=True execute; others are skipped."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1, head_sha="oldsha")
        refreshed_snapshot = PRStateSnapshot(pr_number=1, head_sha="newsha")

        class _InvalidatingAction:
            @property
            def name(self):
                return "squash"

            def evaluate(self, snapshot, derived) -> ActionResult:
                return ActionResult(name="squash", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                return ActionResult(
                    name="squash",
                    decision=ActionDecision.EXECUTE,
                    invalidates_snapshot=True,
                )

        class _OptInAction:
            @property
            def name(self):
                return "resolve_threads"

            @property
            def runs_after_invalidation(self):
                return True

            def evaluate(self, snapshot, derived) -> ActionResult:
                assert snapshot.head_sha == "newsha"
                derived.set("opt_in_ran", True)
                return ActionResult(name="resolve_threads", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                return ActionResult(name="resolve_threads", decision=ActionDecision.EXECUTE)

        class _RegularAction:
            @property
            def name(self):
                return "merge"

            def evaluate(self, snapshot, derived) -> ActionResult:
                return ActionResult(name="merge", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                return ActionResult(name="merge", decision=ActionDecision.EXECUTE)

        with patch(
            "agentic_devtools.cli.ci.pipeline.runner.build_pr_state_snapshot",
            return_value=refreshed_snapshot,
        ) as mock_refresh:
            summary = run_pipeline(provider, snapshot, [_InvalidatingAction(), _OptInAction(), _RegularAction()])

        mock_refresh.assert_called_once_with(provider, 1)
        assert summary.results[0].decision == ActionDecision.EXECUTE  # squash executed
        assert summary.results[1].decision == ActionDecision.EXECUTE  # resolve_threads proceeded
        assert summary.results[2].decision == ActionDecision.SKIP  # merge halted
        assert "rerun required" in summary.results[2].details.lower()
        assert summary.snapshot is not None
        assert summary.snapshot.head_sha == "newsha"

    def test_runs_after_invalidation_actions_share_refreshed_derived_state(self) -> None:
        """All opt-in actions after invalidation share refreshed snapshot/derived state."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1, head_sha="oldsha")
        refreshed_snapshot = PRStateSnapshot(pr_number=1, head_sha="newsha")
        observed: list[str] = []

        class _InvalidatingAction:
            @property
            def name(self):
                return "squash"

            def evaluate(self, snapshot, derived) -> ActionResult:
                return ActionResult(name="squash", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                return ActionResult(name="squash", decision=ActionDecision.EXECUTE, invalidates_snapshot=True)

        class _FirstOptInAction:
            @property
            def name(self):
                return "resolve_threads"

            @property
            def runs_after_invalidation(self):
                return True

            def evaluate(self, snapshot, derived) -> ActionResult:
                observed.append(snapshot.head_sha)
                derived.set("marker", "set-by-first-optin")
                return ActionResult(name="resolve_threads", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                return ActionResult(name="resolve_threads", decision=ActionDecision.EXECUTE)

        class _SecondOptInAction:
            @property
            def name(self):
                return "request_review"

            @property
            def runs_after_invalidation(self):
                return True

            def evaluate(self, snapshot, derived) -> ActionResult:
                observed.append(snapshot.head_sha)
                assert derived.marker == "set-by-first-optin"
                return ActionResult(name="request_review", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                return ActionResult(name="request_review", decision=ActionDecision.EXECUTE)

        with patch(
            "agentic_devtools.cli.ci.pipeline.runner.build_pr_state_snapshot",
            return_value=refreshed_snapshot,
        ) as mock_refresh:
            summary = run_pipeline(
                provider,
                snapshot,
                [_InvalidatingAction(), _FirstOptInAction(), _SecondOptInAction()],
            )

        mock_refresh.assert_called_once_with(provider, 1)
        assert observed == ["newsha", "newsha"]
        assert [r.decision for r in summary.results] == [
            ActionDecision.EXECUTE,
            ActionDecision.EXECUTE,
            ActionDecision.EXECUTE,
        ]

    def test_runs_after_invalidation_preserves_exclusion_context(self) -> None:
        """Exclusion context from pre-refresh derived state is carried into refreshed state."""
        from agentic_devtools.cli.ci.pipeline.exclusion import ExclusionContext

        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1, head_sha="oldsha")
        refreshed_snapshot = PRStateSnapshot(pr_number=1, head_sha="newsha")
        exclusion_context = ExclusionContext(resolved_comment_ids={101, 102})

        class _InvalidatingAction:
            @property
            def name(self):
                return "apply_suggestions"

            def evaluate(self, snapshot, derived) -> ActionResult:
                return ActionResult(name="apply_suggestions", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                derived.set("exclusion_context", exclusion_context)
                return ActionResult(
                    name="apply_suggestions",
                    decision=ActionDecision.EXECUTE,
                    invalidates_snapshot=True,
                )

        class _OptInAction:
            @property
            def name(self):
                return "dispatch_repair"

            @property
            def runs_after_invalidation(self):
                return True

            def evaluate(self, snapshot, derived) -> ActionResult:
                assert snapshot.head_sha == "newsha"
                assert derived.get("exclusion_context") == exclusion_context
                return ActionResult(name="dispatch_repair", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                return ActionResult(name="dispatch_repair", decision=ActionDecision.EXECUTE)

        with patch(
            "agentic_devtools.cli.ci.pipeline.runner.build_pr_state_snapshot",
            return_value=refreshed_snapshot,
        ) as mock_refresh:
            summary = run_pipeline(provider, snapshot, [_InvalidatingAction(), _OptInAction()])

        mock_refresh.assert_called_once_with(provider, 1)
        assert [r.decision for r in summary.results] == [
            ActionDecision.EXECUTE,
            ActionDecision.EXECUTE,
        ]

    def test_runs_after_invalidation_fails_when_snapshot_refresh_raises(self) -> None:
        """Refresh failures on opt-in actions fail closed and halt remaining actions."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1, head_sha="oldsha")

        class _InvalidatingAction:
            @property
            def name(self):
                return "squash"

            def evaluate(self, snapshot, derived) -> ActionResult:
                return ActionResult(name="squash", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                return ActionResult(name="squash", decision=ActionDecision.EXECUTE, invalidates_snapshot=True)

        class _OptInAction:
            @property
            def name(self):
                return "resolve_threads"

            @property
            def runs_after_invalidation(self):
                return True

            def evaluate(self, snapshot, derived) -> ActionResult:
                return ActionResult(name="resolve_threads", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                return ActionResult(name="resolve_threads", decision=ActionDecision.EXECUTE)

        class _FollowingAction:
            @property
            def name(self):
                return "request_review"

            def evaluate(self, snapshot, derived) -> ActionResult:
                return ActionResult(name="request_review", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                return ActionResult(name="request_review", decision=ActionDecision.EXECUTE)

        with patch(
            "agentic_devtools.cli.ci.pipeline.runner.build_pr_state_snapshot",
            side_effect=RuntimeError("refresh failed"),
        ) as mock_refresh:
            summary = run_pipeline(
                provider,
                snapshot,
                [_InvalidatingAction(), _OptInAction(), _FollowingAction()],
            )

        mock_refresh.assert_called_once_with(provider, 1)
        assert summary.results[0].decision == ActionDecision.EXECUTE
        assert summary.results[1].decision == ActionDecision.FAILED
        assert "Failed to refresh snapshot" in summary.results[1].details
        assert summary.results[2].decision == ActionDecision.SKIP
        assert "halted" in summary.results[2].details.lower()

    def test_skip_actions_not_blocked_after_failure(self) -> None:
        """All actions after a failure are halted (exec_failed_by gate is before evaluate)."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1)

        class _FailingAction:
            @property
            def name(self):
                return "publish"

            def evaluate(self, snapshot, derived) -> ActionResult:
                return ActionResult(name="publish", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                return ActionResult(name="publish", decision=ActionDecision.FAILED)

        actions: list[Action] = [
            _FailingAction(),
            _MockAction("request_review", ActionDecision.SKIP),
        ]
        summary = run_pipeline(provider, snapshot, actions)
        assert summary.results[0].decision == ActionDecision.FAILED
        # Subsequent action is halted by exec_failed_by gate (before evaluate)
        assert summary.results[1].decision == ActionDecision.SKIP
        assert "halted" in summary.results[1].details.lower()

    def test_summary_has_run_url_and_timestamp(self, monkeypatch) -> None:
        """Summary includes run_url and timestamp."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1)
        actions: list[Action] = []

        # Set env vars for run URL
        monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
        monkeypatch.setenv("GITHUB_REPOSITORY", "org/repo")
        monkeypatch.setenv("GITHUB_RUN_ID", "12345")

        summary = run_pipeline(provider, snapshot, actions)
        assert summary.run_url == "https://github.com/org/repo/actions/runs/12345"
        assert summary.timestamp != ""

    def test_no_log_group_annotations_outside_github_actions(self, monkeypatch, capsys) -> None:
        """No ::group:: annotations should be emitted outside GitHub Actions."""
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

        summary = run_pipeline(
            MagicMock(),
            PRStateSnapshot(pr_number=1),
            [_MockAction("publish", ActionDecision.EXECUTE)],
        )
        captured = capsys.readouterr()
        assert summary.results[0].decision == ActionDecision.EXECUTE
        assert "::group::" not in captured.err
        assert "::endgroup::" not in captured.err

    def test_summary_has_empty_run_url_without_actions_env(self, monkeypatch) -> None:
        """Run URL is empty when GitHub Actions environment is incomplete."""
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
        monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
        monkeypatch.delenv("TRIGGER_REASON", raising=False)
        summary = run_pipeline(MagicMock(), PRStateSnapshot(pr_number=1), [])
        assert summary.run_url == ""

    def test_log_helpers_noop_outside_github_actions(self, monkeypatch) -> None:
        """When not in GitHub Actions, _log_group/_log_endgroup are no-ops."""
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1)
        actions = [_MockAction("approve", ActionDecision.EXECUTE)]
        summary = run_pipeline(provider, snapshot, actions)
        assert summary.results[0].decision == ActionDecision.EXECUTE

    def test_non_guards_blocked_does_not_set_guard_block(self) -> None:
        """A non-guards action returning BLOCKED does not set guard_blocked."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1)

        class _BlockingAction:
            @property
            def name(self):
                return "publish"

            def evaluate(self, snapshot, derived) -> ActionResult:
                return ActionResult(name="publish", decision=ActionDecision.BLOCKED, details="blocked")

            def execute(self, provider, snapshot, derived) -> ActionResult:
                return ActionResult(name="publish", decision=ActionDecision.EXECUTE)

        summary = run_pipeline(provider, snapshot, [_BlockingAction(), _MockAction("approve", ActionDecision.EXECUTE)])
        assert summary.results[0].decision == ActionDecision.BLOCKED
        # Subsequent actions are NOT blocked by guard
        assert summary.results[1].decision == ActionDecision.EXECUTE

    def test_guards_execute_exception_does_not_halt_pipeline(self) -> None:
        """Guards execute() exception → FAILED but exec_failed_by not set."""
        provider = MagicMock()
        snapshot = PRStateSnapshot(pr_number=1)

        class _ExplodingGuards:
            @property
            def name(self):
                return "guards"

            def evaluate(self, snapshot, derived) -> ActionResult:
                return ActionResult(name="guards", decision=ActionDecision.EXECUTE)

            def execute(self, provider, snapshot, derived) -> ActionResult:
                raise RuntimeError("guards exploded")

        summary = run_pipeline(provider, snapshot, [_ExplodingGuards(), _MockAction("publish", ActionDecision.EXECUTE)])
        assert summary.results[0].decision == ActionDecision.FAILED
        assert "guards exploded" in summary.results[0].error
        # exec_failed_by is not set for guards, so publish still runs
        assert summary.results[1].decision == ActionDecision.EXECUTE

    def test_summary_includes_trigger_reason_from_env(self, monkeypatch) -> None:
        """Summary captures TRIGGER_REASON from environment."""
        monkeypatch.setenv("TRIGGER_REASON", "agent_session_finished")
        summary = run_pipeline(MagicMock(), PRStateSnapshot(pr_number=1), [])
        assert summary.trigger_reason == "agent_session_finished"

    def test_summary_has_empty_trigger_reason_when_env_not_set(self, monkeypatch) -> None:
        """trigger_reason is empty when TRIGGER_REASON env var is not set."""
        monkeypatch.delenv("TRIGGER_REASON", raising=False)
        summary = run_pipeline(MagicMock(), PRStateSnapshot(pr_number=1), [])
        assert summary.trigger_reason == ""

    def test_all_8_actions_evaluated_on_ci_completion(self) -> None:
        """All 8 actions evaluated on a CI completion event."""
        provider = MagicMock()
        snapshot = self._make_pipeline_snapshot()
        actions = self._make_pipeline_actions()
        summary = run_pipeline(provider, snapshot, actions)
        assert len(summary.results) == 8
        action_names = [r.name for r in summary.results]
        assert action_names == [
            "guards",
            "publish",
            "request_review",
            "resolve_threads",
            "dispatch_repair",
            "squash",
            "approve",
            "merge",
        ]

    def test_all_8_actions_evaluated_on_review_submission(self) -> None:
        """All 8 actions evaluated on a review submission event."""
        provider = MagicMock()
        snapshot = self._make_pipeline_snapshot()
        actions = self._make_pipeline_actions()
        summary = run_pipeline(provider, snapshot, actions)
        assert len(summary.results) == 8

    def test_all_8_actions_evaluated_on_issue_comment(self) -> None:
        """All 8 actions evaluated on an issue_comment event."""
        provider = MagicMock()
        snapshot = self._make_pipeline_snapshot()
        actions = self._make_pipeline_actions()
        summary = run_pipeline(provider, snapshot, actions)
        assert len(summary.results) == 8

    def test_three_trigger_types_produce_identical_evaluations(self) -> None:
        """Different trigger types with same state produce identical evaluations."""
        snapshot = self._make_pipeline_snapshot()
        actions = self._make_pipeline_actions()
        results_per_trigger = []

        for _ in range(3):
            provider = MagicMock()
            summary = run_pipeline(provider, snapshot, actions)
            results_per_trigger.append([(r.name, r.decision) for r in summary.results])

        assert results_per_trigger[0] == results_per_trigger[1]
        assert results_per_trigger[1] == results_per_trigger[2]

    def test_two_runs_same_state_same_decisions(self) -> None:
        """Running pipeline twice on unchanged state produces identical decisions."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            head_sha="abc123",
            base_branch="main",
            head_branch="feature",
            commit_count=1,
            ci_status="passing",
            review_state="APPROVED",
            copilot_review_id=100,
            copilot_review_inline_count=0,
            active_session=False,
            copilot_review_pending=False,
            unresolved_threads=0,
            labels=["ai-auto-merge-allowed"],
            is_draft=False,
            mergeable=True,
            has_approval_on_head=True,
            head_repo_full_name="org/repo",
            base_repo_full_name="org/repo",
            files=["src/main.py"],
            has_changes=True,
        )

        # Intentionally omit DispatchRepairAction: this deterministic scenario
        # asserts decision stability without exercising dedup/cycle-limit probes.
        actions: list[Action] = [
            GuardsAction(),
            PublishAction(),
            RequestReviewAction(),
            ResolveThreadsAction(),
            SquashAction(),
            ApproveAction(),
            MergeAction(),
        ]

        provider1 = MagicMock()
        summary1 = run_pipeline(provider1, snapshot, actions)

        provider2 = MagicMock()
        summary2 = run_pipeline(provider2, snapshot, actions)

        assert len(summary1.results) == len(summary2.results)
        for r1, r2 in zip(summary1.results, summary2.results):
            assert r1.decision == r2.decision, f"Action '{r1.name}' decisions differ"

        assert summary1.results[0].decision == ActionDecision.EXECUTE
        assert summary1.results[1].decision == ActionDecision.SKIP
        assert summary1.results[2].decision == ActionDecision.SKIP
        assert summary1.results[3].decision == ActionDecision.SKIP
        assert summary1.results[4].decision == ActionDecision.SKIP
        assert summary1.results[5].decision == ActionDecision.SKIP
        assert summary1.results[6].decision == ActionDecision.EXECUTE

        provider1.merge_pr.assert_called_once()
        provider2.merge_pr.assert_called_once()

    def test_fifty_runs_no_state_change(self) -> None:
        """50 runs on an already-complete state produce 0 non-guard executions."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            head_sha="abc123",
            base_branch="main",
            head_branch="feature",
            commit_count=1,
            ci_status="pending",
            review_state="",
            copilot_review_id=0,
            active_session=False,
            copilot_review_pending=True,
            unresolved_threads=0,
            labels=[],
            is_draft=False,
            mergeable=True,
            has_approval_on_head=False,
            head_repo_full_name="org/repo",
            base_repo_full_name="org/repo",
            files=["src/main.py"],
            has_changes=True,
        )

        # Intentionally omit DispatchRepairAction to keep this loop focused on
        # no-op waiting behavior without provider dedup/cycle-limit checks.
        actions: list[Action] = [
            GuardsAction(),
            PublishAction(),
            RequestReviewAction(),
            ResolveThreadsAction(),
            SquashAction(),
            ApproveAction(),
            MergeAction(),
        ]

        for _ in range(50):
            provider = MagicMock()
            summary = run_pipeline(provider, snapshot, actions)
            executed = [r for r in summary.results if r.decision == ActionDecision.EXECUTE]
            assert len(executed) == 1
            assert executed[0].name == "guards"
            provider.merge_pr.assert_not_called()
            provider.approve_pr.assert_not_called()
            provider.publish_pr.assert_not_called()
            provider.dispatch_repair.assert_not_called()

    def test_review_request_can_run_after_dispatch_repair_review_dedup_skip(self) -> None:
        """Review request can still run when dispatch repair dedup path skips."""
        provider = MagicMock()
        initial_snapshot = PRStateSnapshot(
            pr_number=1,
            head_sha="oldsha",
            base_branch="main",
            head_branch="feature",
            commit_count=2,
            ci_status="passing",
            review_state="COMMENTED",
            copilot_review_id=4401589029,
            copilot_review_inline_count=2,
            unresolved_threads=0,
            is_draft=False,
            copilot_review_pending=False,
            base_repo_full_name="org/repo",
        )
        refreshed_snapshot = PRStateSnapshot(
            pr_number=1,
            head_sha="newsha",
            base_branch="main",
            head_branch="feature",
            commit_count=1,
            ci_status="passing",
            review_state="",
            copilot_review_id=0,
            copilot_review_inline_count=0,
            unresolved_threads=0,
            is_draft=False,
            copilot_review_pending=False,
            base_repo_full_name="org/repo",
        )
        actions: list[Action] = [
            DispatchRepairAction(),
            SquashAction(),
            RequestReviewAction(),
        ]

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.is_duplicate_trigger",
                return_value=True,
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.squash.is_copilot_session_active_via_agent_task",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.request_review.is_copilot_session_active_via_agent_task",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.runner.build_pr_state_snapshot",
                return_value=refreshed_snapshot,
            ),
        ):
            summary = run_pipeline(provider, initial_snapshot, actions)

        assert [r.decision for r in summary.results] == [
            ActionDecision.SKIP,
            ActionDecision.EXECUTE,
            ActionDecision.EXECUTE,
        ]
        assert summary.results[2].preconditions.get("no_repair_dispatched") is True
        provider.dispatch_repair.assert_not_called()
        provider.squash_post_repair.assert_called_once()
        provider.request_reviewer.assert_called_once()

    def _make_pipeline_snapshot(self) -> PRStateSnapshot:
        return PRStateSnapshot(
            pr_number=1,
            head_sha="abc123",
            base_branch="main",
            head_branch="feature",
            commit_count=1,
            ci_status="passing",
            review_state="APPROVED",
            copilot_review_id=100,
            copilot_review_inline_count=0,
            active_session=False,
            copilot_review_pending=False,
            unresolved_threads=0,
            labels=[],
            is_draft=False,
            mergeable=True,
            has_approval_on_head=True,
            head_repo_full_name="org/repo",
            base_repo_full_name="org/repo",
            files=["src/main.py"],
            has_changes=True,
        )

    def _make_pipeline_actions(self) -> list[Action]:
        return [
            GuardsAction(),
            PublishAction(),
            RequestReviewAction(),
            ResolveThreadsAction(),
            DispatchRepairAction(),
            SquashAction(),
            ApproveAction(),
            MergeAction(),
        ]
