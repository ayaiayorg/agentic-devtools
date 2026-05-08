# Cross-Artifact Consistency & Quality Analysis

**Feature**: Restructure setup-dev-tools into modular .agdt-managed scripts (#1322)

---

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A-01 | A. Duplication | LOW | FR-009 / FR-010 | FR-009 and FR-010 describe identical fail-fast orchestration patterns differing only in which scripts are chained. Both are necessary (different scope), but their shared behavior should reference a common pattern. | Add a cross-reference note; no consolidation needed. Informational only. |
| B-01 | B. Ambiguity | MEDIUM | NFR-002 | "Complete within 30 seconds under normal conditions (excluding network latency)" — "normal conditions" is unmeasurable. No definition of CPU, disk speed, or artifact count bounds. | Define "normal conditions" (e.g., ≤50 artifacts in site-packages, SSD-backed filesystem) or remove the time bound in favor of "single-pass, no retry loops." |
| B-02 | B. Ambiguity | LOW | FR-005 | "based on the user's interactive tool selections" — the spec clarifies known candidates (cspell, ruff, markdownlint-cli2) but the plan's T022 says "wire tool selection prompts" without specifying the prompt UX (checkbox list? yes/no per tool? config file?). | Clarify in plan whether tool selection is interactive prompts, a config file, or CLI flags. |
| C-01 | C. Underspecification | MEDIUM | Edge Case: Concurrent runs | Spec requires atomic writes for concurrency safety. T042 tests concurrent writes, but no task implements the actual locking/atomic-write logic beyond T003's `atomic_write.py`. T003's description ("write-to-temp + rename") may be insufficient on Windows where `os.rename` fails if the target exists. | Specify that T003 must use `os.replace()` (atomic on all platforms) and document Windows NTFS atomicity guarantees. |
| C-02 | C. Underspecification | MEDIUM | FR-011 | `--foreground` flag is a no-op today. No task explicitly tests that unknown/future flags (e.g., `--background`) are rejected gracefully. The argument parser behavior for unrecognized flags is unspecified. | Add acceptance criterion: unrecognized flags produce a clear error, not silent ignoring. |
| C-03 | C. Underspecification | LOW | Edge Case: Syntax errors in customer scripts | Spec says orchestrator must "catch the failure" from `setup-repo-specific-dev-tools.py` syntax errors, but no task explicitly tests this edge case. | Add edge-case test to T027 or T028 for subprocess failure from a syntactically invalid customer script. |
| D-01 | D. Constitution Alignment | LOW | Plan | No explicit "Rollback Strategy" section in plan. If script generation partially fails (e.g., 3 of 5 scripts written), there's no defined recovery. | Add rollback notes: either all-or-nothing generation (stage in temp dir, then move) or document that re-running `agdt-setup` is the recovery. |
| E-01 | E. Coverage Gaps | MEDIUM | NFR-002 | NFR-002 (30-second performance bound) has no corresponding test task. No task validates execution time. | Add a performance smoke test or explicitly mark NFR-002 as "verified by manual testing only." |
| E-02 | E. Coverage Gaps | MEDIUM | NFR-003 | NFR-003 (idempotent byte-for-byte output) is mentioned in T019 description but has no dedicated test. T020 tests "managed scripts refreshed per run" but not byte-for-byte identity. | Add an explicit idempotency assertion in T020 or a separate test: run generation twice, assert file contents are identical. |
| E-03 | E. Coverage Gaps | MEDIUM | NFR-004 | NFR-004 (actionable error messages with script name/path) has no dedicated test task. Error message quality is implicitly tested but never explicitly asserted. | Add assertions in fail-fast tests (T027) that error output contains the failing script's name and path. |
| E-04 | E. Coverage Gaps | LOW | NFR-005 | NFR-005 (backward compat — old repos work until migrated) is covered by US4 tasks but no test verifies that a repo with *only* the old monolithic script continues to work *without* running `agdt-setup`. | Add a test that directly invokes a legacy `setup-dev-tools.py` and confirms it still functions standalone. |
| F-01 | F. Inconsistency | MEDIUM | Spec vs. Plan | Spec says "five scripts" in the architecture table, but Plan Phase 1–4 only generates four scripts via code; the fifth (`setup-repo-specific-dev-tools.py`) is a stub. Plan treats it as a generator (`repo_specific.py`) but it's customer-owned post-creation — terminology drifts between "generated" and "managed." | Clarify in plan that `repo_specific.py` generates only the initial stub; after creation, it's customer-owned and never regenerated. |
| F-02 | F. Inconsistency | LOW | Tasks T006–T010 vs. T011–T015 | Test tasks (T006–T010) test functions like `detect_corrupted_artifacts()`, `cleanup_artifacts()` as if they are separate Python functions, but T015 generates a *standalone script* (not importable functions). The test strategy implies unit-testing functions that only exist inside generated script content. | Clarify: either the functions are implemented as importable helpers (tested directly) and the generated script calls them, or the tests exercise the generated script via subprocess. The current framing is ambiguous. |
| G-01 | G. Task Deduplication | HIGH | T021, T034 | T021 implements the script generation phase in `commands.py`; T034 integrates legacy migration into the same script generation phase in `commands.py`. Both modify `agentic_devtools/cli/setup/commands.py` to add logic to the same phase. | Ensure T034 is scoped as an incremental addition to T021's work, not a parallel rewrite. Consider merging or making the dependency explicit. |
| G-02 | G. Task Deduplication | HIGH | T021, T040 | T021 implements the script generation phase in `commands.py`; T040 integrates the `.gitignore` updater into the same phase in `commands.py`. Both target the same function/file. | Same as G-01: make sequential dependency explicit. T040 should be a narrow addition to the phase built by T021. |
| G-03 | G. Task Deduplication | HIGH | T009, T035, T036 | T009 tests `setup_git_hooks()` "happy-path and failure scenarios"; T035 tests `setup_git_hooks()` in non-git context; T036 tests `setup_git_hooks()` warning on overwrite. T035 and T036 are subsets of what T009's "failure scenarios" could cover. | Clarify that T009 covers the core happy path, while T035/T036 are additional edge-case-only tests. Consider consolidating if T009 already covers these scenarios. |

---

### Category G Structured Findings

```json
[
  {
    "id": "G-01",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T021", "T034"],
    "dimensions": ["file_path", "code_section"],
    "rationale": "Both tasks modify agentic_devtools/cli/setup/commands.py, specifically the script generation phase at the end of setup_cmd(). T021 creates the phase; T034 adds legacy migration into the same phase. Risk of merge conflict or redundant scaffolding if worked in parallel."
  },
  {
    "id": "G-02",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T021", "T040"],
    "dimensions": ["file_path", "code_section"],
    "rationale": "Both tasks modify agentic_devtools/cli/setup/commands.py, specifically the script generation phase. T021 builds the phase; T040 adds .gitignore updater call into the same phase. Sequential execution required."
  },
  {
    "id": "G-03",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T009", "T035", "T036"],
    "dimensions": ["description", "code_section"],
    "rationale": "All three tasks test setup_git_hooks(). T009 covers 'happy-path and failure scenarios' broadly; T035 and T036 test specific failure/edge cases (non-git context, overwrite warning) that may overlap with T009's failure scenarios. Risk of duplicate test assertions."
  }
]
```

---

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T002, T006, T011, T016 | Covered with happy-path, negative, edge-case |
| FR-002 | ✅ | T007, T012, T016 | Covered with happy-path, negative, edge-case |
| FR-003 | ✅ | T008, T013 | Covered with happy-path, negative |
| FR-004 | ✅ | T009, T014, T035, T036, T037 | Extensive coverage including edge cases |
| FR-005 | ✅ | T017, T018, T019 | Covered |
| FR-006 | ✅ | T020, T021 | Covered |
| FR-007 | ✅ | T032, T033 | Covered (negative tests only — no happy-path) |
| FR-008 | ✅ | T032, T033 | Covered (negative tests only — no happy-path) |
| FR-009 | ✅ | T023, T025, T027 | Covered (negative/edge-case, no happy-path) |
| FR-010 | ✅ | T024, T026, T027, T028 | Covered (negative/edge-case, no happy-path) |
| FR-011 | ✅ | T025, T026, T045 | Covered |
| FR-012 | ✅ | T002, T010, T015, T043, T044 | Covered with stdlib validation |
| FR-013 | ✅ | T029, T030, T031, T034 | Covered (negative tests only — no happy-path) |
| FR-014 | ✅ | T038, T039, T040 | Covered |
| FR-015 | ✅ | T021, T041, T042, T046 | Covered with integration tests |
| NFR-001 | ✅ | T043, T044 | Cross-platform path tests |
| NFR-002 | ❌ | — | No performance test task |
| NFR-003 | ⚠️ | T019 (implicit) | Mentioned in T019 description but no dedicated assertion |
| NFR-004 | ❌ | — | No explicit error message quality test |
| NFR-005 | ⚠️ | T029–T034 (implicit) | Covered via US4 tasks but no standalone legacy-works-without-migration test |

---

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements | 20 (15 FR + 5 NFR) |
| Total Tasks | 47 |
| FR Coverage % | 100% (15/15) |
| Overall Coverage % (incl. NFR) | 85% (17/20) |
| Ambiguity Count | 2 (B-01, B-02) |
| Requirement Duplication Count (Category A) | 1 (A-01, informational) |
| Critical Issues Count | 0 |
| Task Deduplication Finding Count | 3 |
| Task Deduplication by Type | duplicate: 0 / overlapping: 3 / conflicting: 0 |
| Multi-Task Group Count | 1 (G-03 involves 3 tasks) |

---
*Generated by Copilot SDK (claude-opus-4.6)*
