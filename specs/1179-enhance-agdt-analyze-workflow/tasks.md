# Tasks: Enhance agdt.analyze-workflow (#1179)

## User Story Index

| Label | Story | Priority |
|-------|-------|----------|
| US1 | Parameterized invocation (`--issue-key`, `--pr-id`, `--static-only`) | P1 |
| US2 | Multi-identity log scanning across all identity directories | P1 |
| US3 | External worktree context collection (read-only) | P2 |
| US4 | `external_context` field in JSON output schema | P2 |
| US5 | Backward compatibility — existing outputs remain valid | P3 |

---

## Phase 1: Setup — Package & Test Scaffolding

- [ ] T001 Create package directory `agentic_devtools/cli/analysis/` and empty `__init__.py`
- [ ] T002 Create test directory `tests/unit/cli/analysis/` with `__init__.py`
- [ ] T003 Create test subdirectory `tests/unit/cli/analysis/context_resolver/` with `__init__.py`
- [ ] T004 Create test subdirectory `tests/unit/cli/analysis/identity_scanner/` with `__init__.py`
- [ ] T005 Create test subdirectory `tests/unit/cli/analysis/external_context/` with `__init__.py`
- [ ] T006 Run `python scripts/validate_test_structure.py` to confirm scaffolding is valid

---

## Phase 2: Foundational — Shared Dataclasses & Package Exports

- [ ] T007 Define `AnalysisContext` and `WorktreeStateDir` frozen dataclasses in `agentic_devtools/cli/analysis/context_resolver.py` (stub functions only)
- [ ] T008 [P] Define `IdentityDir`, `LogEvidence` frozen dataclasses in `agentic_devtools/cli/analysis/identity_scanner.py` (stub functions only)
- [ ] T009 [P] Define `ExternalContext`, `ExternalLogEvidence` dataclasses in `agentic_devtools/cli/analysis/external_context.py` (stub functions only)
- [ ] T010 Wire up `agentic_devtools/cli/analysis/__init__.py` with all public exports from T007–T009
- [ ] T011 Verify import: `python -c "from agentic_devtools.cli.analysis import AnalysisContext, LogEvidence, ExternalContext; print('OK')"`

---

## Phase 3: US1 — Parameterized Invocation (Context Resolver)

### Tests (RED)

- [ ] T012 Write failing tests in `tests/unit/cli/analysis/context_resolver/test_resolve_analysis_context.py`:
      happy path with `issue_key`, happy path with `pr_id`, fallback to bootstrap (neither param), mutual exclusion
      error (both params), empty `issue_key` string, non-integer `pr_id` type handling
- [ ] T013 [P] Write failing tests in `tests/unit/cli/analysis/context_resolver/test_list_worktree_state_dirs.py`:
      multiple identities found, no matching directories, `_unscoped` directory skipped, permission errors handled
      gracefully

### Implementation (GREEN)

- [ ] T014 Implement `resolve_analysis_context(issue_key, pr_id) -> AnalysisContext` in
      `agentic_devtools/cli/analysis/context_resolver.py` — mutual exclusion check, resolution precedence matching
      `state.py`'s `_sync_bootstrap_for_context_key()`, returns immutable `AnalysisContext`
- [ ] T015 Implement `list_worktree_state_dirs(worktree_key) -> list[WorktreeStateDir]` in
      `agentic_devtools/cli/analysis/context_resolver.py` — scan `.agdt/workflows/*/` excluding `_unscoped`, detect
      `background-tasks/logs/` presence
- [ ] T016 Run `agdt-test-pattern tests/unit/cli/analysis/context_resolver/ -v` to confirm all tests pass (GREEN)

---

## Phase 4: US2 — Multi-Identity Log Scanning

### Tests (RED)

- [ ] T017 Write failing tests in `tests/unit/cli/analysis/identity_scanner/test_scan_identity_logs.py`: logs found
      across multiple identities, workflow name filter applied, no logs found, empty identity dirs,
      identity dir name attribution (verify `LogEvidence.identity` is set to the directory name, not
      the `.identity-owner` email — email is only used by `list_identity_directories`)
- [ ] T018 [P] Write failing tests in `tests/unit/cli/analysis/identity_scanner/test_list_identity_directories.py`:
      multiple identities listed, empty workflows dir, missing `.identity-owner` returns `None`,
      `_unscoped` directory excluded from results
- [ ] T019 [P] Write failing tests in `tests/unit/cli/analysis/identity_scanner/test_format_evidence_prefix.py`: standard format `[identity: {name}]`, special characters in identity name

### Implementation (GREEN)

- [ ] T020 Implement `scan_identity_logs(git_root, worktree_key, workflow_name) -> list[LogEvidence]` in
      `agentic_devtools/cli/analysis/identity_scanner.py` — iterate identity dirs, match worktree_key, optional
      workflow name filter, read-only
