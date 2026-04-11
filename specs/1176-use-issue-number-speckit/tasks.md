# Tasks: Use Issue Number in SpecKit Directories

**Feature**: 1176-use-issue-number-speckit
**Source Issue**: #1176

## User Story Mapping

| Story | Description | Priority |
|-------|-------------|----------|
| US1 | ISSUE_NUMBER validation at script entry | P1 |
| US2 | Collision detection & directory reuse in CI pipeline | P1 |
| US3 | Autoincrement filter ignores issue-numbered directories (all scripts) | P1 |

### Task Markers

- **[P]** — Parallelizable: this task has no dependency on the preceding task and can be executed concurrently with other `[P]` tasks in the same phase.

### Plan ↔ Tasks Phase Crosswalk

| Tasks Phase | Plan Phase(s) | Description |
|-------------|---------------|-------------|
| Phase 1: Setup | — (prerequisite) | Read and understand baseline code |
| Phase 2: Foundational | Phase 4 (Testing) | Autoincrement filter test infrastructure |
| Phase 3: US1 | Phase 1a | ISSUE_NUMBER validation |
| Phase 4: US2 | Phase 1b | Collision detection & directory reuse |
| Phase 5: US3 | Phase 1c, 2, 3 | Autoincrement filter fixes (all scripts) |
| Phase 6: Polish | Phase 4, 5 | Documentation, integration testing, workflow idempotency, helper compat |

---

## Phase 1: Setup

- [ ] T001 Read and understand current regex patterns in all three target scripts to confirm baseline bugs match plan

---

## Phase 2: Foundational — Autoincrement Filter Test Infrastructure

- [ ] T002 Create test script `.github/scripts/speckit-trigger/test-autoincrement-filter.sh` with helper functions for temp directory setup/teardown and assertion utilities
- [ ] T003 Add test cases to `test-autoincrement-filter.sh` for Bash `get_highest_from_specs` verifying `42-bar` is ignored and `001-foo` / `002-baz` are counted (expected highest = 2)
- [ ] T004 Add test cases to `test-autoincrement-filter.sh` for Bash `get_highest_from_branches` verifying non-3-digit branch prefixes like `99-bar` are ignored

---

## Phase 3: US1 — ISSUE_NUMBER Validation (P1)

- [ ] T005 [US1] Add test case in `test-autoincrement-filter.sh` for ISSUE_NUMBER validation:
  positive integer accepted, `0` rejected, `abc` rejected, empty rejected, `-1` rejected, `042` rejected (leading zero)
- [ ] T006 [US1] Add ISSUE_NUMBER validation (`^[1-9][0-9]*$`) in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` immediately after the existing `${ISSUE_NUMBER:?}` check
- [ ] T007 [US1] Run validation test cases from T005 to confirm all pass

---

## Phase 4: US2 — Collision Detection & Directory Reuse (P1)

- [ ] T008 [US2] Add test cases in `test-autoincrement-filter.sh` for collision detection: existing `42-old-name` dir is reused when ISSUE_NUMBER=42, no new dir created
- [ ] T009 [US2] Add test case for re-run with changed title: existing `42-old-name` is reused even when SHORT_NAME differs (FR-012)
- [ ] T010 [US2] Add test case for no collision: ISSUE_NUMBER=42 with no existing `42-*` dir creates new `42-short-name`
- [ ] T010a [US2] Add edge-case test for 3-digit issue-number overlap with legacy namespace:
  existing `117-legacy-feature` directory (no matching `**Source Issue**: #117` in `checklists/requirements.md` or `spec.md`) + `ISSUE_NUMBER=117`;
  verify the script fails fast rather than reusing the unrelated legacy directory (FR-015)
- [ ] T010b [US2] Add edge-case test for 3-digit issue-number safe reuse:
  existing `117-some-issue` directory (with matching `**Source Issue**: #117` in `checklists/requirements.md`) + `ISSUE_NUMBER=117`;
  verify the script correctly reuses the directory (FR-015)
- [ ] T011 [US2] Implement collision detection in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` —
  add glob scan for `${ISSUE_NUMBER}-*` (raw, unpadded) after `BRANCH_NAME` is computed,
  before the `SPEC_DIR` assignment
- [ ] T011a [US2] Implement Source Issue verification guard for 3-digit issue numbers (FR-015):
  when a candidate directory is found and `ISSUE_NUMBER` has exactly 3 digits, check
  `checklists/requirements.md` first (deterministic), then fall back to `spec.md` (tolerant regex);
  fail fast if neither artifact contains `**Source Issue**: #N` matching the current issue
- [ ] T012 [US2] Add directory reuse logic: when `EXISTING_DIR` is found, set `SPEC_DIR` and `BRANCH_NAME`
  from existing dir; otherwise create new `${ISSUE_NUMBER}-${SHORT_NAME}` directory (raw, unpadded issue number)
- [ ] T013 [US2] Ensure `SPEC_FILE` output variable also reflects the reused directory path (verify `SPEC_FILE` is derived from `SPEC_DIR`)
- [ ] T014 [US2] Run collision detection test cases from T008–T010b to confirm all pass

---

## Phase 5: US3 — Autoincrement Filter Fix (P1)

### 5a: `generate-spec-from-issue.sh` — spec directory scan

