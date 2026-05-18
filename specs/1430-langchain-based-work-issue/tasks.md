# Tasks: LangChain Work-on-Issue Workflow (`--engine langchain`)

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup — Project Scaffolding | — | Initial scaffolding tasks needed before feature implementation phases. |
| Phase 2: Foundational — Blocking Prerequisites | Phase 2 | Shared prerequisites (checkpointing, state schema, lazy imports, git adapter). |
| Phase 3: User Story 1 — Invoke LangGraph Workflow via CLI Flag | Phase 1, Phase 4 | CLI routing/resume behavior and LangChain runner implementation. |
| Phase 4: User Story 2 — Existing Workflow Remains Unchanged | Phase 1 | Non-regression verification for existing default workflow behavior. |
| Phase 5: User Story 3 — Real Tool Integration in Node Functions | Phase 3, Phase 4 | Real node implementations and graph wiring for tool-layer integrations. |
| Phase 6: User Story 4 — Durable Checkpoint Persistence | Phase 2, Phase 4 | Persistence and restart/resume behavior for LangGraph checkpoints. |
| Phase 7: User Story 5 — Side-by-Side Comparison Testing | Phase 5 | Legacy-vs-LangChain comparison validation and performance verification. |
| Phase 8: Polish & Cross-Cutting | Phase 6, Phase 7 | Documentation, full validation, and release readiness checks. |

## Phase 1: Setup — Project Scaffolding

- [ ] T001 Create `__init__.py` files for new test directories under `tests/unit/orchestration/nodes/`, `tests/unit/orchestration/runner/` (FR-003)
- [ ] T002 Create placeholder `agentic_devtools/orchestration/nodes.py` with module docstring and empty imports
- [ ] T003 Create placeholder `agentic_devtools/orchestration/runner.py` with module docstring and empty imports

## Phase 2: Foundational — Blocking Prerequisites

- [ ] T004 Write tests for `get_checkpointer()` worktree-scoped path resolution in `tests/unit/orchestration/checkpointing/test_get_checkpointer.py` (FR-005, NFR-003)
- [ ] T005 Write tests for `sqlite3.DatabaseError` corruption detection and reset in `tests/unit/orchestration/checkpointing/test_get_checkpointer.py` (FR-005)
- [ ] T006 Update `agentic_devtools/orchestration/checkpointing.py` — replace `_get_git_repo_root()` with `get_state_dir()` path resolution (FR-005, NFR-003)
- [ ] T007 Add corruption detection in `checkpointing.py` — catch `sqlite3.DatabaseError` and offer reset path
- [ ] T008 Write tests for `WorkOnIssueState` new typed fields in `tests/unit/orchestration/state_schema/test_workonissuestate.py` (FR-007)
- [ ] T009 Write tests for `WorkOnIssueEvent` optional `node`/`details` keys in `tests/unit/orchestration/state_schema/test_workonissueevent.py` (FR-007)
- [ ] T010 [P] Extend `agentic_devtools/orchestration/state_schema.py` — add `commit_message`, `source_branch`, `pr_title`, `pr_description`, `failed_node`, `resume_target_node`, `idempotency_keys`,
  `artifact_references`, `implementation_result` fields
- [ ] T011 [P] Extend `WorkOnIssueEvent` TypedDict with optional `node: str | None` and `details: dict[str, Any] | None` keys using `NotRequired`
- [ ] T012 Write tests for lazy `__init__.py` exports in `tests/unit/orchestration/test_lazy_imports.py` (FR-009 guard)
- [ ] T013 Refactor `agentic_devtools/orchestration/__init__.py` — replace eager imports with lazy `__getattr__` + `__all__` pattern (FR-009)
- [ ] T014 Write tests for `tools/git.py` orchestration-safe adapter in `tests/unit/tools/git/test_save_work.py` including `_run_op()`/`SystemExit` safety (FR-003)
- [ ] T015 Extend `agentic_devtools/tools/git.py` — add orchestration-safe adapter providing `agdt-git-save-work` parity (sync/rebase, publish-on-first, amend/force-push)

## Phase 3: User Story 1 — Invoke LangGraph Workflow via CLI Flag (P1)

### Tests First (TDD Red)

