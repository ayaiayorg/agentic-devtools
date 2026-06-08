# Tasks: Prevent @agdt.advance-workflow from Re-initiating Workflows

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1-6 | Phase 1: Rewrite Agent Prompt (Single Phase — Complete Fix) | Tasks split the single implementation phase into setup, story delivery, and verification work. |

## Phase 1: Setup

- [ ] T001 Read and analyze current agent prompt structure at `.github/agents/agdt.advance-workflow.agent.md`
- [ ] T002 Review existing agent prompts in `.github/agents/` for consistent formatting patterns (YAML frontmatter, section hierarchy)
- [ ] T003 [US1] Run existing CLI unit tests covering missing/completed workflow behavior (FR-001, FR-005): `agdt-test-pattern tests/unit/cli/workflows/commands/test_advance_workflow_cmd.py -v`

## Phase 2: Foundational

- [ ] T004 Identify all initiation commands/agents referenced across `.github/agents/` and `.github/prompts/` to build the complete prohibition list for FR-001
- [ ] T005 [US2] Verify `agdt-get-workflow` output format (FR-002, FR-003, FR-005) for active, completed, missing, and corrupted workflow states to inform prompt error handling logic

## Phase 3: User Story 1 — Safe Failure on Missing Workflow State (P1)

- [ ] T006 [US1] Rewrite the `## Purpose` section in `.github/agents/agdt.advance-workflow.agent.md` to clearly state the agent's scope and constraints
- [ ] T007 [US1] Add `## PROHIBITED ACTIONS` section (FR-001, FR-004) explicitly listing all initiation commands/agents that MUST NOT be invoked: `@agdt.pull-request-review.initiate`,
  `agdt-initiate-pull-request-review-workflow`, `agdt-initiate-work-on-jira-issue-workflow`, and any other initiate command/agent
- [ ] T008 [US1] Add completed workflow handling (FR-005) in the Actions section — treat `_workflow.status == "completed"` as inactive and apply the same prohibition against re-initiation
- [ ] T009 [US1] Add corrupted state handling section — report "Corrupted workflow state detected" with specific missing/invalid fields and suggest `agdt-clear-workflow`
- [ ] T010 [US1] Validate the rewritten prompt preserves YAML frontmatter and section hierarchy (FR-001) consistent with other agent prompts in `.github/agents/`

## Phase 4: User Story 2 — Diagnostic Guidance on Failure (P2)

- [ ] T011 [US2] Add `## Failure Output Format` section (FR-002) specifying error must include: "No active workflow found" phrase, full absolute state directory path, and statement that no
  re-initiation will be attempted
- [ ] T012 [US2] Add diagnostic command suggestions (FR-003) in failure output: `agdt-get-workflow` and `agdt-show` as troubleshooting steps, plus mention of state directory mismatch possibility
  referencing issue #1913
- [ ] T013 [US2] Add step-name preservation in error context (FR-007) — when user provides a step argument, include it in the error output so the operator knows which advancement was attempted
- [ ] T014 [US2] Resolve state dir in prompt; invoke with `python3 -c "from agentic_devtools.state import get_state_dir; print(get_state_dir().resolve())"` (fallback: `python`, `py`)

## Phase 5: User Story 3 — Default Single Retry for Race Conditions (P3)

- [ ] T015 [US3] Add retry logic to `## Actions` (FR-006): check `agdt-get-workflow`, delay via `python3 -c "import time; time.sleep(4)"` (fallback: `python`/`py`), then single retry
- [ ] T016 [US3] Add retry logging instruction — agent must output "No active workflow detected. Retrying in 4 seconds..." before the delay
- [ ] T017 [US3] Add explicit retry limit — MUST NOT retry more than once, MUST NOT fall back to re-initiation regardless of retry outcome (reinforces FR-001 and FR-006)

## Phase 6: Polish & Cross-Cutting

- [ ] T018 Run existing CLI happy-path unit tests (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007)
  to verify no regressions: `agdt-test-pattern tests/unit/cli/workflows/commands/test_advance_workflow_cmd.py -v`
- [ ] T019 Invoke `@agdt.advance-workflow` in a no-workflow scenario and verify runtime failure behavior (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007):
  confirm no re-initiation occurs, diagnostics include the state path plus `agdt-get-workflow`/`agdt-show`,
  the single retry is logged, any requested step name is preserved, and plain-text output matches NFR-002
- [ ] T020 Commit changes via `agdt-git-save-work` with conventional commit message referencing issue #1914

## Dependency Graph

```text
T001, T002, T003 → T004, T005 (setup informs foundational)
T004, T005 → T006, T007, T008, T009, T010 (foundational informs US1)
T007 → T011, T012, T013, T014 (prohibition section informs diagnostics)
T011 → T015, T016, T017 (failure format informs retry logic)
T017 → T018, T019 → T020 (all content → validate → commit)
```

## FR Traceability Matrix

| FR | Task(s) |
|----|---------|
| FR-001 (prohibition against initiation) | T003, T007, T010, T017, T018, T019 |
| FR-002 (structured error message with path) | T005, T011, T018, T019 |
| FR-003 (diagnostic command suggestions) | T005, T012, T018, T019 |
| FR-004 (no state modification on failure) | T007, T018, T019 |
| FR-005 (completed workflow = inactive) | T003, T005, T008, T018, T019 |
| FR-006 (single retry with 4s delay) | T015, T016, T017, T018, T019 |
| FR-007 (preserve step-name in error) | T013, T018, T019 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
