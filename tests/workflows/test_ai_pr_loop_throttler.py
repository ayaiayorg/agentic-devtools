"""Tests for ai-pr-loop-throttler.yml workflow structure (PR Scheduler)."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
AI_PR_LOOP_THROTTLER = REPO_ROOT / ".github" / "workflows" / "ai-pr-loop-throttler.yml"


class TestAiPrLoopThrottler:
    """Validates ai-pr-loop-throttler workflow structure and requirements."""

    def test_workflow_file_exists(self) -> None:
        assert AI_PR_LOOP_THROTTLER.exists()

    def test_has_workflow_dispatch_trigger(self) -> None:
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert "workflow_dispatch:" in content

    def test_has_no_schedule_trigger(self) -> None:
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert "schedule:" not in content
        assert "*/5 * * * *" not in content

    def test_has_required_permissions(self) -> None:
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert "contents: read" in content
        assert "pull-requests: write" in content
        assert "actions: write" in content
        assert "issues: write" in content

    def test_has_timeout_minutes_6(self) -> None:
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert "timeout-minutes: 6" in content

    def test_has_concurrency_group(self) -> None:
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert "group: ai-pr-loop-throttler" in content
        assert "cancel-in-progress: false" in content

    def test_uses_agdt_pr_approver_pat(self) -> None:
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert "AGDT_PR_APPROVER_PAT" in content

    def test_dispatches_ai_pr_loop_with_correct_fields(self) -> None:
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert "gh workflow run ai-pr-loop.yml" in content
        assert 'pr_number="$pr"' in content
        assert "trigger_reason=scheduler_oldest_eligible" in content

    def test_filters_fork_prs(self) -> None:
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert "isCrossRepository" in content
        assert "reason=fork_pr" in content

    def test_filters_ignored_prs(self) -> None:
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert "ai-pr-loop-ignore" in content
        assert "reason=ai_pr_loop_ignore_label" in content

    def test_only_has_workflow_dispatch_trigger(self) -> None:
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)
        # YAML parses 'on' as True, so use True as key
        triggers = set(parsed[True].keys()) if isinstance(parsed[True], dict) else set()
        assert triggers == {"workflow_dispatch"}

    def test_valid_yaml(self) -> None:
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)
        assert parsed is not None
        assert "jobs" in parsed
        assert "monitor-agent-sessions" in parsed["jobs"]

    def test_has_dry_run_support(self) -> None:
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert "DRY_RUN" in content
        assert 'is_truthy "${DRY_RUN:-}"' in content

    def test_has_scan_budget_enforcement(self) -> None:
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert "SCAN_BUDGET_SECONDS" in content
        assert "budget_exceeded" in content
        assert "reason=budget_exhausted" in content

    def test_has_step_summary_output(self) -> None:
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert "GITHUB_STEP_SUMMARY" in content

    def test_orders_prs_by_creation_date_ascending(self) -> None:
        """Scheduler must select oldest PR first."""
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert "CREATED_AT" in content
        assert "ASC" in content

    def test_dispatches_at_most_one_pr_per_cycle(self) -> None:
        """Scheduler must dispatch exactly one PR then break."""
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        # After dispatching, the loop must break
        assert "break" in content
        # Only one dispatch variable increment
        assert "DISPATCHES=1" in content

    def test_detects_human_blocked_state(self) -> None:
        """Scheduler must skip PRs that are merge-ready but lack ai-auto-merge-allowed."""
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert "human_blocked" in content
        assert "ai-auto-merge-allowed" in content
        assert "reason=human_blocked" in content

    def test_selects_oldest_eligible_pr(self) -> None:
        """Scheduler logs the selection reason as oldest_eligible."""
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert "reason=oldest_eligible" in content
        assert "action=selected" in content

    def test_logs_skip_reasons(self) -> None:
        """Scheduler must log why each PR was skipped."""
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert "action=skipped" in content
        # Multiple skip reasons documented
        assert "reason=fork_pr" in content
        assert "reason=ai_pr_loop_ignore_label" in content
        assert "reason=human_blocked" in content

    def test_no_multi_pr_dispatch(self) -> None:
        """Scheduler must NOT dispatch multiple PRs in one cycle."""
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        # The dispatch count is set to 1 (not incremented)
        lines = content.split("\n")
        found_increments = [line for line in lines if "DISPATCHES=$((DISPATCHES + 1))" in line]
        assert len(found_increments) == 0, "Should not use increment — uses fixed DISPATCHES=1"

    def test_exits_cleanly_when_no_eligible_pr(self) -> None:
        """Scheduler exits 0 when no PR is eligible."""
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert "reason=no_eligible_pr" in content
        assert "reason=no_open_prs" in content

    def test_check_runs_api_failure_is_fail_safe(self) -> None:
        """Check-runs API failures must fail safe (not leave CHECK_RUNS_OK=true)."""
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        # The fallback on API failure must be a non-zero value so CHECK_RUNS_OK is set to false,
        # matching the fail-safe behaviour of the other API fallbacks (HAS_APPROVAL defaults to
        # false, COMBINED_STATUS_JSON defaults to state=unknown/total_count=-1).
        assert 'CHECK_RUNS_JSON="-1"' in content
        assert 'CHECK_RUNS_JSON="0"' not in content

    def test_pending_check_runs_block_ci_passing(self) -> None:
        """Queued/in-progress checks must prevent CI_PASSING from being true."""
        content = AI_PR_LOOP_THROTTLER.read_text(encoding="utf-8")
        assert 'select((.status != "completed") or' in content
