"""Tests for minimized CI workflow YAMLs."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AI_PR_LOOP = REPO_ROOT / ".github" / "workflows" / "ai-pr-loop.yml"
AI_PR_LOOP_LINT = REPO_ROOT / ".github" / "workflows" / "ai-pr-loop-lint.yml"
SPECKIT_TRIGGER = REPO_ROOT / ".github" / "workflows" / "speckit-issue-trigger.yml"
WORKFLOW_APPROVAL_MONITOR = REPO_ROOT / ".github" / "workflows" / "workflow-approval-monitor.yml"


def _non_empty_line_count(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


class TestMinimizedCiWorkflows:
    """Validates minimized workflow structure and limits."""

    def test_ai_pr_loop_is_within_line_limit(self) -> None:
        assert _non_empty_line_count(AI_PR_LOOP) <= 90

    def test_speckit_trigger_is_within_line_limit(self) -> None:
        assert _non_empty_line_count(SPECKIT_TRIGGER) <= 40

    def test_ai_pr_loop_uses_single_command_with_feature_flag(self) -> None:
        content = AI_PR_LOOP.read_text(encoding="utf-8")
        assert 'AGDT_USE_PYTHON_ORCHESTRATOR: "1"' in content
        assert content.count("agdt-ai-pr-loop") == 1

    def test_speckit_trigger_uses_single_command_with_feature_flag(self) -> None:
        content = SPECKIT_TRIGGER.read_text(encoding="utf-8")
        assert "AGDT_USE_PYTHON_ORCHESTRATOR:" in content
        assert content.count("agdt-speckit-trigger") == 1

    def test_ai_pr_loop_has_required_setup_steps(self) -> None:
        content = AI_PR_LOOP.read_text(encoding="utf-8")
        assert "actions/setup-python" in content
        assert "pip install" in content
        assert "actions/checkout" in content

    def test_ai_pr_loop_configures_acmarsn_agdt_identity(self) -> None:
        content = AI_PR_LOOP.read_text(encoding="utf-8")
        assert 'git config user.name "acmarsn-agdt"' in content
        assert 'git config user.email "269151600+acmarsn-agdt@users.noreply.github.com"' in content
        assert "Configure git identity\n        if: github.event_name != 'issue_comment'" in content

    def test_speckit_trigger_has_required_setup_steps(self) -> None:
        content = SPECKIT_TRIGGER.read_text(encoding="utf-8")
        assert "timeout-minutes: 30" in content
        assert "actions/setup-python" in content
        assert "pip install" in content
        assert "actions/checkout" in content

    def test_ai_pr_loop_has_concurrency_group(self) -> None:
        content = AI_PR_LOOP.read_text(encoding="utf-8")
        assert "concurrency:" in content
        assert "github.event.pull_request.number" in content
        assert "github.event.issue.number" in content
        assert "github.event.workflow_run.pull_requests" in content

    def test_ai_pr_loop_uses_pull_request_and_ci_completion_triggers(self) -> None:
        content = AI_PR_LOOP.read_text(encoding="utf-8")
        assert "pull_request:" in content
        assert "issue_comment:" in content
        assert "workflow_run:" in content

    def test_redundant_ai_pr_loop_workflows_are_removed(self) -> None:
        assert not AI_PR_LOOP_LINT.exists()
        assert not WORKFLOW_APPROVAL_MONITOR.exists()

    def test_speckit_trigger_has_concurrency_group(self) -> None:
        content = SPECKIT_TRIGGER.read_text(encoding="utf-8")
        assert "concurrency:" in content