- [ ] T021 Implement `list_identity_directories(git_root) -> list[IdentityDir]` in
      `agentic_devtools/cli/analysis/identity_scanner.py` — list dirs under `.agdt/workflows/`
      excluding `_unscoped` (consistent with `scan_identity_logs`), read `.identity-owner` files
      for owner email attribution
- [ ] T022 Implement `format_evidence_prefix(identity) -> str` in `agentic_devtools/cli/analysis/identity_scanner.py`
- [ ] T023 Run `agdt-test-pattern tests/unit/cli/analysis/identity_scanner/ -v` to confirm all tests pass (GREEN)

---

## Phase 5: US3 — External Worktree Context Collection

### Tests (RED)

- [ ] T024 Write failing tests in `tests/unit/cli/analysis/external_context/test_collect_external_context.py`:
      external worktrees found, `static_only=True` returns `None`, no external worktrees returns `None`
      (consistent with `static_only` contract), inaccessible worktree handled gracefully, read-only safety
      (assert no write calls)
- [ ] T025 [P] Write failing tests in `tests/unit/cli/analysis/external_context/test_build_external_context_field.py`: populated `ExternalContext` → dict with correct keys, `None` input → `None` output

### Implementation (GREEN)

- [ ] T026 Implement `collect_external_context(git_root, worktree_key, static_only) -> ExternalContext | None` in
      `agentic_devtools/cli/analysis/external_context.py` — discover worktrees via
      `git worktree list --porcelain`, read-only log collection, excerpt truncation (keep last 500 lines via tail,
      prepend `[…truncated {N} lines…]` header when truncation occurs), ISO-8601 timestamps
- [ ] T027 Implement `build_external_context_field(external_ctx) -> dict | None` in `agentic_devtools/cli/analysis/external_context.py` — serialize `ExternalContext` to JSON-compatible dict
- [ ] T028 Run `agdt-test-pattern tests/unit/cli/analysis/external_context/ -v` to confirm all tests pass (GREEN)

---

## Phase 5b: NFR Validation & Edge Case Testing

### NFR Tests

- [ ] T050 Write tests for NFR-002 (latency): benchmark `scan_identity_logs()` and `list_identity_directories()` complete
      in < 2s for ≤ 20 identity directories — use `time.monotonic()` upper-bound assertion in
      `tests/unit/cli/analysis/identity_scanner/test_scan_identity_logs_performance.py`
- [ ] T051 Write tests for NFR-004 (error clarity): assert every error raised by `resolve_analysis_context()` includes
      the specific parameter or path that caused the failure — cover mutual exclusion (`--issue-key` + `--pr-id`),
      empty `--issue-key`, invalid `--pr-id` type, and missing bootstrap worktree key in
      `tests/unit/cli/analysis/context_resolver/test_resolve_analysis_context_errors.py`
- [ ] T052 Write tests for NFR-005 (determinism): given identical filesystem fixtures, assert two consecutive calls to
      `scan_identity_logs()` produce byte-identical JSON output (stable ordering of identities, log entries, and
      evidence fields) in `tests/unit/cli/analysis/identity_scanner/test_scan_identity_logs_determinism.py`

### Edge Case Tests

- [ ] T053 Write tests asserting exact error messages from the edge-case table (EC1–EC7) in
      `tests/unit/cli/analysis/context_resolver/test_resolve_analysis_context_edge_cases.py`:
      - EC1: mutual exclusion error string matches `"--issue-key and --pr-id are mutually exclusive. Provide one or neither."`
      - EC2: empty `--issue-key` raises usage error
      - EC3: no `.agdt/workflows/` directory proceeds with code-only evidence and notes in findings
      - EC4: no identity directories found proceeds with code-only evidence
      - EC5: inaccessible external worktree path logs warning, continues
      - EC6: `--static-only` with external worktrees sets `external_context: null`
      - EC7: identity directory with no matching logs is skipped silently
- [ ] T054 Run `agdt-test-pattern tests/unit/cli/analysis/context_resolver/test_resolve_analysis_context_edge_cases.py -v`
      to confirm all edge case tests pass
- [ ] T055 Run `agdt-test-pattern tests/unit/cli/analysis/identity_scanner/test_scan_identity_logs_performance.py -v`
      to confirm performance test passes
- [ ] T056 Run `agdt-test-pattern tests/unit/cli/analysis/identity_scanner/test_scan_identity_logs_determinism.py -v`
      to confirm determinism test passes

---

## Phase 6: US4 — Extend SKILL.md JSON Schema

- [ ] T029 Add `external_context` property to root `properties` object in
      `agentic_devtools/_bundled_skills/workflow-analysis/SKILL.md` — use `oneOf` with `$ref ExternalContext` and
      `null`, do NOT add to `required` array
