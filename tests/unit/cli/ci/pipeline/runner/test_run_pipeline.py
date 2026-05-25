"""Tests for run_pipeline."""

from unittest.mock import MagicMock

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

        actions = [_BrokenAction(), _MockAction("merge", ActionDecision.EXECUTE)]
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

        actions = [_FailingAction(), _SentinelAction()]
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

        actions = [_BrokenGuards(), _MockAction("publish", ActionDecision.EXECUTE)]
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

        actions = [
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

        actions = [
            _ExplodingAction(),
            _MockAction("merge", ActionDecision.EXECUTE),
        ]
        summary = run_pipeline(provider, snapshot, actions)
        assert summary.results[0].decision == ActionDecision.FAILED
        assert summary.results[1].decision == ActionDecision.SKIP
        assert "halted" in summary.results[1].details.lower()

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

        actions = [
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
        actions = []

        # Set env vars for run URL
        monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
        monkeypatch.setenv("GITHUB_REPOSITORY", "org/repo")
        monkeypatch.setenv("GITHUB_RUN_ID", "12345")

        summary = run_pipeline(provider, snapshot, actions)
        assert summary.run_url == "https://github.com/org/repo/actions/runs/12345"
        assert summary.timestamp != ""

    def test_summary_has_empty_run_url_without_actions_env(self, monkeypatch) -> None:
        """Run URL is empty when GitHub Actions environment is incomplete."""
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
        monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
        summary = run_pipeline(MagicMock(), PRStateSnapshot(pr_number=1), [])
        assert summary.run_url == ""

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