- [ ] T015 [US3] Fix autoincrement regex in `get_next_feature_number` in
  `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` (inside the spec directory scan loop):
  change `grep -o '^[0-9]\+'` to filter `^[0-9]\{3\}-` with continue, then extract `^[0-9]\{3\}` with `10#$number` base-10 conversion
- [ ] T016 [US3] Add test case: specs dir has `001-foo`, `002-bar`, `42-issue` → `get_next_feature_number` returns 3 (ignores `42-issue`)

### 5b: `create-new-feature.sh` — spec directory scan

- [ ] T017 [P] [US3] Fix autoincrement regex in `get_highest_from_specs` in
  `.specify/scripts/bash/create-new-feature.sh` (inside the spec directory scan loop):
  change `grep -o '^[0-9]\+'` to filter `^[0-9]\{3\}-` with continue, then extract `^[0-9]\{3\}` with `10#$number` base-10 conversion
- [ ] T018 [P] [US3] Verify `get_highest_from_branches` in `.specify/scripts/bash/create-new-feature.sh`
  already correctly uses `^[0-9]\{3\}-` — no change needed, document as confirmed

### 5c: `create-new-feature.ps1` — both functions

- [ ] T019 [P] [US3] Fix `Get-HighestNumberFromSpecs` regex in `.specify/scripts/powershell/create-new-feature.ps1` (in the `Get-HighestNumberFromSpecs` function): change `'^(\d+)'` to `'^(\d{3})-'`
- [ ] T020 [P] [US3] Fix `Get-HighestNumberFromBranches` regex in `.specify/scripts/powershell/create-new-feature.ps1` (in the `Get-HighestNumberFromBranches` function): change `'^(\d+)-'` to `'^(\d{3})-'`

### 5d: Verification

- [ ] T021 [US3] Run autoincrement filter test cases from T003, T004, T016 to confirm all three scripts correctly ignore non-3-digit prefixes
- [ ] T022 [US3] Manual verification: confirm existing `specs/` directory contents (all 3-digit prefixed) still produce correct next number

---

## Phase 6: Polish & Cross-Cutting

### Documentation

- [ ] T023 [P] Update `specs/README.md` — add section documenting issue-numbered directories (`<ISSUE_NUMBER>-<slug>` from raw issue number, unpadded)
  vs autoincrement directories, and that autoincrement ignores issue-numbered dirs
- [ ] T024 [P] Update `SPEC_DRIVEN_DEVELOPMENT.md` — document the CI pipeline directory naming convention
  for issue-driven directories (`<ISSUE_NUMBER>-<slug>` using the raw unpadded issue number)
  and ISSUE_NUMBER validation rules
- [ ] T025 [P] Add inline comments in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` referencing FR-011, FR-004, FR-007, FR-012 at each modification site

### Integration testing

- [ ] T026 Run full manual test matrix from plan Phase 4a (8 test cases) covering all three scripts
- [ ] T027 Verify `check-idempotency.sh` continues to work correctly with issue-numbered directories (no changes needed to that script, but verify no regressions)
- [ ] T028 Verify the existing `specs/1176-use-issue-number-speckit/` directory is correctly ignored by autoincrement in all three scripts (real-world validation with actual repo contents)

### Workflow idempotency

- [ ] T029 [P] Update `speckit-issue-trigger.yml` "Commit Planning Artifacts" step to handle existing
  remote branches: detect whether `origin/$BRANCH_NAME` already exists, and if so check out and reset
  the existing branch instead of `git checkout -b` (which fails when the branch exists)
- [ ] T030 [P] Update `speckit-issue-trigger.yml` "Push Branch" step to use `git push --force-with-lease`
  (or equivalent) so reruns can update the remote branch instead of failing with a non-fast-forward error
- [ ] T031 [P] Add test case to `test-autoincrement-filter.sh` for workflow rerun idempotency:
  simulate an existing remote branch for the same issue and verify the workflow handles it gracefully

### `.specify` helper compatibility

- [ ] T032 [P] Update `check_feature_branch` in `.specify/scripts/bash/common.sh` to accept both
  legacy 3-digit prefixes (`^[0-9]{3}-`) and longer numeric issue-number prefixes (`^[0-9]+-`)
  so issue-number branches like `1176-...` are not rejected
- [ ] T033 [P] Update `find_feature_dir_by_prefix` in `.specify/scripts/bash/common.sh` to extract
  and match numeric prefixes of any length (not just exactly 3 digits) so issue-numbered spec
  directories are discoverable from issue-number branches

### Cleanup

- [ ] T034 Ensure `test-autoincrement-filter.sh` is executable (`chmod +x`) and has a shebang line
- [ ] T035 Final review: confirm no `grep -o '^[0-9]\+'` patterns remain in any of the three modified scripts

---

## Dependency Graph

```text
T001 ─→ T002 ─→ T003, T004 (parallel)
                    │
         T005 ─→ T006 ─→ T007
                    │
    T008, T009, T010 ─→ T011 ─→ T012 ─→ T013 ─→ T014
                                            │
                              T015 ─→ T016 ─┤
                              T017 ──────────┤  (parallel with T019, T020)
                              T019 ──────────┤
                              T020 ──────────┤
                                             ↓
                                     T021 ─→ T022
                                             │
                              T023, T024, T025 (parallel)
                              T029, T030, T031 (parallel — workflow idempotency)
                              T032, T033 (parallel — .specify helper compat)
                                             │
                                     T026 ─→ T027 ─→ T028
                                             │
                                     T034 ─→ T035
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