- [ ] T016 [US1] Write tests for `--engine langchain` flag acceptance in `tests/unit/cli/workflows/commands/test_initiate_work_on_jira_issue_workflow.py` (FR-001)
- [ ] T017 [US1] Write tests for `--use-langchain` alias resolution to `engine="langchain"` in `tests/unit/cli/workflows/commands/test_initiate_work_on_jira_issue_workflow.py` (FR-001)
- [ ] T018 [US1] Write tests for `--resume` requiring LangChain engine selection — exit code 1 when used without `--engine langchain` or `--use-langchain` (FR-011)
- [ ] T019 [US1] Write tests for `--resume-data` without `--resume` rejection (exit code 1) in `tests/unit/cli/workflows/commands/test_initiate_work_on_jira_issue_workflow.py` (FR-013)
- [ ] T020 [US1] Write tests for `--resume-data` invalid JSON and non-object JSON rejection (FR-013)
- [ ] T021 [US1] Write tests for `--resume-data` schema validation — missing `completed`, empty `summary`, invalid `affected_paths` entries (FR-013)
- [ ] T022 [US1] Write tests for "both `--use-langchain` and `--engine` provided" deduplication case (FR-001)
- [ ] T023 [US1] Write tests for routing to runner when `engine=="langchain"` vs existing manager path in `tests/unit/cli/workflows/commands/test_initiate_work_on_jira_issue_workflow.py` (FR-001)

### Implementation (TDD Green)

- [ ] T024 [US1] Add `--engine` argument with choices `["langchain"]` to argparse in `agentic_devtools/cli/workflows/commands.py` (FR-001)
- [ ] T025 [US1] Add `--use-langchain` boolean alias that sets `engine="langchain"` in `agentic_devtools/cli/workflows/commands.py` (FR-001)
- [ ] T026 [US1] Add `--resume` flag with validation requiring LangChain engine selection in `agentic_devtools/cli/workflows/commands.py` (FR-011)
- [ ] T027 [US1] Add `--resume-data` optional JSON string argument with mutual constraint validation in `agentic_devtools/cli/workflows/commands.py` (FR-013)
- [ ] T028 [US1] Implement routing logic — when `engine=="langchain"` call `runner.run_langchain_workflow()`, otherwise existing path in `commands.py`
- [ ] T029 [US1] Forward `--interactive` and `--model` values into the LangGraph runner context via `agent_context`

### Runner Tests (TDD Red)

- [ ] T030 [US1] Write tests for `run_langchain_workflow()` fresh invocation in `tests/unit/orchestration/runner/test_run_langchain_workflow.py` (FR-001)
- [ ] T031 [US1] Write tests for FR-009 dependency guard — mock missing `langgraph` import, assert install message and `sys.exit(1)` (FR-009)
- [ ] T032 [US1] Write tests for FR-009 dependency guard — mock missing `langgraph.checkpoint.sqlite`, assert install message and `sys.exit(1)` (FR-009)
- [ ] T033 [US1] Write tests for resume with no existing checkpoint — exit code 1 with descriptive error (FR-012)
- [ ] T034 [US1] Write tests for resume from `planning_gate` — `Command(resume=True)` invocation (FR-004)
- [ ] T035 [US1] Write tests for resume from `implementation_gate` without `--resume-data` — exit code 1 (FR-013)
- [ ] T036 [US1] Write tests for resume from `implementation_gate` with valid `--resume-data` — `Command(resume=<dict>)` invocation (FR-013)
- [ ] T037 [US1] Write tests for selective checkpoint reset on fresh run — unrelated thread IDs preserved (FR-012)
- [ ] T038 [US1] Write tests for pre-flight auto-setup command reconstruction preserving `--engine langchain`, `--resume`, `--resume-data`, `--skip-copilot-session` (FR-001)
- [ ] T039 [US1] Write tests for `GraphInterrupt` handling and pause message output (FR-004)

### Happy-Path Tests (TDD Red)

