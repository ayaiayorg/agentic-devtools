# Tasks: Fix Agent Assignment Token in speckit-implement-trigger Workflow

**Feature**: GitHub Issue #1759 — Fix silent failure of Copilot coding agent assignment  
**Target file**: `.github/workflows/speckit-implement-trigger.yml`

---

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Branch setup and baseline validation (no direct plan equivalent) |
| Phase 2: Foundational | Phase 1: Add Preflight Token Validation Step | Preflight step insertion (FR-002, US2) |
| Phase 3: User Story 1 | Phase 2: Fix Agent Assignment Step Authentication; Phase 3: Add Elevated Token to Downstream Steps | Assignment step auth fix and downstream token propagation (FR-001/004/005/006/007, US1) |
| Phase 4: User Story 3 | Phase 2 (partial — FR-003 logging) | Token identity logging in assignment step (FR-003, US3) |
| Phase 5: Polish & Cross-Cutting | Phase 4: Validation & Testing | YAML lint, constraint checks, FR-level verification |

---

## Phase 1: Setup

- [ ] T001 Create feature branch `fix/1759-agent-assignment-token` from main if not already present
- [ ] T002 [US2] Verify current workflow YAML parses cleanly with `actionlint` or YAML linter before modifications in `.github/workflows/speckit-implement-trigger.yml`

---

## Phase 2: Foundational — Preflight Token Validation (FR-002)

- [ ] T003 [US2] Insert new step `Validate Agent Assignment Token` (id: `validate-token`) before the "Assign Copilot Coding Agent" step (before line 381) in
  `.github/workflows/speckit-implement-trigger.yml` — shell `run:` step that checks `SPECKIT_PR_TOKEN` and `COPILOT_GITHUB_TOKEN` env vars (FR-002)
- [ ] T004 [US2] Add `if:` condition to preflight step matching existing gate: `steps.discover.outputs.found == 'true' && steps.check-pr.outputs.exists != 'true'` in
  `.github/workflows/speckit-implement-trigger.yml`
- [ ] T005 [US2] Implement `::error::` annotation output when neither token is configured, naming both required secrets and exiting with code 1 (FR-002, NFR-003) in
  `.github/workflows/speckit-implement-trigger.yml`
- [ ] T006 [US2] Output `token_identity` to `$GITHUB_OUTPUT` for downstream logging consumption in `.github/workflows/speckit-implement-trigger.yml`

---

## Phase 3: User Story 1 — Automatic Agent Assignment (P1)

- [ ] T007 [US1] Add `github-token: ${{ secrets.SPECKIT_PR_TOKEN || secrets.COPILOT_GITHUB_TOKEN }}` to the `with:` block of "Assign Copilot Coding Agent" step (FR-001) in
  `.github/workflows/speckit-implement-trigger.yml`
- [ ] T008 [US1] Add `if:` dependency on preflight step success (`steps.validate-token.outcome == 'success'`) to the assignment step's condition (FR-006 preserved, preflight gate added) in
  `.github/workflows/speckit-implement-trigger.yml`
- [ ] T009 [US1] Add response validation: check HTTP status and verify `response.data.agent_assignment` is non-null; emit `::warning::` and set `assigned` output to `'false'` when null/absent (FR-004)
  in `.github/workflows/speckit-implement-trigger.yml`
- [ ] T010 [US1] Add error handling for 404 (non-fatal skip with log, `assigned='false'`), 401 (fail with actionable message), and other non-2xx (fail with status and body) (FR-004) in
  `.github/workflows/speckit-implement-trigger.yml`
- [ ] T011 [US1] Preserve all existing assignment parameters unchanged: `custom_agent`, `base_branch`, `custom_instructions`, `model` (FR-005) in `.github/workflows/speckit-implement-trigger.yml`
- [ ] T012 [US1] Add `github-token: ${{ secrets.SPECKIT_PR_TOKEN || secrets.COPILOT_GITHUB_TOKEN }}` to the "Update Labels" step `with:` block (FR-007) in
  `.github/workflows/speckit-implement-trigger.yml`
