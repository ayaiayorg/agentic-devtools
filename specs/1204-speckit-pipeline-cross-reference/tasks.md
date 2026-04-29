# Tasks: Pass G — Code Reference Cross-Referencing

**Feature**: SpecKit pipeline cross-reference plan code references against actual codebase
**Issue**: #1204
**Spec**: `specs/1204-speckit-pipeline-cross-reference/spec.md`
**Plan**: `specs/1204-speckit-pipeline-cross-reference/plan.md`

---

## Phase 1: Setup — Project Scaffolding

- [ ] T001 Create package directory `agentic_devtools/cli/speckit/pass_g/` with `__init__.py`
- [ ] T002 Create extractor subpackage `agentic_devtools/cli/speckit/pass_g/extractors/` with `__init__.py`
- [ ] T003 Create test directory tree `tests/unit/cli/speckit/pass_g/` with all `__init__.py` files for subdirectories: `constants/`, `models/`, `extractors/`, `extractors/base/`,
  `extractors/python_extractor/`, `inventory/`, `reference_extractor/`, `intent_detector/`, `matcher/`, `classifier/`, `reporter/`

---

## Phase 2: Foundational — Constants and Data Models

### Constants (`agentic_devtools/cli/speckit/pass_g/constants.py`)

- [ ] T004 [P] Write test `tests/unit/cli/speckit/pass_g/constants/test_suggestion_threshold.py` — verify `SUGGESTION_THRESHOLD == 0.75` (FR-008)
- [ ] T005 [P] Write test `tests/unit/cli/speckit/pass_g/constants/test_high_confidence_threshold.py` — verify `HIGH_CONFIDENCE_THRESHOLD == 0.90` (FR-009)
- [ ] T006 [P] Write test `tests/unit/cli/speckit/pass_g/constants/test_disambiguation_margin.py` — verify `DISAMBIGUATION_MARGIN == 0.05` (FR-009, FR-010)
- [ ] T007 [P] Write test `tests/unit/cli/speckit/pass_g/constants/test_performance_warning_seconds.py` — verify `PERFORMANCE_WARNING_SECONDS == 30` (NFR-002)
- [ ] T008 [P] Write test `tests/unit/cli/speckit/pass_g/constants/test_new_symbol_verb_markers.py` — verify tuple contains all 12 verb markers from FR-006
- [ ] T009 [P] Write test `tests/unit/cli/speckit/pass_g/constants/test_new_symbol_noun_markers.py` — verify tuple contains all noun markers from FR-006
- [ ] T010 [P] Write test `tests/unit/cli/speckit/pass_g/constants/test_protected_file_patterns.py` — verify `_version.py`, `__pycache__`, `.git/` present (FR-011)
- [ ] T011 [P] Write test `tests/unit/cli/speckit/pass_g/constants/test_max_candidates_per_reference.py` — verify `MAX_CANDIDATES_PER_REFERENCE == 5`
- [ ] T012 Implement `agentic_devtools/cli/speckit/pass_g/constants.py` — all named constants (FR-006, FR-008, FR-009, FR-010, FR-011, NFR-002); make tests T004–T011 pass

### Data Models (`agentic_devtools/cli/speckit/pass_g/models.py`)

- [ ] T013 [P] Write test `tests/unit/cli/speckit/pass_g/models/test_referencekind.py` — verify enum members: `FILE_PATH`, `MODULE_PATH`, `CLASS_NAME`, `FUNCTION_NAME`, `METHOD_NAME`, `CLI_COMMAND`,
  `UNCLASSIFIED` (FR-001, FR-007)