- [ ] T105 [US1] Write happy-path success test for `--engine langchain` routing — verify `run_langchain_workflow()` is called with correct args when engine is "langchain", no error raised (FR-001)
- [ ] T106 [US1] Write happy-path success test for `run_langchain_workflow()` fresh invocation — mock graph returns without interrupt, verify exit code 0 and progress messages emitted (FR-001, FR-009)
- [ ] T107 [US1] Write happy-path success test for planning gate resume — checkpoint exists at `planning_gate`, `Command(resume=True)` invoked, workflow resumes and continues to checklist creation (FR-004)
- [ ] T108 [US1] Write happy-path success test for implementation gate resume — checkpoint at `implementation_gate`, valid `--resume-data` accepted, `Command(resume=<dict>)` invoked (FR-013)
- [ ] T109 [US1] Write happy-path success test for `--resume` with existing checkpoint — checkpoint found for issue key, resume flow initiated, exit code 0 (FR-011, FR-012)
- [ ] T110 [US1] Write happy-path success test for dry-run mode — all nodes emit `dry_run_skipped` event, no external API calls made, exit code 0 (FR-006)
- [ ] T111 [US1] Write happy-path success test for audit trail event emission — each completed node emits structured event with expected `node`, `type`, `details` fields (FR-007)
- [ ] T112 [US1] Write happy-path success test for verification first-attempt pass — `verification_node()` routes directly to `commit_node`, retry counter remains at 0 (FR-008)

### Runner Implementation (TDD Green)

- [ ] T040 [US1] Create `agentic_devtools/orchestration/runner.py` — `run_langchain_workflow()` entry point with FR-009 dependency guard
- [ ] T041 [US1] Implement worktree/branch pre-flight logic and scope/bootstrap initialization before `get_state_dir()` calls in `runner.py`
- [ ] T042 [US1] Implement pre-flight auto-setup flow preserving LangGraph flags in reconstructed command in `runner.py`
- [ ] T043 [US1] Implement checkpointer resolution via `get_checkpointer()` after scope initialization in `runner.py` (FR-005)
- [ ] T044 [US1] Implement graph build via `build_work_on_issue_graph(checkpointer=..., node_set="real")` in `runner.py`
- [ ] T045 [US1] Implement fresh invocation path — detect existing checkpoint, warn, selectively reset by `thread_id`, invoke graph
- [ ] T046 [US1] Implement resume path — classify gate type and invoke with appropriate `Command(resume=...)` (FR-004, FR-013)
- [ ] T104 [US1] Write tests for resume path checkpoint-existence guard and gate classification in `tests/unit/orchestration/runner/test_run_langchain_workflow.py` (FR-004, FR-013)
- [ ] T047 [US1] Implement `implementation_gate` resume-data validation in runner before graph invocation (FR-013)
- [ ] T048 [US1] Implement error handling — record `error`/`failed_node`/`resume_target_node` in state, preserve checkpoint
- [ ] T049 [US1] Implement progress message output matching existing workflow UX conventions (NFR-002)
- [ ] T050 [US1] Implement human-in-the-loop pause detection from invoke return values + `GraphInterrupt` fallback (FR-004)

## Phase 4: User Story 2 — Existing Workflow Remains Unchanged (P1)

- [ ] T051 [US2] Write regression tests verifying no-flag invocation routes to `manager.py` state machine in `tests/unit/cli/workflows/commands/test_initiate_work_on_jira_issue_workflow.py` (FR-002)
- [ ] T052 [US2] Write regression tests verifying `agdt-advance-workflow` and `agdt-add-jira-comment` behavior unchanged without `--engine langchain` (FR-002)
- [ ] T053 [US2] Verify no modifications to pull request review workflow files (FR-010)
- [ ] T113 [US2] Write happy-path success test for default invocation — no `--engine` flag routes to `manager.py` state machine and completes without error (FR-002)
- [ ] T114 [US2] Write happy-path success test for PR review workflow — verify PR review commands execute successfully without modification and return expected results (FR-010)

## Phase 5: User Story 3 — Real Tool Integration in Node Functions (P1)

### Node Tests (TDD Red)

- [ ] T054 [US3] Write tests for `initiate_node()` in `tests/unit/orchestration/nodes/test_initiate_node.py` — validate issue key, set initial state (FR-003)
- [ ] T055 [US3] Write tests for the pre-flight node behavior in `tests/unit/orchestration/nodes/` — consume pre-flight results, fail-fast on failure (FR-003)
- [ ] T056 [US3] Write tests for `planning_node()` in `tests/unit/orchestration/nodes/test_planning_node.py` — calls `tools.jira.fetch_issue_context()`, records plan in state (FR-003)
- [ ] T057 [US3] Write tests for `planning_gate_node()` in `tests/unit/orchestration/nodes/test_planning_gate_node.py` — `interrupt()` pause, post comment on resume via `tools.jira.add_comment()`
  (FR-003, FR-004)
