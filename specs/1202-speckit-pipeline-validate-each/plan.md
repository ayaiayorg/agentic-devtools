# Implementation Plan: SpecKit E.2 Test Coverage Validation

**Issue**: [#1202](https://github.com/ayaiayorg/agentic-devtools/issues/1202)
**Branch**: `speckit/1202/phase-3-plan`

## 1. Technical Context

- **Stack**: Python >=3.10, `agentic-devtools` pip package, `speckit.analyze` agent prompt
- **Key dependencies**: Existing `validate_frs.py` (FR extraction + coverage), `.github/agents/speckit.analyze.agent.md` (Category E), `pass_g/` package (precedent for structured analysis passes)
- **Architecture**: Two execution paths exist for SpecKit analysis:
  1. **Local CLI** (`agdt-speckit-analyze`): renders and prints the agent prompt from `.github/agents/speckit.analyze.agent.md` for the user/agent to execute
  2. **GitHub Action pipeline** (`generate-spec-from-issue.sh` → `run_analyze_phase`): runs analysis via an inline prompt that loads artifact files (e.g., `fr-coverage.json`) into LLM context

  This feature adds a **deterministic Python module** (`pass_e2/`) that performs test-coverage validation, plus updates to **both** integration points:
  the agent prompt template (Category E) and the pipeline's artifact-loading logic
- **Test policy**: 1:1:1 test structure under `tests/unit/`, TDD red-green-refactor, 100% coverage per source file

## 2. Research Summary

Key architectural decisions:

- **Architecture choice**: Deterministic Python module (like `validate_frs.py` and `pass_g/`) vs. pure prompt instructions → **Hybrid**: Python module for deterministic validation + prompt updates for
  report integration
- **Keyword matching strategy**: Regex with word-boundary and hyphen-normalization rules per FR-002
- **User-story mapping**: Positional document-order parsing of `spec.md` user story sections
- **Regression test approach**: Parameterized pytest discovering `specs/*/` directories

## 3. Design Overview

### Module Structure

```text
agentic_devtools/cli/speckit/
├── pass_e2/                          # NEW: Test coverage validation
│   ├── __init__.py                   # Public API exports
│   ├── constants.py                  # Keyword sets (FR-011), test-type keyword tables (FR-006)
│   ├── models.py                     # Data classes: TestTask, FRInfo, FRCoverage, TestCoverageResult, TestCoverageFinding
│   ├── spec_parser.py                # FR extraction with priority + user-story section parsing
│   ├── task_classifier.py            # Test-task identification (FR-002) + test-type classification (FR-006)
│   ├── coverage_mapper.py            # FR-to-test-task mapping (FR-003) + coverage evaluation (FR-004/005)
│   ├── reporter.py                   # Test Coverage Summary table + findings generation (FR-007/008)
│   └── validator.py                  # Orchestrator: runs the full E.2 pipeline
```

### Data Flow

```text
spec.md → spec_parser → FRs with priorities + US sections
                                                           ↘
tasks.md → task_classifier → test tasks with types          → coverage_mapper → TestCoverageResult
                                                           ↗
                                          US-to-FR mapping
                                                           ↓
                                                      reporter → findings + summary table
```

### Integration Points

1. **`.github/agents/speckit.analyze.agent.md`**: Update Category E section to add E.1/E.2 sub-pass labeling and instruct the agent to incorporate E.2 test-coverage findings
2. **CLI entry point**: `agdt-speckit-test-coverage` standalone command (like `agdt-speckit-validate-frs`)
3. **Analysis artifact (`test-coverage.json`)**: Optionally emit `test-coverage.json` for the analyze agent to consume deterministically

## 4. Implementation Phases

### Phase 1: Setup & Data Models

**Deliverables**: Module scaffolding, data classes, constants

- T001: Create `agentic_devtools/cli/speckit/pass_e2/` package with `__init__.py`
- T002: Create `tests/unit/cli/speckit/pass_e2/` directory tree with `__init__.py` files
- T003: **[RED]** Write tests for `constants.py` — verify `TEST_TASK_KEYWORDS` contains all FR-002 keywords, `TEST_TYPE_KEYWORDS` contains all FR-006 type tables, keyword sets are non-empty, no
  duplicates
- T004: Implement `constants.py` — `TEST_TASK_KEYWORDS` list (FR-002/FR-011), `TEST_TYPE_KEYWORDS` dict mapping test types to keyword lists (FR-006)
- T005: **[RED]** Write tests for `models.py` — `TestTask`, `FRInfo`, `FRCoverage`, `TestCoverageResult`, `TestCoverageFinding` data classes with field access, equality, serialization
- T006: Implement `models.py` — all data classes

### Phase 2: Spec Parser (FR-001, FR-003 partial)

**Deliverables**: FR extraction with priority, user-story section parsing

- T007: **[RED]** Write tests for `spec_parser.extract_frs_with_priority()` — extract FR identifiers with associated user-story priority (P1/P2/P3), default to non-P1 when priority
  undetermined (i.e., treat as HIGH severity for FR-004 and avoid FR-005 CRITICAL escalation per FR-001), emit LOW informational finding with stable key `FR-NNN:priority-ambiguous` for ambiguous
  priority
- T008: Implement `spec_parser.extract_frs_with_priority()`
- T009: **[RED]** Write tests for `spec_parser.parse_user_story_sections()` — positional extraction of user story sections from spec.md, collecting FR references within each section's text boundary,
  handling edge cases (no user stories, single user story, user stories without FRs)
- T010: Implement `spec_parser.parse_user_story_sections()`
- T011: **[RED]** Write tests for `spec_parser.build_us_to_fr_mapping()` — given parsed user story sections, produce `{1: ["FR-001", "FR-003"], 2: ["FR-002"]}` mapping
- T012: Implement `spec_parser.build_us_to_fr_mapping()`

### Phase 3: Task Classifier (FR-002, FR-006)

**Deliverables**: Test-task identification, test-type classification

- T013: **[RED]** Write tests for `task_classifier.is_test_task()` — single-word keyword matching with word boundaries, multi-word keyword matching with hyphen/space normalization, plural variants,
  case-insensitive, false-positive avoidance (e.g., "contest", "unverified")
- T014: Implement `task_classifier.is_test_task()`
- T015: **[RED]** Write tests for `task_classifier.classify_test_types()` — happy-path, edge-case, negative, integration, e2e, unit, infrastructure keywords; multiple types per task; hyphen/space
  normalization; empty result for non-test tasks
- T016: Implement `task_classifier.classify_test_types()`
- T017: **[RED]** Write tests for `task_classifier.extract_task_fr_refs()` — explicit FR-NNN references in task description, `[USn]` label extraction
- T018: Implement `task_classifier.extract_task_fr_refs()`
- T019: **[RED]** Write tests for `task_classifier.detect_ambiguous_task()` — tasks with both implementation and test keywords flagged as ambiguous
- T020: Implement `task_classifier.detect_ambiguous_task()`

### Phase 4: Coverage Mapper (FR-003, FR-004, FR-005)

**Deliverables**: FR-to-test-task mapping, coverage evaluation, severity determination

- T021: **[RED]** Write tests for `coverage_mapper.map_test_tasks_to_frs()` — explicit FR refs, US-label mapping via `us_to_fr`, unmapped test tasks (no FR ref, no US label), invalid US refs (`[US99]`
  when only 3 user stories)
- T022: Implement `coverage_mapper.map_test_tasks_to_frs()`
- T023: **[RED]** Write tests for `coverage_mapper.evaluate_coverage()` — FR with zero test tasks → HIGH finding (FR-004), P1 FR with no happy-path test → CRITICAL (FR-005), de-duplication (FR-004 +
  FR-005 → single CRITICAL), fully covered FR → no finding, P3 FR with no test → HIGH not CRITICAL
- T024: Implement `coverage_mapper.evaluate_coverage()`
- T025: **[RED]** Write tests for edge cases — empty tasks.md → CRITICAL finding (FR-009) with stable key `TASK:empty-tasks-file`, tasks.md not found → CRITICAL with stable key
  `TASK:missing-tasks-file`, FR without acceptance scenarios → finding with "N/A" note
- T025a: **[RED]** Write tests for `coverage_mapper.generate_task_scoped_findings()` — invalid `[USn]` refs → LOW finding with stable key `TASK:invalid-us-ref`, unmapped test tasks (no FR ref,
  no `[USn]` label) → LOW finding with stable key `TASK:unmapped-test-task`, ambiguous tasks (from `detect_ambiguous_task()`) → LOW finding with stable key `TASK:ambiguous-task`;
  all task-scoped findings are allowlistable under NFR-003
- T025b: Implement `coverage_mapper.generate_task_scoped_findings()` — emit LOW-severity `TestCoverageFinding` entries with stable `TASK:<kind>` keys for each task-scoped issue

### Phase 5: Reporter (FR-007, FR-008)

**Deliverables**: Test Coverage Summary table, actionable recommendations

- T026: **[RED]** Write tests for `reporter.render_test_coverage_summary()` — table with columns: FR, user story, test task IDs, test types, coverage status; N/A for unknown user story; "None" for
  uncovered FRs
- T027: Implement `reporter.render_test_coverage_summary()`
- T028: **[RED]** Write tests for `reporter.render_findings()` — severity column, actionable Recommendation referencing specific FR and acceptance scenarios (or "N/A"),
  CRITICAL vs HIGH vs LOW distinction; include task-scoped findings (invalid-us-ref, unmapped-test-task, ambiguous-task) in an "Unmapped Tasks" sub-section
- T029: Implement `reporter.render_findings()`

> **Finding ID strategy**: E.2 outputs use **stable keys** internally — `FR-NNN:<kind>` for FR-scoped findings (e.g., `FR-001:no-test-task`, `FR-002:no-happy-path`,
> `FR-001:priority-ambiguous`) and `TASK:<kind>` for task-scoped findings (e.g., `TASK:unmapped-test-task`, `TASK:invalid-us-ref`, `TASK:ambiguous-task`) as well as
> input-level findings (e.g., `TASK:missing-tasks-file`, `TASK:empty-tasks-file` per FR-009). Both key formats are defined by NFR-003's allowlist schema, so
> input-level validation failures reuse the `TASK:<kind>` prefix rather than introducing a third format. These keys are emitted in `test-coverage.json` for NFR-003 allowlisting
> and deterministic regression testing. The analyze report (`.github/agents/speckit.analyze.agent.md`) assigns **global sequential `F-NN` IDs** when composing the final report across all
> categories/sub-passes, avoiding ID collisions between E.1, E.2, and other passes. The `reporter.render_findings()` function therefore does **not** assign `F-NN` IDs — it renders
> findings by stable key, and the agent prompt handles final numbering.

### Phase 6: Orchestrator & CLI (FR-010)

**Deliverables**: End-to-end validation pipeline, CLI entry point

- T030: **[RED]** Write tests for `validator.validate_test_coverage()` — end-to-end: spec+tasks input → `TestCoverageResult` with findings, summary, and coverage mappings
- T031: Implement `validator.validate_test_coverage()`
- T032: **[RED]** Write tests for CLI entry point `test_coverage_command()` — JSON output, human-readable output, exit codes (0 = no findings, 1 = findings present including CRITICAL such as
  missing/empty tasks.md per FR-009, 2 = fatal operational error e.g. unreadable file or unexpected parse exception)
- T033: Implement CLI entry point in `validator.py` or separate `cli.py`
- T034: Add `agdt-speckit-test-coverage` to `COMMAND_MAP` in `agentic_devtools/cli/runner.py`; add `[project.scripts]` entry pointing to `agentic_devtools.cli.runner:run_as_script`
  (mirroring `agdt-speckit-validate-frs` — all `agdt-speckit-*` commands dispatch through the runner, not directly to module functions)
- T035: Add exports in `pass_e2/__init__.py` and `speckit/__init__.py`
- T036: Reinstall package, verify `agdt-speckit-test-coverage --help`

### Phase 7: Agent Prompt Integration (FR-010)

**Deliverables**: Updated `.github/agents/speckit.analyze.agent.md` with E.1/E.2 structure

- T037: Update Category E in `.github/agents/speckit.analyze.agent.md` — rename existing coverage check to "E.1 Task Coverage",
  add "E.2 Test Coverage Validation" sub-pass referencing `test-coverage.json` (if present) or instructing the agent to apply the E.2 rules inline
- T038: Update "Load Artifacts" section (Step 2) to include `test-coverage.json` loading
- T039: Update "Produce Compact Analysis Report" section (Step 6) to include "Test Coverage Summary" table
- T040: Update Severity Assignment (Step 5) to document CRITICAL for P1+no-happy-path, HIGH for any-FR+no-test-task
- T041: Update Metrics section to include test-coverage metrics

### Phase 8: Regression Tests (NFR-003)

**Deliverables**: Parameterized regression test, SC-001 fixture

- T042: Create `specs/1202-speckit-pipeline-validate-each/fixtures/sc-001/spec.md` — synthetic spec with P1 FR, no happy-path test task
- T043: Create `specs/1202-speckit-pipeline-validate-each/fixtures/sc-001/tasks.md` — implementation tasks + infrastructure tests but no happy-path test for FR-001
- T044: **[RED]** Write parameterized regression test `test_regression_specs_zero_false_positives` — discovers all `specs/*/` with both `spec.md` and `tasks.md`, runs `validate_test_coverage()`,
  asserts generated finding keys (using stable `FR-NNN:<kind>` and `TASK:<kind>` formats per NFR-003) exactly match `expected-findings.txt` allowlist via set semantics (or zero findings when no
  allowlist exists)
- T045: Run regression test against all existing specs, create `expected-findings.txt` files where needed
- T046: **[RED]** Write SC-001 test — verify CRITICAL finding for FR-001 missing happy-path test in sc-001 fixture
- T047: Write SC-003 test — verify Test Coverage Summary table with 3+ FRs
- T048: Write SC-004 test — verify all findings have non-empty actionable Recommendation
- T049: Write SC-005 test — verify CRITICAL vs HIGH severity distinction

### Phase 9: Pipeline Integration

**Deliverables**: Shell integration in `generate-spec-from-issue.sh`

- T050: Add `run_test_coverage_validation()` bash function calling `agdt-speckit-test-coverage --spec-file --tasks-file --json` and saving output to `$SPEC_DIR/test-coverage.json`;
  capture exit code and continue (like `run_fr_validation`) — exit 1 (findings present) is non-blocking so findings flow into the analyze phase; only exit 2 (fatal) aborts
- T051: Integrate `run_test_coverage_validation()` in pipeline after `run_fr_validation()`, before analysis phase
- T051a: Update `run_analyze_phase` in `generate-spec-from-issue.sh` to load `test-coverage.json` into the inline LLM prompt context (mirroring how `fr-coverage.json` is injected today),
  so CI-generated `analysis-report.md` includes E.2 findings
- T052: End-to-end smoke test verifying pipeline integration (including `test-coverage.json` artifact presence in analysis output)

### Phase 10: Final Validation

- T053: Run full test suite (`agdt-test` + `agdt-task-wait`)
- T054: Run `bash scripts/run-pr-checks.sh`
- T055: Manual verification against SC-001 fixture
- T056: Verify backward compatibility — all existing specs produce no new false positives

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Keyword matching produces false positives on existing specs | Medium | HIGH | NFR-003 regression test runs against all `specs/*/`; `expected-findings.txt` allowlist for known gaps |
| User-story section parsing is fragile across different spec formats | Medium | MEDIUM | Test against all existing spec.md files; use robust heading-level detection |
| Hyphen/space normalization in keyword matching interacts unexpectedly with FR-002's word-boundary rules | Low | HIGH | Comprehensive unit tests covering all edge cases from the spec's FR-002 definition |
| Agent prompt changes cause regression in non-E.2 analysis categories | Low | MEDIUM | Keep E.2 changes strictly additive; test existing analysis output is unchanged |
| `expected-findings.txt` allowlist becomes stale as specs evolve | Low | LOW | CI enforcement via exact-match assertion catches both new and stale entries |

## 6. Dependencies

### Internal

- `agentic_devtools/cli/speckit/validate_frs.py` — reuse `extract_frs()`, `sort_fr_ids()`, `_FR_RE` regex
- `agentic_devtools/cli/speckit/pass_g/` — architectural precedent for structured analysis passes
- `.github/agents/speckit.analyze.agent.md` — prompt template to update
- `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` — pipeline integration point

### External

- None (pure Python, no new dependencies)

---
*Generated by Copilot SDK (claude-opus-4.6)*