- [ ] T030 Add `ExternalContext` definition to `$defs` in
      `agentic_devtools/_bundled_skills/workflow-analysis/SKILL.md` — `worktrees_scanned`, `log_evidence`,
      `identities_scanned` fields with `additionalProperties: false`
- [ ] T031 Add `ExternalLogEvidence` definition to `$defs` in `agentic_devtools/_bundled_skills/workflow-analysis/SKILL.md` — `worktree_path`, `identity`, `log_file`, `excerpt`, `timestamp` fields
- [ ] T032 [US5] Add annotated example to SKILL.md showing `"external_context": null` (static-only case) and a populated `external_context` example

---

## Phase 7: US1 + US2 + US3 — Update Agent Prompt

- [ ] T033 [US1] Add Phase 0 (§0.1–0.4) to `.github/prompts/agdt.analyze-workflow.prompt.md` — parameter parsing
      for `--issue-key`, `--pr-id`, `--static-only`; mutual exclusion check; context resolution via Python helper;
      identity directory scanning
- [ ] T034 [US2] Enhance Step 6 (log evidence collection) in `.github/prompts/agdt.analyze-workflow.prompt.md` —
      replace single-directory search with `scan_identity_logs()` call, add `[identity: {name}]` attribution prefix
- [ ] T035 [US3] Enhance Step 6 to call `collect_external_context()` when `--static-only` is not set, merge external log evidence into findings
- [ ] T036 [US4] Enhance Phase 3 output section in `.github/prompts/agdt.analyze-workflow.prompt.md` — include `external_context` field in JSON template, document null vs populated cases
- [ ] T037 [US4] Enhance Phase 4 validation in `.github/prompts/agdt.analyze-workflow.prompt.md` — add rule 7 for `external_context` field validation
- [ ] T038 [US1] Add error handling rows to the prompt's error table — mutual exclusion, missing parameter values,
      no identity directories, inaccessible external worktree, `--static-only` with external worktrees present

---

## Phase 8: US1 — Update Agent Definition

- [ ] T039 [US1] Update description in `.github/agents/agdt.analyze-workflow.agent.md` to reflect multi-identity scanning, external worktree context, and parameterized scoping
- [ ] T040 [US1] Update `## User Input` section in `.github/agents/agdt.analyze-workflow.agent.md` to document `--issue-key`, `--pr-id`, and `--static-only` parameters

---

## Phase 9: US5 — Backward Compatibility Verification

- [ ] T041 [US5] Verify existing analysis JSON output (without `external_context`) still validates against updated SKILL.md schema — `external_context` is not in `required`
- [ ] T042 [US5] Verify `create-issues-from-analysis` agent definition does not reference `external_context` — it only processes `findings`, `priority_order`, `cascade_graph`
- [ ] T043 [US5] Verify no changes to `COMMAND_MAP` in `agentic_devtools/cli/runner.py` or existing CLI entry points in `pyproject.toml`

---

## Final Phase: Polish & Cross-Cutting

- [ ] T044 Update `agentic_devtools/cli/analysis/__init__.py` exports to match all implemented public symbols
- [ ] T045 Run `python scripts/validate_test_structure.py` to confirm 1:1:1 compliance
- [ ] T046 Run `ruff check --fix . && ruff format .` to fix lint/format issues
- [ ] T047 Run `agdt-test` + `agdt-task-wait` — full test suite passes with no regressions
- [ ] T048 Run `bash scripts/run-pr-checks.sh` — all PR checks pass (tests, coverage, lint, format, markdownlint, mypy)
- [ ] T049 Verify Python helpers are importable: `python -c "from agentic_devtools.cli.analysis import resolve_analysis_context, scan_identity_logs, collect_external_context; print('OK')"`

---

## Dependency Graph

```text
T001 ─► T007, T008, T009 ─► T010 ─► T011
T002 ─► T003, T004, T005 ─► T006

T011 + T006 ─► T012, T013 (US1 tests)
T012, T013 ─► T014, T015 ─► T016

T011 + T006 ─► T017, T018, T019 (US2 tests)  [parallel with US1 impl]
T017, T018, T019 ─► T020, T021, T022 ─► T023

T011 + T006 ─► T024, T025 (US3 tests)  [parallel with US1/US2 impl]
T024, T025 ─► T026, T027 ─► T028

T016 + T023 + T028 ─► T050, T051, T052, T053 (NFR + edge case tests)  [parallel]
T053 ─► T054; T050 ─► T055; T052 ─► T056

T028 ─► T029, T030, T031 ─► T032 (US4 schema)
T032 ─► T033, T034, T035, T036, T037, T038 (prompt updates)
T038 ─► T039, T040 (agent definition)

T040 ─► T041, T042, T043 (backward compat)
T043 ─► T044 ─► T045 ─► T046 ─► T047 ─► T048 ─► T049
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