- [ ] T014 [P] Write test `tests/unit/cli/speckit/pass_g/models/test_reference.py` — verify dataclass fields: `text`, `kind`, `plan_location`, `context_sentence` (FR-001, FR-004)
- [ ] T015 [P] Write test `tests/unit/cli/speckit/pass_g/models/test_matchstatus.py` — verify enum members: `MATCHED`, `INVALID`, `AMBIGUOUS`, `PARTIAL`, `SKIPPED`, `NEW_SYMBOL` (FR-003)
- [ ] T016 [P] Write test `tests/unit/cli/speckit/pass_g/models/test_candidate.py` — verify dataclass fields: `symbol_name`, `file_path`, `similarity_score`, `kind` (FR-008)
- [ ] T017 [P] Write test `tests/unit/cli/speckit/pass_g/models/test_finding.py` — verify dataclass fields: `reference`, `status`, `candidates`, `confidence_level`, `explanation` (FR-013, FR-014)
- [ ] T018 Implement `agentic_devtools/cli/speckit/pass_g/models.py` — all enums and dataclasses; make tests T013–T017 pass

### Extractor Base Class (`agentic_devtools/cli/speckit/pass_g/extractors/base.py`)

- [ ] T019 Write test `tests/unit/cli/speckit/pass_g/extractors/base/test_symbolextractor.py` — verify abstract base class with `supported_extensions()` and `extract_symbols()` methods, plus
  `SymbolEntry` dataclass (FR-002)
- [ ] T020 Implement `agentic_devtools/cli/speckit/pass_g/extractors/base.py` — abstract `SymbolExtractor` base and `SymbolEntry` dataclass; make test T019 pass

---

## Phase 3: US1 — Detect Nonexistent Code References (P1)

### Repository Inventory (`agentic_devtools/cli/speckit/pass_g/inventory.py`)

- [ ] T021 [US1] Write test `tests/unit/cli/speckit/pass_g/inventory/test_build_inventory.py` — verify `build_inventory()` discovers files via `git ls-files`, applies `PROTECTED_FILE_PATTERNS`,
  delegates to language extractors (FR-002, FR-011)
  - Depends on: T012, T018, T020
- [ ] T022 [US1] Write test `tests/unit/cli/speckit/pass_g/inventory/test_symbolinventory.py` — verify `has_file()`, `find_files()`, `get_symbols_by_name()`, `get_all_symbols()`,
  `get_all_file_paths()` methods; verify deterministic sort order (FR-002, FR-007, NFR-001)
  - Depends on: T018, T020
- [ ] T023 [US1] Implement `agentic_devtools/cli/speckit/pass_g/inventory.py` — `SymbolInventory` class and `build_inventory()` function using `git ls-files --cached --others --exclude-standard` for
  file discovery (FR-002, FR-007, FR-011); make tests T021–T022 pass

### Python Extractor (`agentic_devtools/cli/speckit/pass_g/extractors/python_extractor.py`)

- [ ] T024 [P] [US1] Write test `tests/unit/cli/speckit/pass_g/extractors/python_extractor/test_pythonextractor.py` — verify extraction of class names, function names, method names, module paths from
  `.py` files via `ast.parse()`; verify `pyproject.toml` CLI entry point extraction; verify graceful skip on unparseable files (FR-002, FR-007, NFR-005)
  - Depends on: T020
- [ ] T025 [US1] Implement `agentic_devtools/cli/speckit/pass_g/extractors/python_extractor.py` — `PythonExtractor` implementing `SymbolExtractor` base; uses `ast` for Python symbols and
  `tomllib`/fallback for CLI entry points (FR-002, FR-007); make test T024 pass

### Plan Reference Extraction (`agentic_devtools/cli/speckit/pass_g/reference_extractor.py`)

- [ ] T026 [US1] Write test `tests/unit/cli/speckit/pass_g/reference_extractor/test_extract_references.py` — verify backtick-quoted identifiers, code fence contents, deduplication, line number
  preservation; verify empty plan yields zero references (FR-001, FR-004, FR-015)
  - Depends on: T018
- [ ] T027 [US1] Write test `tests/unit/cli/speckit/pass_g/reference_extractor/test_classify_reference_kind.py` — verify classification into `ReferenceKind` by syntactic pattern: file paths, module
  dotted paths, class/function names, CLI commands, unclassified (FR-001, FR-007)
  - Depends on: T018
