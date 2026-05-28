"""Tests for agent-session-monitor.yml workflow structure."""

import json
import os
import re
import subprocess
import textwrap
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_SESSION_MONITOR = REPO_ROOT / ".github" / "workflows" / "agent-session-monitor.yml"
TEST_FIXTURE = REPO_ROOT / ".github" / "test-fixtures" / "seen-events-sample.json"


def _extract_scan_script() -> str:
    content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
    match = re.search(
        (
            r"      - name: Scan and dispatch\n.*?        run: \|\n"
            r"(?P<script>.*?)(?=\n      - name: Save seen-events cache)"
        ),
        content,
        re.DOTALL,
    )
    assert match is not None
    return textwrap.dedent(match.group("script"))


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
        assert "pull-requests: read" in content
        assert "actions: write" in content
        assert "issues: read" in content

    def test_has_timeout_minutes_2(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "timeout-minutes: 2" in content

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

    def test_has_cache_restore_and_save(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "actions/cache/restore@v4" in content
        assert "actions/cache/save@v4" in content
        assert "agent-monitor-seen-events-" in content
        assert "seen-events.json" in content
        assert "steps.scan.outputs.save_cache == 'true'" in content

    def test_has_dry_run_support(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert "DRY_RUN" in content
        assert 'if is_truthy "${DRY_RUN:-}"; then' in content

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
        # Final step checks for errors after cache save
        assert "Check for scan errors" in content

    def test_prunes_seen_events_to_500(self) -> None:
        content = AGENT_SESSION_MONITOR.read_text(encoding="utf-8")
        assert ".[-500:]" in content

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

    def test_dry_run_skips_seen_events_behaviorally(self, tmp_path: Path) -> None:
        script = _extract_scan_script()

        seen_event_ids = [101, *range(1000, 1501)]
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        (cache_dir / "seen-events.json").write_text(json.dumps(seen_event_ids), encoding="utf-8")

        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        workflow_run_log = tmp_path / "workflow-run.log"
        gh_path = fake_bin / "gh"
        gh_path.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                if [ "$1" = "api" ] && [ "$2" = "graphql" ]; then
                  cat <<'JSON'
                [{"data":{"repository":{"pullRequests":{"nodes":[{"number":42,"isCrossRepository":false,"updatedAt":"2026-05-28T00:00:00Z","labels":{"nodes":[]}}],"pageInfo":{"hasNextPage":false,"endCursor":null}}}}}]
                JSON
                  exit 0
                fi
                if [ "$1" = "api" ]; then
                  cat <<'JSON'
                [{"id":101,"event":"copilot_work_finished"},{"id":202,"event":"copilot_work_finished_failure"}]
                JSON
                  exit 0
                fi
                if [ "$1" = "workflow" ] && [ "$2" = "run" ]; then
                  printf '%s\\n' "$*" >> "$WORKFLOW_RUN_LOG"
                  exit 0
                fi
                echo "unexpected gh invocation: $*" >&2
                exit 1
                """
            ),
            encoding="utf-8",
        )
        gh_path.chmod(0o755)

        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{fake_bin}:{env.get('PATH', '')}",
                "GITHUB_REPOSITORY": "owner/repo",
                "GITHUB_STEP_SUMMARY": str(tmp_path / "step-summary.md"),
                "GITHUB_ENV": str(tmp_path / "github-env.txt"),
                "GH_TOKEN": "dummy-token",
                "DRY_RUN": "true",
                "WORKFLOW_RUN_LOG": str(workflow_run_log),
            }
        )

        result = subprocess.run(
            ["bash", "-c", script],
            cwd=tmp_path,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        assert "event_id=101 event_type=copilot_work_finished action=skipped reason=already_seen" in result.stdout
        assert "event_id=202 event_type=copilot_work_finished_failure action=dispatched mode=dry_run" in result.stdout
        assert result.stdout.count("[DRY_RUN] Would dispatch: gh workflow run ai-pr-loop.yml") == 1
        assert json.loads((cache_dir / "seen-events.json").read_text(encoding="utf-8")) == seen_event_ids
        assert not workflow_run_log.exists()