- [ ] T058 [US3] Write tests for `checklist_creation_node()` in `tests/unit/orchestration/nodes/test_checklist_creation_node.py` (FR-003)
- [ ] T059 [US3] Write tests for `implementation_node()` in `tests/unit/orchestration/nodes/test_implementation_node.py` (FR-003)
- [ ] T060 [US3] Write tests for `implementation_gate_node()` in `tests/unit/orchestration/nodes/test_implementation_gate_node.py` — `interrupt()` pause, resume with structured payload (FR-004)
- [ ] T061 [US3] Write tests for `implementation_review_node()` in `tests/unit/orchestration/nodes/test_implementation_review_node.py` (FR-003)
- [ ] T062 [US3] Write tests for `verification_node()` in `tests/unit/orchestration/nodes/test_verification_node.py` — retry logic routing back to implementation up to MAX_RETRIES=3 (FR-008)
- [ ] T063 [US3] Write tests for `commit_node()` in `tests/unit/orchestration/nodes/test_commit_node.py` — calls `tools.git.save_work()` with parity, hard-stop on failure (FR-003)
- [ ] T064 [US3] Write tests for `pull_request_node()` in `tests/unit/orchestration/nodes/test_pull_request_node.py` — calls `tools.azure_devops.create_pull_request()` (FR-003)
- [ ] T065 [US3] Write tests for `completion_node()` in `tests/unit/orchestration/nodes/test_completion_node.py` — calls `tools.jira.add_comment()` for final comment (FR-003)
- [ ] T066 [US3] Write tests for structured audit trail event emission from each node (FR-007)
- [ ] T115 [US3] Write happy-path success test for full node execution pipeline — each node function called in sequence with mock tool responses, all return valid state updates (FR-003)

### Node Implementation (TDD Green)

- [ ] T067 [US3] Implement `initiate_node()` in `agentic_devtools/orchestration/nodes.py` — enforce issue-key requirement, initialize state, emit event (FR-007)
- [ ] T068 [US3] Implement `setup_node()` in `nodes.py` — consume pre-flight results, fail-fast guard, emit event (FR-007)
- [ ] T069 [US3] Implement `planning_node()` in `nodes.py` — call `tools.jira.fetch_issue_context()`, store plan in state, emit event (FR-003, FR-007)
- [ ] T070 [US3] Implement `planning_gate_node()` in `nodes.py` — `interrupt()` for approval, on resume call `tools.jira.add_comment(state["plan"])`, emit event (FR-003, FR-004, FR-007)
- [ ] T071 [US3] Implement `checklist_creation_node()` in `nodes.py` — create checklist from plan, emit event (FR-007)
- [ ] T072 [US3] Implement `implementation_node()` in `nodes.py` — prepare implementation assignment state, emit event (FR-007)
- [ ] T073 [US3] Implement `implementation_gate_node()` in `nodes.py` — `interrupt()` for handoff, resume with structured `ImplementationResumeData`, emit event (FR-004, FR-007)
- [ ] T074 [US3] Implement `implementation_review_node()` in `nodes.py` — process resumed implementation output, emit event (FR-007)
- [ ] T075 [US3] Implement `verification_node()` in `nodes.py` — run verification, track retries, route back on failure up to MAX_RETRIES=3 (FR-008, FR-007)
- [ ] T076 [US3] Implement `commit_node()` in `nodes.py` — call `tools.git.save_work()` adapter, hard-stop on failure result, emit event (FR-003, FR-007)
- [ ] T077 [US3] Implement `pull_request_node()` in `nodes.py` — call `tools.azure_devops.create_pull_request()`, emit event (FR-003, FR-007)
- [ ] T078 [US3] Implement `completion_node()` in `nodes.py` — call `tools.jira.add_comment()` for final comment, emit event (FR-003, FR-007)

### Graph Builder Integration

