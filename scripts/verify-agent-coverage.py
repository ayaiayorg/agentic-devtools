#!/usr/bin/env python3
"""Verify that every workflow step has agent and prompt files."""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = REPO_ROOT / ".github" / "agents"
PROMPTS_DIR = REPO_ROOT / ".github" / "prompts"

SINGLE_STEP_WORKFLOWS = {
    "create-jira-issue": "create-jira-issue",
    "create-jira-epic": "create-jira-epic",
    "create-jira-subtask": "create-jira-subtask",
    "update-jira-issue": "update-jira-issue",
    "apply-pull-request-review-suggestions": "apply-pr-suggestions",
}

EXTRA_WORKFLOW_STEPS = {
    "work-on-jira-issue": {"retrieve"},
}


def load_workflow_steps() -> dict[str, set[str]]:
    manager_path = REPO_ROOT / "agentic_devtools" / "cli" / "workflows" / "manager.py"
    text = manager_path.read_text(encoding="utf-8")

    def extract_block(start_token: str, end_token: str) -> str:
        start_idx = text.find(start_token)
        if start_idx == -1:
            raise RuntimeError(f"Unable to find {start_token} in manager.py")
        end_idx = text.find(end_token, start_idx)
        if end_idx == -1:
            raise RuntimeError(f"Unable to find {end_token} in manager.py")
        return text[start_idx:end_idx]

    def collect_steps(block: str) -> set[str]:
        steps = set()
        steps.update(re.findall(r'initial_step="([^"]+)"', block))
        steps.update(re.findall(r'from_step="([^"]+)"', block))
        steps.update(re.findall(r'to_step="([^"]+)"', block))
        return steps

    work_block = extract_block(
        "WORK_ON_JIRA_ISSUE_WORKFLOW", "PULL_REQUEST_REVIEW_WORKFLOW"
    )
    pr_block = extract_block("PULL_REQUEST_REVIEW_WORKFLOW", "WORKFLOW_REGISTRY")

    return {
        "work-on-jira-issue": collect_steps(work_block),
        "pull-request-review": collect_steps(pr_block),
    }


def expected_agent_name(workflow: str, step: str) -> str:
    return f"agdt.{workflow}.{step}"


def check_file(path: Path) -> bool:
    return path.exists()


def main() -> int:
    workflows = load_workflow_steps()

    expected_steps: list[tuple[str, str, str]] = []

    for workflow_name, steps in workflows.items():
        steps = set(steps)
        steps.update(EXTRA_WORKFLOW_STEPS.get(workflow_name, set()))
        for step in sorted(steps):
            expected_steps.append((workflow_name, workflow_name, step))

    for workflow_name, agent_namespace in SINGLE_STEP_WORKFLOWS.items():
        expected_steps.append((workflow_name, agent_namespace, "initiate"))

    total = 0
    covered = 0
    missing = []

    for workflow_name, agent_namespace, step in sorted(expected_steps):
        agent_name = expected_agent_name(agent_namespace, step)
        agent_path = AGENTS_DIR / f"{agent_name}.agent.md"
        prompt_path = PROMPTS_DIR / f"{agent_name}.prompt.md"
        agent_ok = check_file(agent_path)
        prompt_ok = check_file(prompt_path)
        total += 1
        if agent_ok and prompt_ok:
            covered += 1
            status = "OK"
        else:
            status = "MISSING"
            missing.append(agent_name)
        print(f"{status} {workflow_name}.{step} agent={agent_ok} prompt={prompt_ok}")

    print(f"Coverage: {covered}/{total} steps covered")

    if missing:
        print("Missing steps:")
        for name in missing:
            print(f"- {name}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
