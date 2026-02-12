# Tasks: GitHub Action SpecKit Trigger

**Input**: Design documents from `/specs/002-github-action-speckit-trigger/`
**Prerequisites**: plan.md (required), spec.md (required for user stories),
research.md

**Tests**: Manual testing via issue creation; automated validation via
workflow syntax check and `act` (local GitHub Actions runner).

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and directory structure for the workflow

- [ ] T001 Create helper scripts directory structure at
    .github/scripts/speckit-trigger/
- [ ] T002 [P] Create workflow file skeleton at
    .github/workflows/speckit-issue-trigger.yml with event trigger and
    inputs
- [ ] T003 [P] Add workflow documentation section to README.md explaining
    the SpecKit trigger feature

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user
story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Implement assignee validation logic in
    .github/scripts/speckit-trigger/validate-assignee.sh
- [ ] T005 [P] Implement branch name sanitization in
    .github/scripts/speckit-trigger/sanitize-branch-name.sh
- [ ] T006 [P] Implement issue comment posting helper in
    .github/scripts/speckit-trigger/post-issue-comment.sh
- [ ] T007 Implement idempotency check (spec already exists) in
    .github/scripts/speckit-trigger/check-idempotency.sh
- [ ] T008 Create comment templates directory and markdown templates at
    .github/scripts/speckit-trigger/templates/
- [ ] T009 [P] Add started.md comment template at
    .github/scripts/speckit-trigger/templates/started.md
- [ ] T010 [P] Add completed.md comment template at
    .github/scripts/speckit-trigger/templates/completed.md
- [ ] T011 [P] Add failed.md comment template at
    .github/scripts/speckit-trigger/templates/failed.md
- [ ] T012 [P] Add already-processed.md comment template at
    .github/scripts/speckit-trigger/templates/already-processed.md

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Trigger SDD on Issue Assignment (Priority: P1) 🎯 MVP

**Goal**: Automatically start the SDD process when an issue is assigned to
the SpecKit agent

**Independent Test**: Create a GitHub issue, assign it to `speckit-agent`,
and verify that a spec.md is generated

### Validation for User Story 1

- [ ] T013 [US1] Validate workflow YAML syntax with `actionlint` or
    GitHub's workflow validator
- [ ] T014 [US1] Create test issue template for manual validation at
    .github/ISSUE_TEMPLATE/speckit-test.md

### Implementation for User Story 1

- [ ] T015 [US1] Add checkout step to workflow in
    .github/workflows/speckit-issue-trigger.yml
- [ ] T016 [US1] Add assignee validation job/step using
    validate-assignee.sh in .github/workflows/speckit-issue-trigger.yml
- [ ] T017 [US1] Add job condition to skip workflow when assignee doesn't
    match in .github/workflows/speckit-issue-trigger.yml
- [ ] T018 [US1] Implement spec generation script at
    .github/scripts/speckit-trigger/generate-spec-from-issue.sh
- [ ] T019 [US1] Integrate existing create-new-feature.sh script call in
    generate-spec-from-issue.sh
- [ ] T020 [US1] Add issue content extraction (title, body) to
    generate-spec-from-issue.sh
- [ ] T021 [US1] Add source issue reference injection to generated spec.md
    in generate-spec-from-issue.sh
- [ ] T022 [US1] Add spec generation step to workflow calling
    generate-spec-from-issue.sh in
    .github/workflows/speckit-issue-trigger.yml
- [ ] T023 [US1] Add git commit step for generated spec files in
    .github/workflows/speckit-issue-trigger.yml
- [ ] T024 [US1] Add error handling for spec generation failures in
    .github/workflows/speckit-issue-trigger.yml

**Checkpoint**: US1 is independently testable - assigning an issue to
speckit-agent creates a spec

---

## Phase 4: User Story 2 - Configurable Agent Assignment (Priority: P2)

**Goal**: Allow administrators to configure which GitHub users trigger the
SDD process

**Independent Test**: Modify workflow input to use a different assignee
and verify only that assignee triggers

### Validation for User Story 2

- [ ] T025 [US2] Test workflow with single custom assignee
    configuration
- [ ] T026 [US2] Test workflow with multiple assignees (comma-separated
    list)

### Implementation for User Story 2

- [ ] T027 [US2] Add `speckit_assignees` input with default value to
    workflow inputs in .github/workflows/speckit-issue-trigger.yml
- [ ] T028 [US2] Update validate-assignee.sh to accept assignee list as
    parameter
- [ ] T029 [US2] Implement comma-separated assignee parsing in
    validate-assignee.sh