- [ ] T013 [US1] Add `github-token: ${{ secrets.SPECKIT_PR_TOKEN || secrets.COPILOT_GITHUB_TOKEN }}` to the "Post Implementation Triggered Comment" step `with:` block (FR-007) in
  `.github/workflows/speckit-implement-trigger.yml`

---

## Phase 4: User Story 3 — Assignment Identity Logging (P3)

- [ ] T014 [US3] Add token identity logging line (`console.log`) reading from `steps.validate-token.outputs.token_identity` before the API call in the assignment step script (FR-003) in
  `.github/workflows/speckit-implement-trigger.yml`

---

## Phase 5: Polish & Cross-Cutting

- [ ] T015 [US1] Validate final workflow YAML with `actionlint` to confirm no syntax or indentation errors in `.github/workflows/speckit-implement-trigger.yml` (FR-001, FR-002)
- [ ] T016 [US1] Verify `permissions` block remains unchanged (NFR-004, FR-006) — no additions or removals in `.github/workflows/speckit-implement-trigger.yml`
- [ ] T017 [US1] Verify no other workflow files were modified (NFR-004) — `git diff --name-only` shows only `.github/workflows/speckit-implement-trigger.yml`
- [ ] T018 [US1] Verify `github-token` input in the "Assign Copilot Coding Agent" step uses the pattern `${{ secrets.SPECKIT_PR_TOKEN || secrets.COPILOT_GITHUB_TOKEN }}` (FR-001)
- [ ] T019 [US3] Verify token identity log line (`console.log`) referencing `steps.validate-token.outputs.token_identity` appears before the `github.request()` call in the assignment step script
  (FR-003)
- [ ] T020 [US1] Verify all existing assignment parameters (`custom_agent`, `base_branch`, `custom_instructions`, `model`) remain present and unchanged in the assignment step after modifications
  (FR-005)
- [ ] T021 [US1] Verify original `if:` condition (`steps.discover.outputs.found == 'true' && steps.check-pr.outputs.exists != 'true'`) is preserved on the assignment step
  alongside the new preflight gate (FR-006)
- [ ] T022 [US1] Verify "Update Labels" step and "Post Implementation Triggered Comment" step each have
  `github-token: ${{ secrets.SPECKIT_PR_TOKEN || secrets.COPILOT_GITHUB_TOKEN }}` in their `with:` blocks (FR-007)
- [ ] T023 Perform rubber duck review of all changes against FR-001 through FR-007 and NFR-001 through NFR-005 (NFR-005)
- [ ] T024 [US1] Happy-path end-to-end smoke test: in a test repository with `SPECKIT_PR_TOKEN` configured, trigger the
  `speckit-implement-trigger.yml` workflow against a phase 5 spec PR merge event and verify (end-to-end) that the originating
  issue receives a Copilot coding agent assignment with `assigned=true`, all existing assignment parameters preserved, the
  preflight step passing, and the token identity log line emitted before the API call (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007)
- [ ] T025 [US2] Negative-path preflight failure test: in a test repository where neither `SPECKIT_PR_TOKEN` nor
  `COPILOT_GITHUB_TOKEN` is configured, trigger the implementation workflow and verify the preflight validation step fails
  with a `::error::` annotation naming both required secrets, and the assignment step is skipped (FR-002)

---

## Dependency Graph

```text
T001 → T002 → T003 → T004 → T005 → T006 → T007
                                              ↓
                                    T008 → T009 → T010 → T011
                                              ↓
                                    T012 (P) ──┐
                                    T013 (P) ──┤
                                    T014       ─┤
                                               ↓
                                    T015 → T016 → T017 → T018 → T019 → T020 → T021 → T022 → T023 → T024 → T025
```

**Notes**:

- T012, T013 are parallelizable (modify independent steps in same file)
- T007–T011 are sequential (modify same step block incrementally)
- T015–T023 are sequential validation gates
- T024 is the happy-path e2e smoke test (requires a configured test environment)
- T025 is the negative-path preflight test (requires secrets to be temporarily removed)

---
*Generated by Copilot SDK (claude-opus-4.6)*
