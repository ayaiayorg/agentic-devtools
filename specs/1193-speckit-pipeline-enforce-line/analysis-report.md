# Cross-Artifact Consistency & Quality Analysis Report

## 1. Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F01 | F. Inconsistency | HIGH | Spec §5 `WrappableToken`, Plan §4 Phase 1 `tokenize()` | Spec defines `WrappableToken` as a key entity with `text` and `length` fields, but plan's `tokenize()` returns `list[str]`, not `list[WrappableToken]`. T007 only defines `ProtectedBlock` and `LineContext` dataclasses — `WrappableToken` is never implemented. | Either remove `WrappableToken` from the spec data model or add a task to implement it and update `tokenize()` return type. |
| F02 | E. Coverage | HIGH | NFR-001 | No task verifies the 5-second performance budget for up to 10 files / 50 KB. | Add a dedicated performance test task (e.g., between T037 and T038) that times `wrap_files` against a representative input set. |
| F03 | E. Coverage | HIGH | NFR-003, SM3 | No task verifies directory isolation (no files outside `$SPEC_DIR` modified) or that the wrap step adds <2 seconds to pipeline time. | Add verification tasks for NFR-003 (isolation assertion in pipeline integration tests) and SM3 (timing measurement). |
| F04 | E. Coverage | MEDIUM | T023–T026 (Pipeline) | Plan §4 Phase 3 states the shell function is "tested via existing `test_markdownlint_validation.sh` harness" but no task creates or modifies that harness to exercise `run_line_wrapping`. | Add a task to extend or create a shell test that sources `generate-spec-from-issue.sh` and validates `run_line_wrapping` behavior. |
| F05 | F. Inconsistency | MEDIUM | Plan §4 Phase 1 (tokenize tests), T012, Spec FR-009/FR-010 | Plan and T012 mention "image link preservation" as a test case, but the spec never lists image links (`![alt](url)`) as a protected/unsplittable token in any FR or EC. | Either add an FR for image link protection or remove image link references from plan and T012 to match spec scope. |
| F06 | B. Ambiguity | MEDIUM | FR-012, T024 | "Log the file path and count of wrapped lines" — does not specify log destination (stdout, stderr, or `logging` module), log level, or structured format. Plan says `[Line Wrap]` prefix but the FR does not. | Clarify FR-012 to specify log destination (stderr for CLI, stdout for pipeline) and format pattern. |
| F07 | A. Duplication | MEDIUM | EC4 ↔ FR-016, EC7 ↔ FR-017, EC8 ↔ FR-002 | EC4, EC7, and EC8 restate requirements already fully specified in FR-016, FR-017, and FR-002 respectively, with no additional behavioral detail. | Mark these ECs as "See FR-0xx" cross-references rather than restating the same rule, or merge them into the FR text as examples. |
| F08 | A. Duplication | LOW | Spec §4 assumption #4 ↔ EC2, assumption #6 ↔ FR-002 | Assumption 4 restates EC2 (single long words left as-is). Assumption 6 restates FR-002 (whitespace-only split points). | Consolidate into a single authoritative location; reference from the other. |
| F09 | C. Underspecification | MEDIUM | FR-015 | "One or more file paths or a glob pattern" — does not specify whether recursive globs (`**/*.md`) are supported, whether directory arguments are accepted, or behavior when no files match. | Specify supported glob syntax, whether directories are recursed, and error behavior for zero matches (exit code, message). |
| F10 | C. Underspecification | MEDIUM | FR-007 | "Preserve the original list indentation level" — does not define alignment behavior for different list marker types (`-`, `*`, `1.`, `10.`) which have different prefix widths. | Add examples showing continuation indent for single-char markers vs. multi-digit ordered list markers. |
| F11 | C. Underspecification | MEDIUM | Spec §7–§9 | No requirement addresses error handling for file I/O failures (permission denied, file not found, encoding errors) or partial-write rollback during in-place modification. | Add an FR or NFR defining error behavior: skip files with errors, exit non-zero, write to temp file then rename for atomicity. |
| F12 | C. Underspecification | LOW | Spec §5–§7 | No requirement specifies expected file encoding. UTF-8 is implied but never stated. | Add a brief assumption or NFR specifying UTF-8 encoding for all input/output. |
| F13 | B. Ambiguity | MEDIUM | US4 AC1, SM2 | "At least 90% reduction in MD013 violations compared to the baseline without wrapping" — baseline measurement methodology is undefined. Which files? Measured when? | Define baseline: e.g., "measured against the same generated output before the wrap step is applied, on the current `specs/` directory contents." |
| F14 | B. Ambiguity | LOW | T027, T028 | "Sample spec files from `specs/`" and "files that previously required LLM remediation" are unspecified — verification tasks lack concrete test inputs. | Name specific files or define selection criteria for the verification samples. |
| F15 | F. Inconsistency | LOW | Plan phases ↔ Task phases | Plan defines 4 implementation phases; tasks define 8 phases with different naming and grouping. Phase numbering is not aligned. | Harmonize phase labels between plan and task list, or add a mapping table. |
| F16 | E. Coverage | LOW | NFR-002 | No task explicitly verifies that the implementation uses only stdlib. | Add a check (e.g., grep for non-stdlib imports in `line_wrapper.py`) to T036 or as a standalone task. |
| F17 | F. Inconsistency | LOW | Plan §4 Phase 3, T023 | Plan says function is "best-effort (returns 0 always)" but no FR, task, or test captures this requirement. | Add a test or acceptance criterion verifying `run_line_wrapping` returns 0 even on wrapper failure. |
| F18 | C. Underspecification | LOW | FR-004 | "Table rows (lines matching `\| ... \|` pipe-delimited format)" — does not clarify whether separator rows (`\|---\|---\|`) and incomplete table rows (missing trailing pipe) are also protected. | Specify that any line starting with `\|` and containing at least one interior `\|` is protected, including separator rows. |
| F19 | A. Duplication | LOW | Spec §4 assumption #7 ↔ FR-018 | Assumption 7 restates FR-018 (inline formatting spans not unsplittable). | Consolidate; assumption should reference FR-018. |
| F20 | D. Constitution | LOW | Spec §1–§10 | No explicit "Error Handling" or "Failure Modes" section. While individual ECs address some edge cases, systematic failure behavior (I/O errors, invalid input) is absent. | Add a section or subsection for error handling strategy. |