- [ ] T079 [US3] Write tests for real-node graph wiring in `tests/unit/orchestration/graph_builder/` (FR-003)
- [ ] T080 [US3] Write tests for `implementation_gate_node` reachability in real-node graph topology (FR-004)
- [ ] T081 [US3] Write tests for verification failure after MAX_RETRIES routing to failure state (not commit) (FR-008)
- [ ] T082 [US3] Update `agentic_devtools/orchestration/graph_builder.py` — add `node_set` parameter, wire real nodes when `node_set="real"`
- [ ] T083 [US3] Add `implementation_gate_node` to real-node graph topology between `implementation_node` and `implementation_review_node`
- [ ] T084 [US3] Add explicit error routing — verification failures after MAX_RETRIES route to failure end-state, not commit (FR-008)
- [ ] T085 [US3] Ensure stub graph (`node_set="stub"`) does NOT include `implementation_gate_node` — existing tests unaffected (FR-002)

### Dry-Run Support (FR-006)

- [ ] T086 [US3] Write tests for dry-run behavior — each node skips mutations and emits `dry_run_skipped` event when `agent_context.dry_run=True` (FR-006)
- [ ] T087 [US3] Implement dry-run guard in each node function — check `state.get("agent_context", {}).get("dry_run")`, skip tool calls, emit event (FR-006)

## Phase 6: User Story 4 — Durable Checkpoint Persistence (P2)

- [ ] T088 [US4] Write tests for `SqliteSaver` configured at worktree-scoped path in `tests/unit/orchestration/runner/test_run_langchain_workflow.py` (FR-005)
- [ ] T089 [US4] Write tests for process restart resume from planning gate checkpoint (FR-004, FR-005)
- [ ] T090 [US4] Write tests for process restart resume from implementation gate checkpoint with `--resume-data` (FR-005, FR-013)
- [ ] T091 [US4] Write tests for `--resume` with no interrupted workflow — exit code 1 with descriptive message (FR-012)
- [ ] T092 [US4] Verify checkpoint persistence integration in runner — `orchestration.db` created in correct worktree path (FR-005)

## Phase 7: User Story 5 — Side-by-Side Comparison Testing (P3)

- [ ] T093 [US5] Write integration test comparing legacy workflow and `--engine langchain` workflow artifacts for same issue (FR-001, FR-002)
- [ ] T094 [US5] Document side-by-side comparison procedure in `specs/1430-langchain-based-work-issue/quickstart.md`
- [ ] T095 [US5] Write NFR-001 timing verification test — orchestration overhead within 2x of legacy (excluding API latency) (FR-001)

## Phase 8: Polish & Cross-Cutting

- [ ] T096 Update argparse help strings for `--engine`, `--use-langchain`, `--resume`, `--resume-data` in `agentic_devtools/cli/workflows/commands.py`
- [ ] T097 Update `.github/copilot-instructions.md` — add `--engine langchain`, `--use-langchain`, `--resume`, `--resume-data` flags to command mapping and workflow docs
- [ ] T098 Update `README.md` — document `--engine langchain` invocation, `--resume` usage, and deprecated `--use-langchain` alias
- [ ] T099 Update `docs/workflow-prompts.md` — align workflow prompt guidance with new flags and engine selection
- [ ] T100 Update `CHANGELOG.md` — add feature entry for LangChain work-on-issue workflow
- [ ] T101 Run full test suite (`agdt-test`) and verify 100% coverage for all new modules (NFR-004, FR-001)
- [ ] T102 Run `bash scripts/run-pr-checks.sh` — fix any lint, format, or structure validation failures
- [ ] T103 Verify `pilot_workflow.py` stub file remains unmodified throughout implementation (FR-010)

## Dependency Map

| Task | Depends On |
|---|---|
| T004–T005 | T001 |
| T006–T007 | T004–T005 |
| T008–T009 | T001 |
| T010–T011 | T008–T009 |
| T012 | T001 |
| T013 | T012 |
| T014 | T001 |
| T015 | T014 |
| T016–T023 | T010, T013 |
| T024–T029 | T016–T023 |
| T030–T039, T104 | T024–T029, T015 |
| T105–T112 | T024–T029, T015 |
| T113–T114 | T024–T029 |
| T040–T050 | T030–T039, T104, T006, T013 |
| T051–T053 | T024–T029 |
| T054–T066, T115 | T010, T015 |
| T067–T078 | T054–T066 |
| T079–T085 | T067–T078 |
| T086–T087 | T067–T078 |
| T088–T092 | T040–T050 |
| T093–T095 | T079–T085, T088–T092 |
| T096–T100 | T040–T050, T079–T085 |
| T101–T103 | All implementation tasks |

---
*Generated by Copilot SDK (claude-opus-4.6)*
