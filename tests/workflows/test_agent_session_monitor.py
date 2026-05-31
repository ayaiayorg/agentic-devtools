"""Tests for agent-session-monitor.yml workflow structure."""

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_SESSION_MONITOR = REPO_ROOT / ".github" / "workflows" / "agent-session-monitor.yml"
TEST_FIXTURE = REPO_ROOT / ".github" / "test-fixtures" / "seen-events-sample.json"


class TestAgentSessionMonitor:
    """Validates agent-session-monitor workflow structure and requirements."""

    def test_workflow_file_exists(self) -> None:
        assert AGENT_SESSION_MONITOR.exists()

    def test_has_schedule_trigger_every_5_minutes(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "schedule:" in content
        assert "*/5 * * * *" in content

    def test_has_workflow_dispatch_trigger(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "workflow_dispatch:" in content

    def test_has_required_permissions(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "contents: read" in content
        assert "pull-requests: write" in content
        assert "actions: write" in content
        assert "issues: write" in content

    def test_has_timeout_minutes_6(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "timeout-minutes: 6" in content

    def test_has_concurrency_group(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "agent-session-monitor" in content
        assert "cancel-in-progress: false" in content

    def test_uses_agdt_pr_approver_pat(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "AGDT_PR_APPROVER_PAT" in content

    def test_dispatches_ai_pr_loop_with_correct_fields(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "gh workflow run ai-pr-loop.yml" in content
        assert 'pr_number="$pr"' in content
        assert "trigger_reason=agent_session_finished" in content

    def test_filters_terminal_events(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "copilot_work_finished" in content
        assert "copilot_work_finished_failure" in content

    def test_filters_fork_prs(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "isCrossRepository" in content
        assert "reason=fork_pr" in content

    def test_filters_ignored_prs(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "ai-pr-loop-ignore" in content
        assert "reason=ai_pr_loop_ignore_label" in content

    def test_uses_comment_based_deduplication(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "agent-session-tracker" in content
        assert "is_tracked" in content
        assert "already_tracked" in content

    def test_no_actions_cache_steps(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "actions/cache/restore" not in content
        assert "actions/cache/save" not in content

    def test_has_dry_run_support(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "DRY_RUN" in content
        assert 'is_truthy "${DRY_RUN:-}"' in content

    def test_has_scan_budget_enforcement(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "SCAN_BUDGET_SECONDS" in content
        assert "budget_exceeded" in content

    def test_has_step_summary_output(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "GITHUB_STEP_SUMMARY" in content

    def test_has_error_isolation(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "SCAN_ERRORS" in content

    def test_has_recency_boundary(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "MAX_EVENT_AGE_SECONDS" in content
        assert "AGENT_MONITOR_MAX_EVENT_AGE" in content
        assert "reason=stale_event" in content
        assert "EVENTS_SKIPPED_STALE" in content

    def test_has_dual_source_detection(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        # Agent-task source
        assert "AGENT_TASKS_JSON" in content
        assert "source=agent-task" in content
        # Events API source
        assert "copilot_work_finished" in content
        # Reviews API source
        assert "reviews" in content
        assert "source=reviews-api" in content

    def test_has_reviews_api_detection(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "pulls/$pr/reviews" in content
        assert "copilot-pull-request-reviewer[bot]" in content

    def test_has_max_prs_per_cycle_env_var(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "AGENT_MONITOR_MAX_PRS_PER_CYCLE" in content

    def test_has_graceful_fallback(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "AGENT_TASK_AVAILABLE" in content
        assert "agent_task_list_failed" in content
        assert "Copilot sessions API" in content

    def test_only_has_schedule_and_dispatch_triggers(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)
        # YAML parses 'on' as True, so use True as key
        triggers = set(parsed[True].keys()) if isinstance(parsed[True], dict) else set()
        assert triggers == {"schedule", "workflow_dispatch"}

    def test_valid_yaml(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)
        assert parsed is not None
        assert "jobs" in parsed
        assert "monitor-agent-sessions" in parsed["jobs"]

    def test_test_fixture_exists_and_valid(self) -> None:
        assert TEST_FIXTURE.exists()
        data = json.loads(TEST_FIXTURE.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) > 0
        assert all(isinstance(i, int) for i in data)

    def test_is_tracked_suppresses_redispatch_when_session_in_body(self) -> None:
        """Behavioral: is_tracked correctly returns true when session ID is in comment."""
        import subprocess

        # The is_tracked function is: grep -qF "| $session_id |" <<< "$comment_body"
        # Simulate it with a subprocess call matching the workflow's logic.
        session_id = "event-12345"
        comment_body_with_id = (
            "<!-- agent-session-tracker\nlast_checked=2026-05-31T00:00:00Z\n-->\n"
            "## Agent Sessions for PR #42\n\n"
            "| Session ID | Status |\n|---|---|\n"
            "| event-12345 | dispatched |\n"
        )
        comment_body_without_id = (
            "<!-- agent-session-tracker\nlast_checked=2026-05-31T00:00:00Z\n-->\n"
            "## Agent Sessions for PR #42\n\n"
            "_Last updated: 2026-05-31T00:00:00Z_\n"
        )

        # Session ID present → grep returns 0 (tracked)
        result = subprocess.run(
            ["grep", "-qF", f"| {session_id} |"],
            input=comment_body_with_id,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, "is_tracked should return true when session ID is in body"

        # Session ID absent → grep returns 1 (not tracked)
        result = subprocess.run(
            ["grep", "-qF", f"| {session_id} |"],
            input=comment_body_without_id,
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0, "is_tracked should return false when session ID is not in body"

    def test_is_tracked_uses_exact_session_cell_match(self) -> None:
        """Behavioral: tracking should not match session ID substrings."""
        import subprocess

        session_id = "event-1"
        comment_body = (
            "<!-- agent-session-tracker\nlast_checked=2026-05-31T00:00:00Z\n-->\n"
            "## Agent Sessions for PR #42\n\n"
            "| Session ID | Status |\n|---|---|\n"
            "| event-12 | dispatched |\n"
        )

        result = subprocess.run(
            ["grep", "-qF", f"| {session_id} |"],
            input=comment_body,
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0, "is_tracked must not treat substrings as exact matches"

    def test_tracker_body_contains_session_ids(self) -> None:
        """Behavioral: the tracker body rendered by the workflow includes session IDs."""
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        # The workflow must write session IDs into the tracker body via a table
        assert "Session ID" in content
        assert "ALL_SESSION_IDS" in content
        # Verify the tracker body includes session ID iteration
        assert "for sid in $ALL_SESSION_IDS" in content

    def test_session_id_regex_roundtrip(self) -> None:
        """Behavioral: session IDs written into table are correctly extracted by regex."""
        import subprocess

        # The workflow renders session IDs as: | <session_id> | dispatched |
        # and extracts them with: grep -oP '(event-\d+|task-[^\s|]+|review-\d+)'
        test_ids = [
            "event-123456789",
            "task-abc-def-123",
            "task-a1b2c3",
            "review-9876543",
        ]

        # Build a table body matching the workflow's rendering format
        table_lines = ["| Session ID | Status |", "|---|---|"]
        for sid in test_ids:
            table_lines.append(f"| {sid} | dispatched |")
        table_body = "\n".join(table_lines) + "\n"

        # Use the same regex the workflow uses to extract session IDs
        result = subprocess.run(
            ["grep", "-oP", r"(event-\d+|task-[^\s|]+|review-\d+)"],
            input=table_body,
            text=True,
            capture_output=True,
        )
        extracted = set(result.stdout.strip().split("\n"))
        assert extracted == set(test_ids), f"Regex extraction mismatch: expected {set(test_ids)}, got {extracted}"

    def test_per_pr_dispatch_deduplication(self) -> None:
        """Structural: workflow deduplicates dispatches per PR per cron tick."""
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "PR_DISPATCH_DONE" in content
        assert "dispatch_already_queued" in content

    def test_tracker_comment_session_count_is_capped(self) -> None:
        """Structural: workflow caps tracked sessions before comment upsert."""
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "AGENT_MONITOR_MAX_TRACKED_SESSIONS" in content
        assert "MAX_TRACKED_SESSIONS" in content
        assert 'read -r -a SESSION_ID_ARRAY <<< "$ALL_SESSION_IDS"' in content
        assert 'if [ "${#SESSION_ID_ARRAY[@]}" -gt "$MAX_TRACKED_SESSIONS" ];' in content