- [ ] T030 [US2] Pass workflow input to validation script in
    .github/workflows/speckit-issue-trigger.yml
- [ ] T031 [US2] Document configuration options in README.md workflow
    section

**Checkpoint**: US2 complete - administrators can configure trigger
assignees

---

## Phase 5: User Story 3 - Spec Creation Feedback via Issue Comment (Priority: P2)

**Goal**: Post status comments to the originating GitHub issue during the
SDD process

**Independent Test**: Trigger SDD and verify comments appear for started,
completed, and failed states

### Validation for User Story 3

- [ ] T032 [US3] Test "started" comment is posted within 30 seconds of
    assignment
- [ ] T033 [US3] Test "completed" comment includes link to spec file
- [ ] T034 [US3] Test "failed" comment includes error details and
    resolution steps

### Implementation for User Story 3

- [ ] T035 [US3] Add `comment_on_issue` input with default `true` to
    workflow in .github/workflows/speckit-issue-trigger.yml
- [ ] T036 [US3] Add "started" comment step using actions/github-script in
    .github/workflows/speckit-issue-trigger.yml
- [ ] T037 [US3] Place "started" comment as first step after assignee
    validation for <30s response
- [ ] T038 [US3] Add "completed" comment step with spec file link in
    .github/workflows/speckit-issue-trigger.yml
- [ ] T039 [US3] Add "failed" comment step with error details in
    .github/workflows/speckit-issue-trigger.yml
- [ ] T040 [US3] Add conditional logic to skip comments when
    `comment_on_issue` is false
- [ ] T041 [US3] Add `speckit:processing` label during execution in
    .github/workflows/speckit-issue-trigger.yml
- [ ] T042 [US3] Replace label with `speckit:completed` or
    `speckit:failed` on finish

**Checkpoint**: US3 complete - issue thread shows full status of spec
creation

---

## Phase 6: User Story 4 - Automatic Spec Branch and PR Creation (Priority: P3)

**Goal**: Create a feature branch and pull request with the generated
specification

**Independent Test**: Trigger SDD and verify a new branch exists with spec
files and a PR is opened

### Validation for User Story 4

- [ ] T043 [US4] Test branch creation with correct naming convention
    (NNN-feature-name)
- [ ] T044 [US4] Test PR is created with structured description
- [ ] T045 [US4] Test issue labels are copied to PR

### Implementation for User Story 4

- [ ] T046 [US4] Add `create_branch` input with default `true` to workflow
    in .github/workflows/speckit-issue-trigger.yml
- [ ] T047 [US4] Add `create_pr` input with default `true` to workflow in
    .github/workflows/speckit-issue-trigger.yml
- [ ] T048 [US4] Add `base_branch` input with default `main` to workflow
    in .github/workflows/speckit-issue-trigger.yml
- [ ] T049 [US4] Add branch push step using git push in
    .github/workflows/speckit-issue-trigger.yml
- [ ] T050 [US4] Implement PR creation script at
    .github/scripts/speckit-trigger/create-spec-pr.sh
- [ ] T051 [US4] Add PR description template with spec summary and issue
    link in create-spec-pr.sh
- [ ] T052 [US4] Add label copying from issue to PR in create-spec-pr.sh
- [ ] T053 [US4] Add PR creation step to workflow calling
    create-spec-pr.sh
- [ ] T054 [US4] Add conditional logic to skip branch/PR when inputs are
    false
- [ ] T055 [US4] Update "completed" comment to include PR link when PR is
    created

**Checkpoint**: US4 complete - spec generation creates branch and PR
automatically

---

## Phase 7: User Story 5 - Issue-to-Spec Linking (Priority: P3)

**Goal**: Link generated specifications back to the originating GitHub
issue

**Independent Test**: Verify spec.md contains Source Issue field with
issue number and URL

### Validation for User Story 5

- [ ] T056 [US5] Verify spec.md includes `Source Issue: #N` with correct
    issue number
- [ ] T057 [US5] Verify PR description includes `Relates to #N` linking

### Implementation for User Story 5

- [ ] T058 [US5] Add Source Issue metadata field to spec generation in
    generate-spec-from-issue.sh
- [ ] T059 [US5] Include issue URL in Source Issue field format
- [ ] T060 [US5] Add `Relates to #N` to PR description template in
    create-spec-pr.sh
- [ ] T061 [US5] Update spec template header to include Source Issue
    placeholder

**Checkpoint**: US5 complete - full traceability from issue to spec to
PR

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T062 [P] Add comprehensive workflow documentation to README.md
- [ ] T063 [P] Create CONTRIBUTING.md section for SpecKit trigger usage
- [ ] T064 Add retry logic with exponential backoff for AI API calls in
    generate-spec-from-issue.sh