- [ ] T028 [US1] Implement `agentic_devtools/cli/speckit/pass_g/reference_extractor.py` — `extract_references()` and `classify_reference_kind()` (FR-001, FR-004); make tests T026–T027 pass

### Classifier — Core Invalid Detection (`agentic_devtools/cli/speckit/pass_g/classifier.py`)

- [ ] T029 [US1] Write test `tests/unit/cli/speckit/pass_g/classifier/test_classify_references.py` — US1 scenarios: nonexistent file/symbol flagged as `INVALID` (FR-003, FR-005); multiple invalid refs
  reported separately (FR-013); valid-only plan produces zero findings (FR-015); verify no plan/repo modification (FR-016)
  - Depends on: T018, T023, T028
- [ ] T030 [US1] Implement `agentic_devtools/cli/speckit/pass_g/classifier.py` — `classify_references()` orchestrator with exact match path and `INVALID`/`MATCHED`/`SKIPPED` classification (FR-003,
  FR-005, FR-015, FR-016); make test T029 pass

---

## Phase 4: US2 — Suggest Likely Intended Matches (P1)

### Matcher (`agentic_devtools/cli/speckit/pass_g/matcher.py`)

- [ ] T031 [US2] Write test `tests/unit/cli/speckit/pass_g/matcher/test_exact_match.py` — verify exact match against file paths, symbol names, qualified names (FR-007)
  - Depends on: T018, T023
- [ ] T032 [US2] Write test `tests/unit/cli/speckit/pass_g/matcher/test_fuzzy_match.py` — verify `difflib.SequenceMatcher.ratio()` matching: candidates ≥ 0.75 surfaced, below 0.75 discarded;
  deterministic sort by `(score desc, symbol_name, file_path, kind)`; capped at `MAX_CANDIDATES_PER_REFERENCE`; no suggestion when no candidate ≥ 0.75 (FR-008, FR-010, NFR-001, NFR-003)
  - Depends on: T012, T018, T023
- [ ] T033 [US2] Write test `tests/unit/cli/speckit/pass_g/matcher/test_classify_match_confidence.py` — verify high-confidence when score ≥ 0.90 with no competitor within 0.05; ambiguous when multiple
  within 0.05 (FR-009, FR-010)
  - Depends on: T012, T018
- [ ] T034 [US2] Implement `agentic_devtools/cli/speckit/pass_g/matcher.py` — `exact_match()`, `fuzzy_match()`, `classify_match_confidence()` using `difflib.SequenceMatcher` (FR-007, FR-008, FR-009,
  FR-010, NFR-001, NFR-003); make tests T031–T033 pass
- [ ] T035 [US2] Update `classifier.py` to integrate fuzzy matching path: attempt fuzzy match when exact fails, classify as `AMBIGUOUS` or suggestion-backed `INVALID` (FR-005, FR-008, FR-009); update
  test T029 with US2 scenarios
  - Depends on: T030, T034

---

## Phase 5: US3 — Respect Explicit "New Symbol" Intent (P1)

### Intent Detector (`agentic_devtools/cli/speckit/pass_g/intent_detector.py`)

- [ ] T036 [US3] Write test `tests/unit/cli/speckit/pass_g/intent_detector/test_detect_new_symbol_intent.py` — verify verb markers ("create", "add", etc.) suppress flags (FR-006); verify noun markers
  ("new file", "new class", etc.) suppress flags (FR-006); verify markers must be in same sentence/step; verify mixed new + existing refs only flag existing (FR-006)
  - Depends on: T012, T018
- [ ] T037 [US3] Implement `agentic_devtools/cli/speckit/pass_g/intent_detector.py` — `detect_new_symbol_intent()` using regex against `NEW_SYMBOL_VERB_MARKERS` and `NEW_SYMBOL_NOUN_MARKERS` constants
  (FR-006); make test T036 pass
