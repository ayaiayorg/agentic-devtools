# Tasks: SpecKit FR Validation Gate (#1199)

> Cross-references functional requirements (FR-###) in `spec.md` with task content in `tasks.md`,
> blocking PR creation when any FR lacks corresponding task coverage. Includes auto-retry,
> standalone CLI command, and analysis report enrichment.

---

## Phase 1: Setup

- [ ] T001 Create module file `agentic_devtools/cli/speckit/validate_frs.py` with module docstring and stdlib imports (`re`, `json`, `argparse`, `pathlib`, `dataclasses`, `os`, `sys`)
- [ ] T002 Create test directory `tests/unit/cli/speckit/validate_frs/` with `__init__.py` (parent `__init__.py` files in `tests/unit/cli/speckit/` already exist)

---

## Phase 2: Foundational

- [ ] T003 [P] Write tests for `ValidationResult` dataclass — field access, `passed` property (True when uncovered is empty, False otherwise), and `to_json()` output schema — in
  `tests/unit/cli/speckit/validate_frs/test_validationresult.py`
- [ ] T004 [P] Write tests for `extract_frs()` — basic extraction, case-insensitive dedup with first-occurrence canonical form (FR-001 vs fr-001), varying digit counts (FR-1, FR-01, FR-001 as
  distinct), no FRs found returns empty list, duplicate same-case identifiers counted once — in `tests/unit/cli/speckit/validate_frs/test_extract_frs.py`
- [ ] T005 [P] Write tests for `check_coverage()` — all covered, none covered, partial coverage, case-insensitive match (fr-001 matches FR-001), word-boundary enforcement (FR-1 must NOT match FR-10 or
  FR-100), FR inside fenced code blocks still counts as coverage — in `tests/unit/cli/speckit/validate_frs/test_check_coverage.py`
- [ ] T006 [P] Write tests for `sort_fr_ids()` — numeric suffix ascending order, tie-breaking by string length (shorter first), then lexicographic order, mixed padding (FR-1 before FR-001) — in
  `tests/unit/cli/speckit/validate_frs/test_sort_fr_ids.py`
- [ ] T007 Implement `ValidationResult` dataclass with fields `covered: list[str]`, `uncovered: list[str]`, `total: int`, `warning: str | None`; `passed` as `@property` returning
  `len(self.uncovered) == 0`; `to_json()` returning `{"covered": [...], "uncovered": [...], "total": N}` — in `agentic_devtools/cli/speckit/validate_frs.py`
- [ ] T008 [P] Implement `extract_frs(spec_content: str) -> list[str]` — regex `FR-\d+` with `re.IGNORECASE`, case-insensitive dedup preserving first occurrence as canonical form, returns deduplicated
  list in document order — in `agentic_devtools/cli/speckit/validate_frs.py`
- [ ] T009 [P] Implement `check_coverage(fr_ids: list[str], tasks_content: str) -> dict[str, bool]` — per-FR word-boundary regex `\b{re.escape(fr_id)}\b` with `re.IGNORECASE`,
  returns `{fr_id: True/False}` mapping — in `agentic_devtools/cli/speckit/validate_frs.py`
- [ ] T010 [P] Implement `sort_fr_ids(fr_ids: list[str]) -> list[str]` — sort key: numeric suffix value (int) ascending, then string length ascending, then lexicographic ascending — in
  `agentic_devtools/cli/speckit/validate_frs.py`
- [ ] T011 Write tests for `validate_frs(spec_content: str, tasks_content: str) -> ValidationResult` — full pass (all covered), partial fail (some uncovered), no FRs found (warning + pass per FR-014),
  empty tasks content (all uncovered), empty spec content (warning + pass) — in `tests/unit/cli/speckit/validate_frs/test_validate_frs.py`
- [ ] T012 Implement `validate_frs()` orchestrating `extract_frs()` → `check_coverage()` → `sort_fr_ids()` → `ValidationResult` construction, with FR-014 graceful degradation when no FRs extracted —
  in `agentic_devtools/cli/speckit/validate_frs.py`

---

## Phase 3: US1 — Block incomplete task lists before PR creation

- [ ] T013 [US1] Write core tests for `validate_frs_command()` covering JSON output schema, exit code 0 (all covered), exit code 1 (uncovered FRs), and exit code 0 with warning when no FRs found — in
  `tests/unit/cli/speckit/validate_frs/test_validate_frs_command.py`
- [ ] T014 [US1] Implement `validate_frs_command(argv: list | None = None)` with argparse accepting `--spec-file`, `--tasks-file`, `--json`, `--max-retries`; resolve max retries per FR-008 with
  precedence `--max-retries` CLI flag > `SPECKIT_VALIDATE_MAX_RETRIES` env var > default `2`; keep the validator command itself single-pass (no internal retry loop) and expose the resolved value for
  configuration/metadata and/or forwarding by `generate-spec-from-issue.sh`; support JSON output mode; exit codes 0/1/2 — in `agentic_devtools/cli/speckit/validate_frs.py`
- [ ] T015 [US1] [P] Add `agdt-speckit-validate-frs = "agentic_devtools.cli.runner:run_as_script"` entry point in `pyproject.toml`
- [ ] T016 [US1] [P] Add `"agdt-speckit-validate-frs": ("agentic_devtools.cli.speckit", "speckit_validate_frs")` to `COMMAND_MAP` in `agentic_devtools/cli/runner.py`
- [ ] T017 [US1] [P] Add `from .validate_frs import validate_frs_command as speckit_validate_frs` and update `__all__` in `agentic_devtools/cli/speckit/__init__.py`
- [ ] T018 [US1] Reinstall package with `pip install -e .` and verify `agdt-speckit-validate-frs --help` produces usage output
- [ ] T019 [US1] Add `run_fr_validation()` bash function that calls `agdt-speckit-validate-frs --spec-file "$SPEC_DIR/spec.md" --tasks-file "$SPEC_DIR/tasks.md" --json`, captures output to
  `$SPEC_DIR/fr-coverage.json`, and returns the validator exit code — in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
- [ ] T020 [US1] Integrate `run_fr_validation()` in the phase-4 branch of `run_single_phase` immediately after `run_tasks_phase`, before `markdownlint` runs / before the script exits, so the tasks
  PR is blocked when coverage fails — in
  `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
- [ ] T021 [US1] Integrate `run_fr_validation()` call after `run_tasks_phase` and before `run_analyze_phase` in the monolithic (run-all) path — in
  `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`

---

## Phase 4: US2 — Auto-retry task generation on validation failure

- [ ] T022 [US2] Add `--max-retries` argument to script arg parsing and usage text in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
- [ ] T023 [US2] Implement single retry budget resolution into one shell variable with precedence: parsed `--max-retries` arg > `SPECKIT_VALIDATE_MAX_RETRIES` env var > default `2` — in
  `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
- [ ] T024 [US2] Add retry loop around `run_tasks_phase` + `run_fr_validation` in single-phase path: on validation failure extract uncovered FRs from JSON, build augmented prompt listing uncovered
  FRs, re-invoke `run_tasks_phase` with feedback, re-validate — in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
- [ ] T025 [US2] Add equivalent retry loop in the monolithic (run-all) path, reusing the same resolved retry budget variable — in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
- [ ] T026 [US2] Implement retry exhaustion handling: when retry budget is exceeded, exit with code 1 and print clear error message listing all remaining uncovered FRs — in
  `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`

---

## Phase 5: US3 — Standalone CLI command for local validation

- [ ] T027 [US3] Add tests for human-readable output mode (banner, coverage table with ✅/❌ per FR, summary line) when `--json` is not specified — in
  `tests/unit/cli/speckit/validate_frs/test_validate_frs_command.py`
- [ ] T028 [US3] Add tests for `--json` output FR-011 sort order compliance (numeric suffix ascending, tie-break by length then lexicographic) — in
  `tests/unit/cli/speckit/validate_frs/test_validate_frs_command.py`
- [ ] T029 [US3] Add tests for `--max-retries` FR-008 precedence resolution (CLI flag > env var > default 2) — in `tests/unit/cli/speckit/validate_frs/test_validate_frs_command.py`
- [ ] T030 [US3] Add tests for edge cases: missing/empty `spec.md` emits warning and exits 0 (EC4), missing/empty `tasks.md` with FRs exits 1 (EC3), exit code 2 on operational errors — in
  `tests/unit/cli/speckit/validate_frs/test_validate_frs_command.py`
- [ ] T031 [US3] Implement human-readable output mode as default (when `--json` is not specified): validation banner header, per-FR coverage table with status indicators, and pass/fail summary line —
  in `agentic_devtools/cli/speckit/validate_frs.py`

---

## Phase 6: US4 — Enrich analysis report with FR coverage data

- [ ] T032 [US4] Update `run_analyze_phase()` to read `$SPEC_DIR/fr-coverage.json` when it exists and inject FR coverage summary into the LLM analysis prompt as structured context — in
  `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
- [ ] T033 [US4] Add instruction in Step 2 (Load Artifacts) to load `fr-coverage.json` and include deterministic FR coverage data in the Coverage Gaps detection pass — in
  `.github/agents/speckit.analyze.agent.md`
- [ ] T034 [US4] Add instruction that FR coverage data is deterministic (pre-validated) and should be reported as-is in the analysis report's Coverage Summary section — in
  `.github/agents/speckit.analyze.agent.md`

---

## Final Phase: Polish & Cross-Cutting

- [ ] T035 Run `ruff check --fix . && ruff format .` to fix any lint or formatting issues
- [ ] T036 Run test structure validator with `python scripts/validate_test_structure.py` and fix any structural issues
- [ ] T037 Run full test suite with `agdt-test` and `agdt-task-wait`
- [ ] T038 Run full PR check suite with `bash scripts/run-pr-checks.sh` and fix any failures

---

## Dependency Graph

```text
T001 ──┬──→ T003 ──→ T007 ──┬──→ T008 ──┐
       │                     │           │
       ├──→ T004 ────────────┘           │
       │                                 ├──→ T011 ──→ T012 ──→ T013 ──→ T014 ──┐
       ├──→ T005 ──→ T009 ──────────────┤                                        │
       │                                 │                                        │
       └──→ T006 ──→ T010 ──────────────┘                                        │
                                                                                  │
T002 ──→ T003, T004, T005, T006, T011, T013                                      │
                                                                                  │
T014 ──→ T015, T016, T017 (parallel) ──→ T018                                    │
                                                                                  │
T018 ──→ T019 ──→ T020, T021 (parallel)  ← US1 pipeline gate                     │
                                                                                  │
T020, T021 ──→ T022 ──→ T023 ──→ T024, T025 (parallel) ──→ T026  ← US2 retry    │
                                                                                  │
T014 ──→ T027, T028, T029, T030 (parallel) ──→ T031  ← US3 standalone            │
                                                                                  │
T019 ──→ T032 ──→ T033, T034 (parallel)  ← US4 analysis enrichment               │
                                                                                  │
T026, T031, T034 ──→ T035 ──→ T036 ──→ T037 ──→ T038  ← Final phase             │
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