## 2. Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T017, T018 | |
| FR-002 | ✅ | T012, T014, T015, T016 | |
| FR-003 | ✅ | T009, T010 | |
| FR-004 | ✅ | T009, T010 | Table row definition slightly underspecified (F18) |
| FR-005 | ✅ | T009, T010 | |
| FR-006 | ✅ | T009, T010 | |
| FR-007 | ✅ | T011, T013 | Alignment behavior underspecified for varying marker widths (F10) |
| FR-008 | ✅ | T011, T013 | |
| FR-009 | ✅ | T012, T014 | |
| FR-010 | ✅ | T012, T014 | |
| FR-011 | ✅ | T025, T026 | |
| FR-012 | ✅ | T019, T020, T024 | Log format ambiguous (F06) |
| FR-013 | ✅ | T017, T019 | |
| FR-014 | ✅ | T029, T030 | |
| FR-015 | ✅ | T029, T030 | Glob scope underspecified (F09) |
| FR-016 | ✅ | T009, T010 | |
| FR-017 | ✅ | T009, T010 | |
| FR-018 | ✅ | T012 | |
| FR-019 | ✅ | T019, T020, T029, T030 | |
| FR-020 | ✅ | T019, T020, T029, T030 | |
| FR-021 | ✅ | T002 | |
| FR-022 | ✅ | T030, T031, T032 | |
| NFR-001 | ❌ | — | No performance test task (F02) |
| NFR-002 | ❌ | — | No stdlib-only verification task (F16) |
| NFR-003 | ❌ | — | No directory isolation test (F03) |
| NFR-004 | ✅ | T017 | |
| NFR-005 | ✅ | T009–T029 (structural) | |
| SM1 | ✅ | T035, T036 | Indirect via full suite |
| SM2 | ✅ | T027 | Baseline undefined (F13) |
| SM3 | ❌ | — | No pipeline timing task (F03) |
| SM4 | ✅ | T035 | |

## 3. Metrics

| Metric | Value |
|--------|-------|
| Total Requirements | 31 (22 FR + 5 NFR + 4 SM) |
| Total Tasks | 38 (T001–T038) |
| Coverage % | **87.1%** (27/31 requirements have ≥1 mapped task) |
| Ambiguity Count | 3 (F06, F13, F14) |
| Duplication Count | 3 (F07, F08, F19) |
| Critical Issues Count | 0 |
| High Issues Count | 3 (F01, F02, F03) |
| Medium Issues Count | 8 |
| Low Issues Count | 9 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
