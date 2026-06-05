# Tasks: Rename Workflow Files for Clarity (#1767)

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup — File Renames | Plan Phase 1 | File renames via git mv |
| Phase 2: Foundational — Internal Workflow YAML Updates | Plan Phases 2–3 | Update name: fields and concurrency groups in renamed files |
| Phase 3: User Story 1 — Primary Workflow Rename (P1) | Plan Phases 2–3 | Update comments, step names, and identifier strings in throttler/dispatcher |
| Phase 4: User Story 2 — Cross-Reference Consistency (P1) | Plan Phases 4–8 | Update redispatch.yml, README, Python source, test files, PR_DESCRIPTION |
| Phase 5: User Story 3 — Behavior Preservation (P2) | Plan Phase 9 | Verify workflow triggers, permissions, and YAML syntax |
| Phase 6: Polish & Cross-Cutting — Verification | Plan Phase 9 | Grep sweeps, test runs, and PR checks |

## Phase 1: Setup — File Renames

- [ ] T001 Rename workflow file `agent-session-monitor.yml` → `ai-pr-loop-throttler.yml` via `git mv .github/workflows/agent-session-monitor.yml .github/workflows/ai-pr-loop-throttler.yml` (FR-001)
- [ ] T002 Rename workflow file `pr-activity-dispatch.yml` → `ai-pr-loop-dispatcher.yml` via `git mv .github/workflows/pr-activity-dispatch.yml .github/workflows/ai-pr-loop-dispatcher.yml` (FR-002)
- [ ] T003 Rename test file via `git mv tests/workflows/test_agent_session_monitor.py tests/workflows/test_ai_pr_loop_throttler.py` (FR-006)

## Phase 2: Foundational — Internal Workflow YAML Updates

- [ ] T004 Update `name:` field in `.github/workflows/ai-pr-loop-throttler.yml` to exact value `ai-pr-loop-throttler` (FR-003)
- [ ] T005 Update `name:` field in `.github/workflows/ai-pr-loop-dispatcher.yml` to exact value `ai-pr-loop-dispatcher` (FR-003)
- [ ] T006 Update concurrency group in `.github/workflows/ai-pr-loop-throttler.yml` from `agent-session-monitor` to `ai-pr-loop-throttler` (FR-004)
- [ ] T007 Update concurrency group in `.github/workflows/ai-pr-loop-dispatcher.yml` from `pr-activity-dispatch` to `ai-pr-loop-dispatcher` (FR-004, FR-007)

## Phase 3: User Story 1 — Primary Workflow Rename (P1)

- [ ] T008 [US1] Update all comments and structured log prefixes in `.github/workflows/ai-pr-loop-throttler.yml` replacing `agent-session-monitor` → `ai-pr-loop-throttler` and `pr-activity-dispatch` →
  `ai-pr-loop-dispatcher` (FR-004, FR-005)
- [ ] T009 [P] [US1] Update all comments, step names, API paths, `gh workflow run` targets, and echo strings in `.github/workflows/ai-pr-loop-dispatcher.yml` replacing `agent-session-monitor` →
  `ai-pr-loop-throttler` (FR-004, FR-005)
- [ ] T010 [P] [US1] Update header comments in `.github/workflows/ai-pr-loop-dispatcher.yml` replacing `Agent Session Monitor` → `AI PR Loop Throttler`
  and `PR Activity Dispatch` → `AI PR Loop Dispatcher` (FR-004)
- [ ] T026 [US1] Verify `ai-pr-loop-throttler.yml` exists and its `name:` field equals `ai-pr-loop-throttler` via
  `python -c "import yaml; d=yaml.safe_load(open('.github/workflows/ai-pr-loop-throttler.yml')); assert d['name']=='ai-pr-loop-throttler'"` (FR-001, FR-003)
- [ ] T027 [US1] Verify `ai-pr-loop-dispatcher.yml` exists and its `name:` field equals `ai-pr-loop-dispatcher` via
  `python -c "import yaml; d=yaml.safe_load(open('.github/workflows/ai-pr-loop-dispatcher.yml')); assert d['name']=='ai-pr-loop-dispatcher'"` (FR-002, FR-003)

## Phase 4: User Story 2 — Cross-Reference Consistency (P1)