- [ ] T038 [US3] Update `classifier.py` to check intent before matching: if new-symbol intent detected, classify as `NEW_SYMBOL` and skip matching (FR-006); add US3 test scenarios to T029
  - Depends on: T030, T037

---

## Phase 6: US4 — Handle Ambiguous or Partial References (P2)

- [ ] T039 [US4] Add test scenarios to `test_classify_references.py` — short ambiguous name (`run`, `Config`) marked ambiguous with candidate locations (FR-010); module exists but symbol missing →
  `PARTIAL` (FR-003); unclassifiable reference → `SKIPPED` (FR-015, NFR-005)
  - Depends on: T035, T038
- [ ] T040 [US4] Update `classifier.py` — add `PARTIAL` classification when file exists but symbol not found; add `SKIPPED` for unclassifiable references; graceful degradation when extraction
  incomplete (FR-003, FR-015, NFR-005); make test T039 pass

---

## Phase 7: US5 — Integrate Findings into Analysis Report (P2)

### Reporter (`agentic_devtools/cli/speckit/pass_g/reporter.py`)

- [ ] T041 [US5] Write test `tests/unit/cli/speckit/pass_g/reporter/test_render_markdown.py` — verify Markdown table output with severity mapping (INVALID→HIGH, candidates→MEDIUM, AMBIGUOUS→MEDIUM,
  PARTIAL→LOW, SKIPPED→LOW); verify human-readable explanations with similarity scores (FR-012, FR-013, FR-014); verify performance warning when elapsed > `PERFORMANCE_WARNING_SECONDS` (NFR-002)
  - Depends on: T018, T012
- [ ] T042 [US5] Write test `tests/unit/cli/speckit/pass_g/reporter/test_render_json.py` — verify structured JSON output distinguishing `INVALID`, `AMBIGUOUS`, `SKIPPED`, suggestion-backed findings by
  status (FR-012, FR-013); verify Pass G success with zero findings recorded (FR-015)
  - Depends on: T018
- [ ] T043 [US5] Implement `agentic_devtools/cli/speckit/pass_g/reporter.py` — `render_markdown()` and `render_json()` (FR-012, FR-013, FR-014, NFR-002, NFR-004); make tests T041–T042 pass

### Package Public API

- [ ] T044 [US5] Update `agentic_devtools/cli/speckit/pass_g/__init__.py` — export public API: `classify_references`, `build_inventory`, `extract_references`, `render_markdown`, `render_json`,
  `detect_new_symbol_intent`, constants, and all model classes (FR-012)

---

## Phase 8: US6 — Support Future Remediation Workflows (P3)

- [ ] T045 [US6] Add test scenarios to `test_finding.py` — verify serialized finding includes `reference.text`, `status`, `candidates` with `similarity_score`, `reference.plan_location`; verify stable
  structured output without edits (FR-013, FR-014, FR-016)
  - Depends on: T018
- [ ] T046 [US6] Add `to_dict()` method to `Finding` dataclass in `models.py` for stable JSON serialization — include all metadata for future remediation consumers (FR-013, FR-016); make test T045
  pass

---

## Phase 9: CLI Entry Point and Agent Prompt Integration

### CLI Entry Point (`agentic_devtools/cli/speckit/cross_ref.py`)

- [ ] T047 Create `agentic_devtools/cli/speckit/cross_ref.py` — `cross_ref_command()` with `argparse` accepting `--plan-file` and `--repo-root`; orchestrate full pipeline: extract → build inventory →
  detect intent → classify → report; emit performance warning if elapsed > threshold (NFR-002); output JSON or Markdown (FR-012, FR-013)
  - Depends on: T023, T028, T037, T030, T043
- [ ] T048 Update `agentic_devtools/cli/speckit/__init__.py` — add `cross_ref_command` export as `speckit_cross_ref`
- [ ] T049 Register `agdt-speckit-cross-ref` in `pyproject.toml` `[project.scripts]`
- [ ] T050 Register `agdt-speckit-cross-ref` in `agentic_devtools/cli/runner.py` `COMMAND_MAP`
- [ ] T051 Reinstall package with `pip install -e .` to activate new entry point

