# Tasks: LangChain-Based PR Review Workflow (Parallel Path)

**Issue**: [#1428](https://github.com/ayaiayorg/agentic-devtools/issues/1428)  
**Artifacts Branch**: `speckit/1428/phase-4-tasks`  
**Planned Implementation Branch**: `feature/1428/implement-langchain-based-pull`

---

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | Phase 2 | Optional extra scaffolding and CI dependency wiring |
| Phase 2: Foundational | Phase 1 | Engine resolution and routing foundation |
| Phase 3: US-001 | Phase 1 | Explicit LangChain selection and default-path preservation |
| Phase 4: US-002 | Phase 2, Phase 4 | Preflight validation and review-state compatibility |
| Phase 5: US-001/US-002 | Phase 3, Phase 4 | LangGraph review graph and routing integration |
| Phase 6: US-003 | Phase 6 | Side-by-side artifact comparison outcomes |
| Phase 7: US-004 | Phase 5 | Failure diagnostics, logging, and isolation behavior |
| Phase 8: Polish | Phase 6 | Cross-cutting verification, docs, and final CI checks |

---

## Phase 1: Setup — Project Scaffolding & Dependencies

- [ ] T001 Add `[langchain]` optional extra to `pyproject.toml` with
  `langchain-core>=0.3,<1.0`, `langgraph>=0.4,<1.0`, and
  `langgraph-checkpoint-sqlite>=3.0.1` (FR-008)
- [ ] T002 Create `agentic_devtools/orchestration/review/` subpackage with `__init__.py` (NFR-005)
- [ ] T003 [P] Create `agentic_devtools/cli/workflows/engine_resolution.py` module stub with docstring
- [ ] T004 [P] Update `.github/workflows/test.yml` to install `.[dev,langchain]` in
  coverage-gated jobs (`test-smart`, `test-full`) and in the informational lint
  job (`lint`, which runs with `continue-on-error: true`), while adding/keeping a
  no-extra smoke/regression job (`.[dev]` only) that exercises default routing
  imports (FR-011)
- [ ] T054 Add RED regression scenario in
  `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py`
  confirming default install (no `[langchain]` extra) still routes to existing
  path when no engine flag/state/env is provided (FR-002, NFR-001)
- [ ] T005 Refactor imports in `agentic_devtools/orchestration/__init__.py`,
  `agentic_devtools/orchestration/graph_builder.py`,
  `agentic_devtools/orchestration/pilot_workflow.py`, and
  `agentic_devtools/orchestration/checkpointing.py` to lazy/guarded boundaries;
  only after T054 is in place, move `langgraph` and
  `langgraph-checkpoint-sqlite` from core dependencies into the `[langchain]`
  extra in `pyproject.toml`

---

## Phase 2: Foundational — Engine Resolution & Routing

- [ ] T006 Implement `resolve_review_engine(cli_flag, state_key, env_var) → str`
  in `agentic_devtools/cli/workflows/engine_resolution.py` with priority:
  CLI > state > env > default after T012/T013 are complete
  (FR-001, FR-003, NFR-006)
- [ ] T007 Add `--engine` argparse argument to
  `initiate_pull_request_review_workflow` in
  `agentic_devtools/cli/workflows/commands.py`; add `engine` to the function
  signature and `_effective_argv(...)` handling for programmatic callers; treat
  `--engine` as the highest-priority selector and persist `review.engine` in
  state when provided (consistent with spec/plan behavior), while preserving
  FR-009 isolation guarantees for failed runs (FR-001)
- [ ] T008 Add `--use-langchain` deprecated alias flag that maps to `--engine langchain` in `agentic_devtools/cli/workflows/commands.py` (FR-001)
- [ ] T009 Implement routing dispatch in
  `agentic_devtools/cli/workflows/commands.py` for
  `initiate_pull_request_review_workflow`: call `resolve_review_engine()`, then
  branch to LangChain path or existing path (FR-002, FR-003)
- [ ] T010 Implement environment variable `AGDT_REVIEW_ENGINE` reading in
  `agentic_devtools/cli/workflows/engine_resolution.py` as fallback when no CLI
  flag or state key (FR-001)
- [ ] T011 Add `[langchain]`-prefixed log output in
  `agentic_devtools/cli/workflows/commands.py` when LangChain engine is
  selected in routing dispatch (FR-010)

---

## Phase 3: User Story US-001 [P1] — Select LangChain Review Path Explicitly

**Goal**: Provide explicit, deterministic LangChain routing while preserving the
existing default path unless users opt in.

**Independent Test**: Run
`tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py`
and `tests/unit/cli/workflows/engine_resolution/test_resolve_review_engine.py`
to confirm CLI/state/env priority and unchanged default routing.

### Tests (RED)

- [ ] T012 [US1] Create
  `tests/unit/cli/workflows/engine_resolution/__init__.py` and
  `tests/unit/cli/workflows/engine_resolution/test_resolve_review_engine.py`
  with RED happy-path scenarios for CLI flag priority over state and env
  (FR-001)
- [ ] T013 [US1] Extend
  `tests/unit/cli/workflows/engine_resolution/test_resolve_review_engine.py`
  with RED scenarios for state-only, env-only, default fallback, and conflicting
  signals, plus empty-string/whitespace normalization and case-insensitive
  engine matching edge cases (FR-001, NFR-006)
- [ ] T014 [US1] Extend
  `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py`
  RED routing scenarios: `--engine langchain` and deprecated `--use-langchain`
  route to LangChain, no flag routes to default, and routed LangChain output is
  `[langchain]`-prefixed (FR-001, FR-002, FR-003, FR-010)
- [ ] T015 [US1] Add RED scenario in
  `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py`
  for `AGDT_REVIEW_ENGINE` override when no CLI flag and no state key (FR-001)

### Implementation (GREEN)

- [ ] T016 [US1] Implement edge-case handling in
  `agentic_devtools/cli/workflows/engine_resolution.py` for empty strings,
  whitespace, and case-insensitive matching (FR-001)
- [ ] T017 [US1] Add/keep regression assertions in
  `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py`
  proving default-path behavior is unchanged when no LangChain opt-in
  (FR-002, NFR-001)

---

## Phase 4: User Story US-002 [P1] — Preserve Workflow Compatibility

**Goal**: Ensure LangChain-mode preflight and review-state handling remain fully
compatible with existing review lifecycle behavior and configuration patterns.

**Independent Test**: Run
`tests/unit/orchestration/review/preflight/test_validate_langchain_dependencies.py`,
`tests/unit/orchestration/review/state_bridge/test_apply_graph_updates_to_review_state.py`,
and `tests/unit/cli/azure_devops/review_state/test_reviewsession.py` to validate
dependency/config preflight, state-bridge compatibility, and review-state schema changes.

### Test Scaffolding (non-RED)

- [ ] T018 [P] [US2] Create `tests/unit/orchestration/review/__init__.py`,
  `tests/unit/orchestration/review/preflight/__init__.py`, and
  `tests/unit/orchestration/review/graph_builder/__init__.py`

### Tests (RED)

- [ ] T019 [P] [US2] Create
  `tests/unit/orchestration/review/preflight/test_validate_langchain_dependencies.py`
  with RED happy-path, missing-package, and missing/invalid model configuration
  scenarios producing actionable errors; these RED scenarios also guide T023
  implementation (FR-007, FR-008)
- [ ] T020 [P] [US2] Create `tests/unit/orchestration/review/state_bridge/__init__.py`
  and
  `tests/unit/orchestration/review/state_bridge/test_apply_graph_updates_to_review_state.py`
  to validate LangChain path writes compatible `review-state.json`
  (FR-004, FR-005)
- [ ] T021 [P] [US2] Extend existing
  `tests/unit/cli/azure_devops/review_state/test_reviewsession.py` with RED
  scenarios for optional `engine` field backward compatibility (FR-004)
- [ ] T060 [P] [US2] Create
  `tests/unit/orchestration/review/state_schema/__init__.py` and
  `tests/unit/orchestration/review/state_schema/test_prreviewstate.py`
  with RED scenarios for `PRReviewState` TypedDict field validation and
  backward-compatible deserialization (FR-004)

### Implementation

- [ ] T022 [US2] Implement dependency preflight guard in
  `agentic_devtools/orchestration/review/preflight.py` to attempt imports of
  `langchain_core` and `langgraph`, raising actionable failures when unavailable
  (FR-008)
- [ ] T023 [US2] Implement configuration validation in
  `agentic_devtools/orchestration/review/preflight.py` with explicit fail-fast
  checks for missing/invalid model config, while preserving existing
  `review-models-override.json` precedence and override-only behavior
  (FR-007, FR-008)
- [ ] T024 [US2] Call preflight validation from routing dispatch in
  `agentic_devtools/cli/workflows/commands.py` before LangChain execution;
  exit(1) with actionable message on failure (FR-008)
- [ ] T025 [US2] Add optional `engine: str | None` field to `ReviewSession`
  dataclass in `agentic_devtools/cli/azure_devops/review_state.py` with
  backward-compatible serialization/deserialization (FR-004)
- [ ] T026 [US2] Create `agentic_devtools/orchestration/review/state_bridge.py`
  adapter to load existing `ReviewState`, apply graph output updates, and save
  back with `engine` on session entries (FR-004, FR-005)
- [ ] T027 [P] [US2] Create
  `agentic_devtools/orchestration/review/state_schema.py` with `PRReviewState`
  TypedDict for LangGraph state (FR-004)
- [ ] T028 [US2] Validate lifecycle-command compatibility with explicit tests in
  `tests/unit/cli/azure_devops/file_review_commands/test_approve_file.py`,
  `tests/unit/cli/azure_devops/file_review_commands/test_request_changes.py`,
  `tests/unit/cli/azure_devops/file_review_commands/test_request_changes_with_suggestion.py`,
  and `tests/unit/cli/azure_devops/file_review_commands/test_submit_reviews.py`
  while `engine` is present in review state (FR-006)

---

## Phase 5: User Story US-001/US-002 — LangGraph Review Graph Implementation

**Goal**: Implement and integrate the LangGraph review pipeline so explicit
LangChain routing executes a schema-compatible review flow.

**Independent Test**: Run node, graph builder, and runner tests under
`tests/unit/orchestration/review/` plus routing tests in
`tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py`
to confirm graph execution is invoked through engine routing.

### Tests (RED)

- [ ] T029 [P] [US2] Create `tests/unit/orchestration/review/nodes/__init__.py`
  and `tests/unit/orchestration/review/nodes/test_scaffold_node.py` for RED
  scaffold-node state-write behavior
- [ ] T030 [P] [US2] Create
  `tests/unit/orchestration/review/nodes/test_review_file_node.py` for RED file
  review node behavior
- [ ] T031 [P] [US2] Create
  `tests/unit/orchestration/review/nodes/test_summarize_node.py` for RED
  summarize-node behavior
- [ ] T032 [P] [US2] Create
  `tests/unit/orchestration/review/nodes/test_complete_node.py` for RED
  completion-node session-marking behavior
- [ ] T061 [P] [US2] Create
  `tests/unit/orchestration/review/nodes/test_fetch_pr_details_node.py` with RED
  scenarios for the fetch-PR-details node: verifies it retrieves PR details and
  stores them in graph state
- [ ] T033 [P] [US2] Create RED review-graph tests under
  `tests/unit/orchestration/review/` covering graph wiring, entry-point, and
  invalid-schema rejection scenarios; `__init__.py` for this directory is
  created in T018 (FR-003)
- [ ] T034 [P] [US2] Create `tests/unit/orchestration/review/runner/__init__.py`
  and `tests/unit/orchestration/review/runner/test_run_langchain_review.py` for
  RED runner orchestration behavior

### Implementation

- [ ] T035 [US2] Implement node functions in
  `agentic_devtools/orchestration/review/nodes.py`: `fetch_pr_details_node`,
  `scaffold_node`, `review_file_node`, `summarize_node`, `complete_node`
  (FR-005, FR-006)
- [ ] T036 [US1] Implement
  `build_pr_review_graph(checkpointer=None) → CompiledStateGraph` in
  `agentic_devtools/orchestration/review/graph_builder.py` (FR-003)
- [ ] T037 [US1] Implement
  `run_langchain_review(pr_id, config, state_dir)` in
  `agentic_devtools/orchestration/review/runner.py` to orchestrate graph
  invocation (FR-003)
- [ ] T038 [US2] Wire scaffold/review nodes to existing
  `agentic_devtools/cli/azure_devops/review_scaffold.py` and
  `agentic_devtools/cli/azure_devops/file_review_commands.py` for artifact
  generation (FR-005, FR-006)
- [ ] T039 [US2] Export public API from
  `agentic_devtools/orchestration/review/__init__.py` for dependency preflight,
  review runner, and graph builder symbols
- [ ] T040 [US1] Integrate `run_langchain_review` into routing dispatch in
  `agentic_devtools/cli/workflows/commands.py` so `engine=langchain` executes
  the graph (FR-003)

---

## Phase 6: User Story US-003 [P2] — Compare Outcomes Between Both Paths

**Goal**: Enable objective side-by-side comparison by keeping both engine outputs
structurally equivalent and distinguishable.

**Independent Test**: Run comparison tests in
`tests/unit/orchestration/review/runner/test_run_langchain_review.py` and
confirm both engines produce equivalent required artifact structures.

### Tests (RED)

- [ ] T041 [P] [US3] Extend
  `tests/unit/orchestration/review/runner/test_run_langchain_review.py`
  (created by T034) with RED scenarios for side-by-side artifact schema
  comparison with mock LLM (FR-004, FR-005)

### Implementation

- [ ] T042 [US3] Ensure both engines write to standard
  `pull-request-review/<commit_hash_short>/` and produce structurally equivalent
  `review-state.json` via updates in
  `agentic_devtools/orchestration/review/runner.py` and
  `agentic_devtools/orchestration/review/state_bridge.py` (FR-005)
- [ ] T043 [US3] Add `engine` field to session entries so post-run inspection can
  distinguish which engine produced each session in
  `agentic_devtools/orchestration/review/state_bridge.py` and
  `agentic_devtools/cli/azure_devops/review_state.py` (FR-004)

---

## Phase 7: User Story US-004 [P3] — Diagnose Failures Quickly

**Goal**: Provide actionable diagnostics and safe failure behavior for LangChain
runs without impacting default-mode reliability.

**Independent Test**: Run preflight/logging/failure tests in
`tests/unit/orchestration/review/preflight/test_validate_langchain_dependencies.py`,
`tests/unit/orchestration/review/logging_config/test_create_langchain_logger.py`,
and `tests/unit/orchestration/review/runner/test_run_langchain_review.py`.

### Tests (RED)

- [ ] T044 [P] [US4] Extend
  `tests/unit/orchestration/review/runner/test_run_langchain_review.py`
  (created by T034, extended by T041) with RED scenarios validating failed
  LangChain runs record `"failed"` session status, do not mutate
  `review.engine`, preserve partial debug artifacts, and do not corrupt existing
  `review-state.json` data on failure (FR-009, NFR-002)
- [ ] T045 [P] [US4] Extend
  `tests/unit/orchestration/review/preflight/test_validate_langchain_dependencies.py`
  (created by T019) with RED scenarios for missing model configuration,
  including override-only `review-models-override.json` compatibility and
  base-file fallback (FR-007, FR-008)
- [ ] T046 [P] [US4] Create
  `tests/unit/orchestration/review/logging_config/__init__.py` and
  `tests/unit/orchestration/review/logging_config/test_create_langchain_logger.py`
  to validate `[langchain]` prefixes and no credential leakage
  (FR-010, NFR-004)

### Implementation

- [ ] T047 [US4] Implement `[langchain]`-prefixed logging setup in
  `agentic_devtools/orchestration/review/logging_config.py` via
  `create_langchain_logger()` with credential filtering (FR-010, NFR-004)
- [ ] T048 [US4] Wrap graph invocation in
  `agentic_devtools/orchestration/review/runner.py` with try/except; record
  `"failed"` session status on exception; do not mutate `review.engine`
  (FR-009)
- [ ] T049 [US4] Emit progress markers from
  `agentic_devtools/orchestration/review/runner.py`:
  `[langchain] scaffolding...`, `[langchain] reviewing file N/M...`,
  `[langchain] summarizing...` (FR-010)
- [ ] T050 [US4] Ensure partial artifact writes persist on failure for debugging
  without corrupting existing review-state data by updating
  `agentic_devtools/orchestration/review/runner.py` and
  `agentic_devtools/orchestration/review/state_bridge.py` (FR-009, NFR-002)
- [ ] T051 [US4] Ensure preflight errors include
  `agentic_devtools/orchestration/review/preflight.py` and
  `pip install agentic-devtools[langchain]` guidance when packages are missing
  (FR-008)

---

## Phase 8: Polish & Cross-Cutting — Integration Tests & Documentation

- [ ] T052 Extend
  `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py`
  with full engine routing matrix including deprecated `--use-langchain` alias
  (FR-001, FR-002, FR-011)
- [ ] T053 Add `pytest.importorskip` guards scoped to individual test **functions**
  that require real LangChain execution (not at module-level in files that also
  cover default-path scenarios) in
  `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py`,
  `tests/unit/orchestration/review/nodes/test_scaffold_node.py`,
  `tests/unit/orchestration/review/nodes/test_review_file_node.py`,
  `tests/unit/orchestration/review/nodes/test_summarize_node.py`,
  `tests/unit/orchestration/review/nodes/test_complete_node.py`,
  `tests/unit/orchestration/review/nodes/test_fetch_pr_details_node.py`,
  the graph-builder 1:1:1 test file (see T033),
  `tests/unit/orchestration/review/runner/test_run_langchain_review.py`,
  `tests/unit/orchestration/review/preflight/test_validate_langchain_dependencies.py`,
  and
  `tests/unit/orchestration/review/logging_config/test_create_langchain_logger.py`;
  note: missing-package and missing-config scenarios in T019/T045 must use
  `unittest.mock.patch` to simulate absent imports rather than
  `pytest.importorskip` guards — those tests must always run whether or not
  the `[langchain]` extra is installed (FR-011)
- [ ] T055 [P] Update `.github/copilot-instructions.md` to document
  `--engine langchain`, `review.engine`, and `AGDT_REVIEW_ENGINE`
- [ ] T056 [P] Update `README.md` usage docs for
  `agdt-initiate-pull-request-review-workflow --engine langchain` and add
  `CHANGELOG.md` entry for the LangChain review path feature
- [ ] T059 [US4] Add instrumented startup-overhead assertion in
  `tests/unit/orchestration/review/runner/test_run_langchain_review.py` using
  mocked timers/benchmark metadata to **enforce** the ≤5 second LangChain-vs-default
  delta as a deterministic, non-flaky threshold — use a mocked monotonic timer so
  the assertion is reliable without relying on real wall-clock timing
  (NFR-003)
- [ ] T057 Execute `python scripts/validate_test_structure.py` to check 1:1:1 compliance for all new test files (FR-011)
- [ ] T058 Execute `bash scripts/run-pr-checks.sh` to run the full CI suite with all changes (FR-011)

---

## Task Dependencies

| Task | Depends On |
|------|-----------|
| T003 | T002 |
| T004 | T001 |
| T054 | T003 |
| T005 | T001, T054 |
| T006 | T003, T012, T013 |
| T007 | T006 |
| T008 | T007, T014 |
| T009 | T006, T007, T014 |
| T010 | T006, T015 |
| T011 | T009, T014 |
| T012-T015 | T003 |
| T016-T017 | T012-T015 |
| T019 | T018 |
| T020 | T018 |
| T021 | T018 |
| T060 | T018 |
| T022 | T001, T002 |
| T023 | T001, T002, T019 |
| T024 | T001, T002, T023 |
| T025 | T022, T023, T021 |
| T026 | T022, T023, T020 |
| T028 | T022, T023 |
| T027 | T022, T023, T060 |
| T029-T034, T061 | T027 |
| T035-T040 | T029-T034, T061, T026 |
| T041 | T040 |
| T042, T043 | T040, T041 |
| T044 | T040, T041 |
| T045-T051 | T040 |
| T052 | T040 |
| T053 | T040, T052 |
| T055-T056 | T040 |
| T059 | All previous tasks |
| T057 | T059 |
| T058 | T057 |

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 (Setup) starts immediately; T004 depends on T001, T054 must complete before T005.
- Phase 2 (Foundational) starts after Phase 1 setup; T006 intentionally waits
  for RED tests T012/T013 to satisfy TDD; T009 and T010 wait for RED tests T014
  and T015 respectively to satisfy TDD order.
- Phase 3 starts with RED tests T012-T015 before T006, then continues after
  Phase 2 routing is complete.
- Story phases 4-7 depend on Phase 2 completion; T023 waits for T019 RED tests
  covering missing/invalid model config before implementing config validation.
- Phase 8 (Polish) depends on completion of all selected story phases; T053 runs
  after T052 (sequential, not parallel, as both modify the same test file).

### Story Order

- US-001 (P1) and US-002 (P1) are the MVP-critical paths and should complete first.
- US-003 (P2) depends on routing/graph readiness from US-001/US-002.
- US-004 (P3) hardening follows once core execution exists.

### Within Each Story

- RED tests are created before corresponding implementation tasks.
- State/schema compatibility tests run before lifecycle integration changes.
- Runner/graph integration happens after node and state-bridge foundations.

---

## Parallel Execution Example

```text
After T027 completes:
- Run T029, T030, T031, T032, T033, T034, and T061 in parallel (distinct test files).
After T040 completes:
- Run T041 (US3) in parallel with T045 and T046 (US4 RED tests).
- Run T042 and T043 after T041 (implementations follow their RED test).
- Run T044 after T041 (both update `test_run_langchain_review.py`).
- Run T052 then T053 sequentially (both modify the same workflow command test file).
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Deliver US-001 routing + US-002 compatibility.
3. Validate with independent tests before adding comparison/hardening work.

### Incremental Delivery

1. Add LangGraph execution (Phase 5) once routing/preflight is stable.
2. Add side-by-side comparison (US-003) as a separate increment.
3. Add diagnostics/hardening (US-004), then finish polish/docs/checks.

## FR Coverage Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T006, T007, T008, T010, T012, T013, T014, T015, T016, T052 |
| FR-002 | T009, T014, T017, T052, T054 |
| FR-003 | T006, T009, T014, T036, T037, T040 |
| FR-004 | T020, T021, T025, T026, T027, T041, T043, T060 |
| FR-005 | T020, T026, T035, T038, T041, T042 |
| FR-006 | T028, T035, T038 |
| FR-007 | T023, T045 |
| FR-008 | T001, T019, T022, T023, T024, T045, T051 |
| FR-009 | T044, T048, T050 |
| FR-010 | T011, T014, T046, T047, T049 |
| FR-011 | T004, T052, T053, T057, T058 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