- [ ] T011 [US2] Update all references in `.github/workflows/ai-pr-loop-redispatch.yml`: comments, API path (`agent-session-monitor.yml` → `ai-pr-loop-throttler.yml`), echo strings, step names, and
  `gh workflow run` target (FR-004)
- [ ] T012 [US2] Update all references to `pr-activity-dispatch` in `.github/workflows/ai-pr-loop-redispatch.yml` comments → `ai-pr-loop-dispatcher` (FR-004)
- [ ] T013 [P] [US2] Update `.github/workflows/README.md` replacing all instances of `agent-session-monitor` → `ai-pr-loop-throttler` and `pr-activity-dispatch` → `ai-pr-loop-dispatcher` (FR-004)
- [ ] T014 [P] [US2] Update docstring/comment in `agentic_devtools/cli/ci/guards.py` replacing `agent-session-monitor` → `ai-pr-loop-throttler` (FR-004)
- [ ] T015 [P] [US2] Update `PR_DESCRIPTION.md` replacing `agent-session-monitor.yml` → `ai-pr-loop-throttler.yml` (FR-004)
- [ ] T016 [US2] Update `tests/workflows/test_ai_pr_loop_throttler.py`: rename class `TestAgentSessionMonitor` → `TestAiPrLoopThrottler`, update docstrings, path constant, variable names
  (`AGENT_SESSION_MONITOR` → `AI_PR_LOOP_THROTTLER`), and all assertion strings (FR-006)
- [ ] T017 [P] [US2] Update `tests/workflows/test_ai_pr_loop_redispatch.py`: replace assertion strings `agent-session-monitor.yml` → `ai-pr-loop-throttler.yml`
  and `gh workflow run agent-session-monitor.yml` → `gh workflow run ai-pr-loop-throttler.yml` (FR-004)
- [ ] T028 [US2] Verify `ai-pr-loop-dispatcher.yml` concurrency group reads `ai-pr-loop-dispatcher` via
  `python -c "import yaml; d=yaml.safe_load(open('.github/workflows/ai-pr-loop-dispatcher.yml')); assert d.get('concurrency', {}).get('group')=='ai-pr-loop-dispatcher'"` (FR-007)

## Phase 5: User Story 3 — Behavior Preservation (P2)

- [ ] T018 [US3] Verify workflow triggers, permissions, jobs, and dispatch payloads remain unchanged in `.github/workflows/ai-pr-loop-throttler.yml` — only identifiers updated, no logic changes
  (FR-005)
- [ ] T019 [US3] Verify workflow triggers, permissions, jobs, and dispatch payloads remain unchanged in `.github/workflows/ai-pr-loop-dispatcher.yml` — only identifiers updated, no logic changes
  (FR-005)
- [ ] T020 [US3] Validate YAML syntax: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ai-pr-loop-throttler.yml'))"` and same for dispatcher (FR-005)

## Phase 6: Polish & Cross-Cutting — Verification

- [ ] T021 Run case-sensitive grep for `agent-session-monitor` across `*.yml`, `*.yaml`, `*.py`, `*.md` (excluding `specs/`) — expect zero results (SC-002, NFR-002)
- [ ] T022 Run case-sensitive grep for `pr-activity-dispatch` across `*.yml`, `*.yaml`, `*.py`, `*.md` (excluding `specs/`) — expect zero results (SC-002, NFR-002)
- [ ] T023 [US1] Run `agdt-test-pattern tests/workflows/ -v` to verify all workflow tests pass (FR-001, FR-002, FR-003, FR-006, NFR-001)
- [ ] T024 [US3] Run full test suite via `agdt-test` + `agdt-task-wait` — zero failures (FR-005, NFR-001, SC-003)
- [ ] T025 Run `bash scripts/run-pr-checks.sh --full` — all PR checks pass (SC-003)

## Dependencies

```text
T001, T002, T003 → no dependencies (execute first)
T004–T007 → depend on T001, T002
T008–T010 → depend on T004, T006
T011–T012 → depend on T001
T013–T015 → depend on T001, T002 (parallelizable with each other)
T016 → depends on T003
T017 → depends on T011
T018–T020 → depend on T008, T009, T011
T026 → depends on T004 (name: field updated in throttler)
T027 → depends on T005 (name: field updated in dispatcher)
T028 → depends on T007 (concurrency group updated in dispatcher)
T021–T022 → depend on all preceding tasks
T023 → depends on T016, T017, T026, T027
T024–T025 → depend on T021, T022, T023, T028
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
