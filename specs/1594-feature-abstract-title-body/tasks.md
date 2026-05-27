# Tasks: Abstract PR Title/Body Change Event Filtering as a Provider-Agnostic Guard

**Feature**: #1594 — Provider-agnostic edit-relevance guard for PR title/body/base change events  
**Spec**: `specs/1594-feature-abstract-title-body/spec.md`

---

## Phase 1: Setup

- [ ] T001 Create test directory structure for new guard tests

  ```bash
  mkdir -p tests/unit/cli/ci/guards && touch tests/unit/cli/ci/guards/__init__.py
  ```

- [ ] T002 Ensure existing test directories have `__init__.py` files for `tests/unit/cli/ci/models/`, `tests/unit/cli/ci/github_provider/`, `tests/unit/cli/ci/ado_provider/`,
  `tests/unit/cli/ci/commands/`

---

## Phase 2: Foundational — Extend `EventPayload` Model

- [ ] T003 Add `title_changed: bool = False` field to `EventPayload` in `agentic_devtools/cli/ci/models.py` (FR-001)
- [ ] T004 Add `body_changed: bool = False` field to `EventPayload` in `agentic_devtools/cli/ci/models.py` (FR-001)
- [ ] T005 Add `base_changed: bool = False` field to `EventPayload` in `agentic_devtools/cli/ci/models.py` (FR-001)
- [ ] T006 Add `edit_changes_known: bool = False` field to `EventPayload` in `agentic_devtools/cli/ci/models.py` (FR-001)
- [ ] T007 Update `EventPayload` docstring to document all four new fields and their semantics (FR-001)
- [ ] T008 [P] Write tests for new `EventPayload` fields: construction with/without new fields, frozen enforcement, default values, backward compatibility in
  `tests/unit/cli/ci/models/test_eventpayload.py` (FR-001, NFR-002)

---

## Phase 3: User Story 1 & 2 — Edit-Relevance Guard Implementation (P1)

- [ ] T009 [US1] [US2] Write failing tests for `check_edit_relevance` covering: non-edited action passes through (US3), edited+unknown metadata passes through, title change proceeds (US1), base change
  proceeds, body-only skips (US2), simultaneous title+body proceeds (FR-008), empty changes dict skips in `tests/unit/cli/ci/guards/test_check_edit_relevance.py`
- [ ] T010 [US1] [US2] Implement `check_edit_relevance(event: EventPayload) -> tuple[bool, str]` in `agentic_devtools/cli/ci/guards.py` — returns `(True, reason)` to skip when `action=="edited"` AND
  `edit_changes_known=True` AND `title_changed=False` AND `base_changed=False`; returns `(False, "")` otherwise (FR-004, FR-005, FR-008)
- [ ] T011 [US2] Ensure `check_edit_relevance` reason string matches format "edited event with no title or base change" for body-only/non-title edits (FR-005)
- [ ] T012 [US1] [US2] Verify all test branches pass for `check_edit_relevance` — confirm 100% line and branch coverage

---

## Phase 4: User Story 1 & 2 — GitHub Provider Changes (P1)

- [ ] T013 [P] [US1] Write failing tests for GitHub provider `_parse_pull_request_event()` with edited event payloads containing `changes.title`, `changes.body`, `changes.base`, empty changes, no
  changes key, and non-edited action in `tests/unit/cli/ci/github_provider/test_parse_event.py` (FR-002)
- [ ] T014 [US1] Modify `_parse_pull_request_event()` in `agentic_devtools/cli/ci/github_provider.py` to set `edit_changes_known=True` when `action=="edited"` and `"changes"` key is present in raw
  payload (FR-002)
- [ ] T015 [US1] Set `title_changed = "title" in changes_dict` when conditions from T014 are met (FR-002)
- [ ] T016 [US2] Set `body_changed = "body" in changes_dict` when conditions from T014 are met (FR-002)
- [ ] T017 [US1] Set `base_changed = "base" in changes_dict` when conditions from T014 are met (FR-002)
- [ ] T018 [US1] Pass new fields to `EventPayload` constructor in `_parse_pull_request_event()` (FR-002)
- [ ] T019 [US1] Verify all GitHub provider tests pass — confirm edited event metadata is correctly extracted

---

## Phase 5: User Story 1 & 2 — Wire Guard into Command Entry Point (P1)

- [ ] T020 [US1] [US2] Write failing tests for `ai_pr_loop_command()` in `tests/unit/cli/ci/commands/test_ai_pr_loop_command.py`: body-only edit exits 0 with INFO log (FR-006), title change proceeds
  to routing, non-edited event proceeds (FR-004)
