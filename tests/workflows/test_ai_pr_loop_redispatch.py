"""Tests for ai-pr-loop-redispatch.yml workflow structure."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
AI_PR_LOOP_REDISPATCH = REPO_ROOT / ".github" / "workflows" / "ai-pr-loop-redispatch.yml"


class TestAiPrLoopRedispatch:
    """Validates ai-pr-loop-redispatch workflow structure and requirements."""

    def test_workflow_file_exists(self) -> None:
        assert AI_PR_LOOP_REDISPATCH.exists()

    def test_valid_yaml(self) -> None:
        content = AI_PR_LOOP_REDISPATCH.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)
        assert parsed is not None
        assert "jobs" in parsed
        assert "smart-redispatch" in parsed["jobs"]

    def test_has_only_workflow_dispatch_trigger(self) -> None:
        content = AI_PR_LOOP_REDISPATCH.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)
        triggers = set(parsed[True].keys()) if isinstance(parsed[True], dict) else set()
        assert triggers == {"workflow_dispatch"}

    def test_has_required_permissions(self) -> None:
        content = AI_PR_LOOP_REDISPATCH.read_text(encoding="utf-8")
        assert "actions: write" in content
        assert "pull-requests: read" in content
        assert "contents: read" in content

    def test_has_concurrency_group_with_cancel(self) -> None:
        content = AI_PR_LOOP_REDISPATCH.read_text(encoding="utf-8")
        assert "ai-pr-loop-redispatch" in content
        assert "cancel-in-progress: true" in content

    def test_has_timeout_minutes_8(self) -> None:
        content = AI_PR_LOOP_REDISPATCH.read_text(encoding="utf-8")
        assert "timeout-minutes: 8" in content

    def test_uses_agdt_pr_approver_pat(self) -> None:
        content = AI_PR_LOOP_REDISPATCH.read_text(encoding="utf-8")
        assert "AGDT_PR_APPROVER_PAT" in content

    def test_checks_for_eligible_open_prs(self) -> None:
        content = AI_PR_LOOP_REDISPATCH.read_text(encoding="utf-8")
        assert "ai-pr-loop-ignore" in content
        assert "should_dispatch=false" in content
        assert "should_dispatch=true" in content

    def test_checks_24_hour_stale_merge_guard(self) -> None:
        content = AI_PR_LOOP_REDISPATCH.read_text(encoding="utf-8")
        assert "24" in content
        assert "HOURS_SINCE_MERGE" in content

    def test_calculates_sleep_duration_with_cooldown(self) -> None:
        content = AI_PR_LOOP_REDISPATCH.read_text(encoding="utf-8")
        assert "COOLDOWN" in content
        assert "sleep_seconds" in content
        assert "ai-pr-loop-throttler.yml/runs" in content

    def test_sleeps_before_dispatch(self) -> None:
        content = AI_PR_LOOP_REDISPATCH.read_text(encoding="utf-8")
        assert "sleep" in content
        assert "sleep_seconds" in content

    def test_dispatches_ai_pr_loop_throttler(self) -> None:
        content = AI_PR_LOOP_REDISPATCH.read_text(encoding="utf-8")
        assert "gh workflow run ai-pr-loop-throttler.yml" in content
        assert "default_branch" in content

    def test_stop_conditions_are_guarded(self) -> None:
        """Stop condition steps only run when should_dispatch is true."""
        content = AI_PR_LOOP_REDISPATCH.read_text(encoding="utf-8")
        assert "steps.check.outputs.should_dispatch == 'true'" in content

    def test_exits_cleanly_on_no_eligible_prs(self) -> None:
        content = AI_PR_LOOP_REDISPATCH.read_text(encoding="utf-8")
        assert "No eligible open PRs" in content

    def test_exits_cleanly_on_stale_main(self) -> None:
        content = AI_PR_LOOP_REDISPATCH.read_text(encoding="utf-8")
        assert "human intervention" in content