- [ ] T065 [P] Add timeout handling (5 minute max) to workflow in
    .github/workflows/speckit-issue-trigger.yml
- [ ] T066 Add concurrency control to prevent parallel runs on same issue
    in .github/workflows/speckit-issue-trigger.yml
- [ ] T067 [P] Add workflow_dispatch trigger for manual testing in
    .github/workflows/speckit-issue-trigger.yml
- [ ] T068 Implement AI provider selection (claude/openai) in
    generate-spec-from-issue.sh
- [ ] T069 [P] Add `ai_provider` input with default `claude` to workflow
    inputs
- [ ] T070 [P] Document required repository secrets (ANTHROPIC_API_KEY,
    etc.) in README.md
- [ ] T071 Add edge case handling for empty issue body in
    generate-spec-from-issue.sh
- [ ] T072 Add edge case handling for special characters in issue title in
    sanitize-branch-name.sh
- [ ] T073 [P] Create example workflow usage in docs or README.md
- [ ] T074 Validate all scripts are executable (chmod +x) in workflow
    setup step

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all
  user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase
  completion
  - US1 (P1): Core trigger functionality - MVP
  - US2 (P2): Configurable assignees - builds on US1
  - US3 (P2): Issue comments - builds on US1
  - US4 (P3): Branch/PR creation - builds on US1
  - US5 (P3): Issue linking - builds on US1, enhances US4
- **Polish (Phase 8)**: Depends on all desired user stories being
  complete

### User Story Dependencies

```text
US1 (P1: Core Trigger)
 ├── US2 (P2: Configurable Assignees) - enhances US1
 ├── US3 (P2: Issue Comments) - enhances US1
 ├── US4 (P3: Branch/PR) - extends US1
 │    └── US5 (P3: Linking) - enhances US4
```

### Within Each User Story

- Validation tasks SHOULD be defined first (what to test)
- Implementation tasks follow validation definition
- Core implementation before integration points
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (templates)
- Comment templates (T009-T012) can all be created in parallel
- Within US1: T013/T014 validation tasks can run in parallel
- All Polish tasks marked [P] can run in parallel

---

## File Summary

### New Files to Create

| File | Phase | Description |
| ---- | ----- | ----------- |
| `.github/workflows/speckit-issue-trigger.yml` | P1 | Workflow |
| `.github/scripts/speckit-trigger/validate-assignee.sh` | P2 | Validation |
| `.github/scripts/speckit-trigger/sanitize-branch-name.sh` | P2 | Sanitize |
| `.github/scripts/speckit-trigger/post-issue-comment.sh` | P2 | Comment |
| `.github/scripts/speckit-trigger/check-idempotency.sh` | P2 | Idempotency |
| `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` | P3 | Gen |
| `.github/scripts/speckit-trigger/create-spec-pr.sh` | P6 | PR |
| `.github/scripts/speckit-trigger/templates/started.md` | P2 | Template |
| `.github/scripts/speckit-trigger/templates/completed.md` | P2 | Template |
| `.github/scripts/speckit-trigger/templates/failed.md` | P2 | Template |
| `.github/scripts/speckit-trigger/templates/already-processed.md` | P2 | Tpl |
| `.github/ISSUE_TEMPLATE/speckit-test.md` | P3 | Test tpl |

### Files to Modify

| File | Phase | Description |
| ---- | ----- | ----------- |
| `README.md` | P1, P4, P8 | Docs |

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T012)
3. Complete Phase 3: User Story 1 (T013-T024)
4. **STOP and VALIDATE**: Test by assigning an issue to `speckit-agent`
5. Deploy MVP if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test → Deploy (MVP!)
3. Add User Story 2 + 3 → Test → Deploy (Enhanced feedback)
4. Add User Story 4 + 5 → Test → Deploy (Full automation)
5. Polish phase for production readiness

### Recommended Order for Solo Developer

```text
T001 → T002 → T003 (Setup)
    ↓
T004 → T005 → T006 → T007 (Foundation core)
    ↓
T008 → T009/T010/T011/T012 (Templates - parallel)
    ↓
T015-T024 (US1 - MVP)
    ↓
T027-T031 (US2 - Configurability)
    ↓
T035-T042 (US3 - Feedback)
    ↓
T046-T055 (US4 - PR automation)
    ↓
T058-T061 (US5 - Linking)
    ↓
T062-T074 (Polish)
```

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All bash scripts must be executable (chmod +x)
- Test workflow locally with `act` before pushing to GitHub