### Agent Prompt Integration

- [ ] T052 Update `.github/agents/speckit.analyze.agent.md` — add **Pass G: Code Reference Cross-Referencing** section after Pass F; include instructions to invoke `agdt-speckit-cross-ref` CLI;
  integrate findings into sequential finding ID contract (`F-01`, `F-02`, …); add Pass G to severity assignment guidance and Metrics section (FR-012, NFR-004)
- [ ] T053 [P] Update `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` — add Pass G instructions to `run_analyze_phase` embedded prompt so CI pipeline executes Pass G (FR-012)

---

## Phase 10: Polish & Cross-Cutting

### Determinism and Performance Validation

- [ ] T054 Add determinism integration test — run `classify_references()` twice on identical input and assert identical output including candidate ordering (NFR-001)
  - Depends on: T040
- [ ] T055 Add performance benchmark test — verify Pass G completes within `PERFORMANCE_WARNING_SECONDS` for a synthetic repo with 5,000 file paths and 200 references (NFR-002)
  - Depends on: T047

### Edge Case Coverage

- [ ] T056 [P] Add test — empty plan with no references produces success with zero findings (Edge Case 1, FR-015)
- [ ] T057 [P] Add test — `_version.py` and `__pycache__` excluded from inventory and suggestions (Edge Case 3, FR-011)
- [ ] T058 [P] Add test — non-Python file path references (`.md`, `.toml`, `.yml`, `.json`) matched by file path regardless of language support (Edge Case 7, FR-007)
- [ ] T059 [P] Add test — fresh filesystem scan per run, no stale cache (Edge Case 4, FR-002)

### Validation and Cleanup

- [ ] T060 Run `python scripts/validate_test_structure.py` to verify 1:1:1 test structure compliance
- [ ] T061 Run `bash scripts/run-pr-checks.sh` — full PR check suite (tests, lint, format, markdownlint, mypy)
- [ ] T062 Update `agentic_devtools/cli/speckit/pass_g/__init__.py` docstring and copilot-instructions if needed

---

## Dependency Summary

| Task | Depends On |
|------|-----------|
| T012 | T004–T011 (tests written first) |
| T018 | T013–T017 |
| T020 | T019 |
| T023 | T012, T018, T020 |
| T025 | T020 |
| T028 | T018 |
| T030 | T018, T023, T028 |
| T034 | T012, T018, T023 |
| T035 | T030, T034 |
| T037 | T012, T018 |
| T038 | T030, T037 |
| T040 | T035, T038 |
| T043 | T018, T012 |
| T047 | T023, T028, T037, T030, T043 |
| T048–T051 | T047 |
| T052–T053 | T043, T047 |
| T054–T055 | T040, T047 |
| T056–T059 | T040 |
| T060–T062 | All prior tasks |

## FR Traceability Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T013, T014, T026, T027, T028 |
| FR-002 | T019, T020, T021, T022, T023, T024, T025, T059 |
| FR-003 | T015, T029, T030, T039, T040 |
| FR-004 | T014, T026, T028 |
| FR-005 | T029, T030, T035 |
| FR-006 | T008, T009, T012, T036, T037, T038 |
| FR-007 | T013, T022, T023, T024, T025, T027, T031, T034, T058 |
| FR-008 | T004, T012, T016, T032, T034, T035 |
| FR-009 | T005, T006, T012, T033, T034, T035 |
| FR-010 | T006, T012, T032, T033, T034, T039 |
| FR-011 | T010, T012, T021, T023, T057 |
| FR-012 | T041, T042, T043, T044, T047, T052, T053 |
| FR-013 | T017, T029, T041, T042, T043, T045, T047 |
| FR-014 | T017, T041, T043, T045 |
| FR-015 | T015, T026, T029, T039, T042, T056 |
| FR-016 | T029, T045, T046 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