- [ ] T021 [US1] [US2] Import `check_edit_relevance` from `guards` and `logging` in `agentic_devtools/cli/ci/commands.py` (FR-004)
- [ ] T022 [US1] [US2] Insert edit-relevance preflight between event parsing (line ~97) and v1/v2 routing (line ~103) in `ai_pr_loop_command()`: call `check_edit_relevance(event_payload)`, if
  `should_skip` then log INFO and `sys.exit(0)` (FR-004, FR-006)
- [ ] T023 [US2] Verify INFO log message includes PR number and skip reason matching format "PR #%d: %s" (FR-006, NFR-004)
- [ ] T024 [US1] [US2] Verify command-level tests confirm call ordering: parse → guard → route (FR-004, SC-004)

---

## Phase 6: User Story 3 — Non-Edited Events Pass Through (P2)

- [ ] T025 [P] [US3] Write tests verifying `check_edit_relevance` returns `(False, "")` for `action=opened`, `action=synchronize`, `action=labeled`, `action=ready_for_review` regardless of field
  values in `tests/unit/cli/ci/guards/test_check_edit_relevance.py`
- [ ] T026 [P] [US3] Write command-level test verifying non-edited events reach v1/v2 routing without guard interference in `tests/unit/cli/ci/commands/test_ai_pr_loop_command.py`

---

## Phase 7: User Story 4 — Azure DevOps Provider (P3)

- [ ] T027 [P] [US4] Write failing tests for ADO provider `parse_event()` with PR update payloads containing title change, description-only change, base-ref change, and missing metadata in
  `tests/unit/cli/ci/ado_provider/test_azuredevopsprovider.py` (FR-003)
- [ ] T028 [US4] Modify `AzureDevOpsProvider.parse_event()` in `agentic_devtools/cli/ci/ado_provider.py` to normalize `action` to `"edited"` for `git.pullrequest.updated` events (FR-003)
- [ ] T029 [US4] Set `edit_changes_known=True` when ADO payload structure reliably conveys field-level change metadata (FR-003)
- [ ] T030 [US4] Set `title_changed`, `body_changed`, `base_changed` based on ADO-specific resource fields (FR-003)
- [ ] T031 [US4] Ensure fail-open behavior: when metadata unavailable, keep all new fields at `False` defaults (FR-003)
- [ ] T032 [US4] Verify all ADO provider tests pass with 100% branch coverage on new logic

---

## Phase 8: Workflow YAML Update (Post-Release)

- [ ] T033 Add `edited` to `pull_request` event types in `.github/workflows/ai-pr-loop.yml` — change `types: [opened, reopened]` to `types: [opened, reopened, edited]` (FR-007)
- [ ] T034 Add inline YAML comment explaining PR edit filtering is handled in Python, not workflow-level `if:` conditions (FR-007, FR-009)

---

## Final Phase: Polish & Cross-Cutting

- [ ] T035 Add inline docstring to `check_edit_relevance` explaining guard purpose, return semantics, and relationship to FR-004/FR-005/FR-008 (FR-009)
- [ ] T036 Run full test suite (`agdt-test`) and verify zero regressions in existing tests (SC-005, SC-006)
- [ ] T037 Run `bash scripts/run-pr-checks.sh` to validate all CI-blocking checks pass
- [ ] T038 Verify backward compatibility: all existing `EventPayload` construction sites still work without new fields (NFR-002, SC-006)

---

## Dependency Graph

```text
T001, T002 → T003-T008 (setup before model changes)
T003-T007 → T008 (model fields before model tests)
T003-T007 → T009-T012 (model fields before guard impl)
T003-T007 → T013-T019 (model fields before provider changes)
T010 → T020-T024 (guard impl before wiring into command)
T014-T018 → T020-T024 (provider changes before command integration)
T009-T012 → T025-T026 (guard tests before pass-through tests)
T003-T007 → T027-T032 (model fields before ADO provider)
T020-T024 → T033-T034 (command wiring before YAML update)
T033-T034 gated on PyPI release of Phases 1-7
T035-T038 after all implementation phases complete
```

## FR Coverage Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T003, T004, T005, T006, T007, T008 |
| FR-002 | T013, T014, T015, T016, T017, T018 |
| FR-003 | T027, T028, T029, T030, T031 |
| FR-004 | T009, T010, T020, T021, T022, T024 |
| FR-005 | T010, T011 |
| FR-006 | T020, T022, T023 |
| FR-007 | T033, T034 |
| FR-008 | T009, T010 |
| FR-009 | T034, T035 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
