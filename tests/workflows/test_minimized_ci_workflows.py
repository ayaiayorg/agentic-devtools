"""Tests for minimized CI workflow YAMLs."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AI_PR_LOOP = REPO_ROOT / ".github" / "workflows" / "ai-pr-loop.yml"
AI_PR_LOOP_LINT = REPO_ROOT / ".github" / "workflows" / "ai-pr-loop-lint.yml"
SPECKIT_TRIGGER = REPO_ROOT / ".github" / "workflows" / "speckit-issue-trigger.yml"
WORKFLOW_APPROVAL_MONITOR = REPO_ROOT / ".github" / "workflows" / "workflow-approval-monitor.yml"
SQUASH_WAIT_SCHEDULER = REPO_ROOT / ".github" / "workflows" / "squash-wait-scheduler.yml"
AI_PR_LOOP_CONFIG = REPO_ROOT / ".github" / "ai-pr-loop-config.json"
SPECKIT_IMPLEMENT_TRIGGER = REPO_ROOT / ".github" / "workflows" / "speckit-implement-trigger.yml"


def _non_empty_line_count(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


class TestMinimizedCiWorkflows:
    """Validates minimized workflow structure and limits."""

    def test_ai_pr_loop_is_within_line_limit(self) -> None:
        assert _non_empty_line_count(AI_PR_LOOP) <= 120

    def test_speckit_trigger_is_within_line_limit(self) -> None:
        assert _non_empty_line_count(SPECKIT_TRIGGER) <= 180

    def test_ai_pr_loop_uses_single_command_with_feature_flag(self) -> None:
        content = AI_PR_LOOP.read_text(encoding="utf-8")
        assert 'AGDT_USE_PYTHON_ORCHESTRATOR: "1"' in content
        assert content.count("agdt-ai-pr-loop") == 1

    def test_speckit_trigger_dispatches_to_phase_progression(self) -> None:
        content = SPECKIT_TRIGGER.read_text(encoding="utf-8")
        assert "gh api" in content
        assert "speckit-phase-progression.yml" in content

    def test_ai_pr_loop_has_required_setup_steps(self) -> None:
        content = AI_PR_LOOP.read_text(encoding="utf-8")
        assert "actions/setup-python" in content
        assert "pip install" in content
        assert "actions/checkout" in content

    def test_ai_pr_loop_configures_acmarsn_agdt_identity(self) -> None:
        content = AI_PR_LOOP.read_text(encoding="utf-8")
        assert 'git config user.name "acmarsn-agdt"' in content
        assert 'git config user.email "269151600+acmarsn-agdt@users.noreply.github.com"' in content

    def test_speckit_trigger_is_dispatch_only(self) -> None:
        content = SPECKIT_TRIGGER.read_text(encoding="utf-8")
        assert "timeout-minutes: 5" in content
        assert "actions/setup-python" not in content
        assert "pip install" not in content
        assert "actions/checkout" not in content

    def test_ai_pr_loop_has_concurrency_group(self) -> None:
        content = AI_PR_LOOP.read_text(encoding="utf-8")
        assert "concurrency:" in content
        assert "github.event.inputs.pr_number" in content
        assert "replace(replace(replace(" not in content
        assert 'pr_number="${pr_number#"${pr_number%%[! ]*}"}"' not in content

    def test_ai_pr_loop_uses_workflow_dispatch_only(self) -> None:
        content = AI_PR_LOOP.read_text(encoding="utf-8")
        assert "workflow_dispatch:" in content
        assert "pull_request:" not in content
        assert "issue_comment:" not in content
        assert "workflow_run:" not in content

    def test_redundant_ai_pr_loop_workflows_are_removed(self) -> None:
        assert not AI_PR_LOOP_LINT.exists()

    def test_workflow_approval_monitor_deleted(self) -> None:
        assert not WORKFLOW_APPROVAL_MONITOR.exists()

    def test_squash_wait_scheduler_deleted(self) -> None:
        assert not SQUASH_WAIT_SCHEDULER.exists()

    def test_ai_pr_loop_config_deleted(self) -> None:
        assert not AI_PR_LOOP_CONFIG.exists()

    def test_speckit_trigger_has_concurrency_group(self) -> None:
        content = SPECKIT_TRIGGER.read_text(encoding="utf-8")
        assert "concurrency:" in content

    def test_speckit_implement_trigger_validates_assignment_token(self) -> None:
        content = SPECKIT_IMPLEMENT_TRIGGER.read_text(encoding="utf-8")
        assert "- name: Validate Agent Assignment Token" in content
        assert "SPECKIT_PR_TOKEN: ${{ secrets.SPECKIT_PR_TOKEN }}" in content
        assert "COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}" in content
        assert "Neither SPECKIT_PR_TOKEN nor COPILOT_GITHUB_TOKEN is configured" in content

    def test_speckit_implement_trigger_uses_pat_for_assignment_and_followups(self) -> None:
        content = SPECKIT_IMPLEMENT_TRIGGER.read_text(encoding="utf-8")
        token_line = "github-token: ${{ secrets.SPECKIT_PR_TOKEN || secrets.COPILOT_GITHUB_TOKEN }}"
        assert "steps.validate-token.outcome == 'success'" in content
        assert "const tokenIdentity = ${{ toJSON(steps.validate-token.outputs.token_identity) }};" in content
        assert "possible missing repo scope/permissions" in content
        assert token_line in content
        assert content.count(token_line) >= 3
        assert "response.data?.agent_assignment" not in content
        assert content.index("console.log(`Agent assignment token identity: ${tokenIdentity}`);") < content.index(
            "await github.request('PATCH /repos/{owner}/{repo}/issues/{issue_number}'"
        )
