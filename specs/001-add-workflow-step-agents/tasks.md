# Tasks: Workflow Step Chat Prompts

**Input**: Design documents from `/specs/001-add-workflow-step-agents/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/agent-schema.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent
implementation. No tests are generated (no Python runtime changes; coverage
script serves as validation).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Establish the agent/prompt template pattern and directory awareness

- [x] T001 Create agent body template file at

  specs/001-add-workflow-step-agents/contracts/agent-body-template.md with the
  specs/001-add-workflow-step-agents/contracts/agent-body-template.md with the
  standard body structure (Purpose, Prerequisites, Actions, Expected Outcome,
  Next Step sections) from contracts/agent-schema.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared reference material that all agent files will rely on

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 Read existing Speckit agent files

  (.github/agents/speckit.specify.agent.md, speckit.plan.agent.md) and verify
  (.github/agents/speckit.specify.agent.md, speckit.plan.agent.md) and verify
  the template from T001 is structurally compatible with YAML frontmatter
  conventions and $ARGUMENTS pattern

- [x] T003 Read existing workflow prompt templates

  (agentic_devtools/prompts/work-on-jira-issue/, pull-request-review/) to
  (agentic_devtools/prompts/work-on-jira-issue/, pull-request-review/) to
  extract required state keys and CLI commands for each step (capture in
  data-model.md catalog)

**Checkpoint**: Template validated, step catalog confirmed — agent authoring can
begin

---

## Phase 3: User Story 1 – Start a workflow step from chat (Priority: P1) MVP

**Goal**: Every workflow step has a working agent + prompt pair so developers
can start any step from Copilot Chat.

**Independent Test**: Type `/agdt.work-on-jira-issue.planning` in Copilot Chat
and receive step-specific guidance with CLI commands.

### work-on-jira-issue agents (11 files)

- [x] T004 [P] [US1] Create agent at

  .github/agents/agdt.work-on-jira-issue.initiate.agent.md — description: "Work
  .github/agents/agdt.work-on-jira-issue.initiate.agent.md — description: "Work
  on Jira Issue – Initiate: Start working on a Jira issue (step 1 of 11)";
  required state: jira.issue_key; CLI:
  agdt-initiate-work-on-jira-issue-workflow; handoff → setup OR retrieve

- [x] T005 [P] [US1] Create agent at

  .github/agents/agdt.work-on-jira-issue.setup.agent.md — description: "Work on
  .github/agents/agdt.work-on-jira-issue.setup.agent.md — description: "Work on
  Jira Issue – Setup: Create worktree and branch (step 2 of 11)"; required
  state: jira.issue_key; CLI: agdt-setup-worktree-background; handoff → retrieve

- [x] T006 [P] [US1] Create agent at

  .github/agents/agdt.work-on-jira-issue.retrieve.agent.md — description: "Work
  .github/agents/agdt.work-on-jira-issue.retrieve.agent.md — description: "Work
  on Jira Issue – Retrieve: Fetch Jira issue details (step 3 of 11)"; required
  state: jira.issue_key; CLI: agdt-get-jira-issue; handoff → planning

- [x] T007 [P] [US1] Create agent at

  .github/agents/agdt.work-on-jira-issue.planning.agent.md — description: "Work
  .github/agents/agdt.work-on-jira-issue.planning.agent.md — description: "Work
  on Jira Issue – Planning: Analyze issue and post plan (step 4 of 11)";
  required state: jira.issue_key, jira.comment; CLI: agdt-add-jira-comment;
  handoff → checklist-creation

- [x] T008 [P] [US1] Create agent at

  .github/agents/agdt.work-on-jira-issue.checklist-creation.agent.md —
  .github/agents/agdt.work-on-jira-issue.checklist-creation.agent.md —
  description: "Work on Jira Issue – Checklist Creation: Create implementation
  checklist (step 5 of 11)"; required state: jira.issue_key; CLI:
  agdt-create-checklist; handoff → implementation

- [x] T009 [P] [US1] Create agent at

  .github/agents/agdt.work-on-jira-issue.implementation.agent.md — description:
  .github/agents/agdt.work-on-jira-issue.implementation.agent.md — description:
  "Work on Jira Issue – Implementation: Implement checklist items (step 6 of
  11)"; required state: jira.issue_key; CLI: agdt-update-checklist,
  agdt-git-save-work; handoff → implementation-review

- [x] T010 [P] [US1] Create agent at

  .github/agents/agdt.work-on-jira-issue.implementation-review.agent.md —
  .github/agents/agdt.work-on-jira-issue.implementation-review.agent.md —
  description: "Work on Jira Issue – Implementation Review: Review completed
  checklist (step 7 of 11)"; required state: jira.issue_key; CLI:
  agdt-advance-workflow; handoff → verification

- [x] T011 [P] [US1] Create agent at

  .github/agents/agdt.work-on-jira-issue.verification.agent.md — description:
  .github/agents/agdt.work-on-jira-issue.verification.agent.md — description:
  "Work on Jira Issue – Verification: Run tests and quality gates (step 8 of
  11)"; required state: jira.issue_key; CLI: agdt-test, agdt-advance-workflow;
  handoff → commit

- [x] T012 [P] [US1] Create agent at

  .github/agents/agdt.work-on-jira-issue.commit.agent.md — description: "Work on
  .github/agents/agdt.work-on-jira-issue.commit.agent.md — description: "Work on
  Jira Issue – Commit: Stage and commit changes (step 9 of 11)"; required state:
  commit_message; CLI: agdt-git-save-work; handoff → pull-request

- [x] T013 [P] [US1] Create agent at

  .github/agents/agdt.work-on-jira-issue.pull-request.agent.md — description:
  .github/agents/agdt.work-on-jira-issue.pull-request.agent.md — description:
  "Work on Jira Issue – Pull Request: Create a pull request (step 10 of 11)";
  required state: source_branch, title; CLI: agdt-create-pull-request; handoff →
  completion

- [x] T014 [P] [US1] Create agent at

  .github/agents/agdt.work-on-jira-issue.completion.agent.md — description:
  .github/agents/agdt.work-on-jira-issue.completion.agent.md — description:
  "Work on Jira Issue – Completion: Post final Jira comment (step 11 of 11)";
  required state: jira.issue_key, pull_request_id; CLI: agdt-add-jira-comment;
  no handoff

### work-on-jira-issue prompts (11 files)

- [x] T015 [P] [US1] Create prompt at

  .github/prompts/agdt.work-on-jira-issue.initiate.prompt.md — agent:
  .github/prompts/agdt.work-on-jira-issue.initiate.prompt.md — agent:
  agdt.work-on-jira-issue.initiate

- [x] T016 [P] [US1] Create prompt at

  .github/prompts/agdt.work-on-jira-issue.setup.prompt.md — agent:
  .github/prompts/agdt.work-on-jira-issue.setup.prompt.md — agent:
  agdt.work-on-jira-issue.setup

- [x] T017 [P] [US1] Create prompt at

  .github/prompts/agdt.work-on-jira-issue.retrieve.prompt.md — agent:
  .github/prompts/agdt.work-on-jira-issue.retrieve.prompt.md — agent:
  agdt.work-on-jira-issue.retrieve

- [x] T018 [P] [US1] Create prompt at

  .github/prompts/agdt.work-on-jira-issue.planning.prompt.md — agent:
  .github/prompts/agdt.work-on-jira-issue.planning.prompt.md — agent:
  agdt.work-on-jira-issue.planning

- [x] T019 [P] [US1] Create prompt at

  .github/prompts/agdt.work-on-jira-issue.checklist-creation.prompt.md — agent:
  .github/prompts/agdt.work-on-jira-issue.checklist-creation.prompt.md — agent:
  agdt.work-on-jira-issue.checklist-creation

- [x] T020 [P] [US1] Create prompt at

  .github/prompts/agdt.work-on-jira-issue.implementation.prompt.md — agent:
  .github/prompts/agdt.work-on-jira-issue.implementation.prompt.md — agent:
  agdt.work-on-jira-issue.implementation

- [x] T021 [P] [US1] Create prompt at

  .github/prompts/agdt.work-on-jira-issue.implementation-review.prompt.md —
  .github/prompts/agdt.work-on-jira-issue.implementation-review.prompt.md —
  agent: agdt.work-on-jira-issue.implementation-review

- [x] T022 [P] [US1] Create prompt at

  .github/prompts/agdt.work-on-jira-issue.verification.prompt.md — agent:
  .github/prompts/agdt.work-on-jira-issue.verification.prompt.md — agent:
  agdt.work-on-jira-issue.verification

- [x] T023 [P] [US1] Create prompt at

  .github/prompts/agdt.work-on-jira-issue.commit.prompt.md — agent:
  .github/prompts/agdt.work-on-jira-issue.commit.prompt.md — agent:
  agdt.work-on-jira-issue.commit

- [x] T024 [P] [US1] Create prompt at

  .github/prompts/agdt.work-on-jira-issue.pull-request.prompt.md — agent:
  .github/prompts/agdt.work-on-jira-issue.pull-request.prompt.md — agent:
  agdt.work-on-jira-issue.pull-request

- [x] T025 [P] [US1] Create prompt at

  .github/prompts/agdt.work-on-jira-issue.completion.prompt.md — agent:
  .github/prompts/agdt.work-on-jira-issue.completion.prompt.md — agent:
  agdt.work-on-jira-issue.completion

### pull-request-review agents (5 files)

- [x] T026 [P] [US1] Create agent at

  .github/agents/agdt.pull-request-review.initiate.agent.md — description: "PR
  .github/agents/agdt.pull-request-review.initiate.agent.md — description: "PR
  Review – Initiate: Start a pull request review (step 1 of 5)"; required state:
  pull_request_id OR jira.issue_key; CLI: agdt-review-pull-request; handoff →
  file-review

- [x] T027 [P] [US1] Create agent at

  .github/agents/agdt.pull-request-review.file-review.agent.md — description:
  .github/agents/agdt.pull-request-review.file-review.agent.md — description:
  "PR Review – File Review: Review individual files (step 2 of 5)"; required
  state: pull_request_id, file_review.file_path; CLI: agdt-approve-file,
  agdt-request-changes; handoff → file-review OR summary

- [x] T028 [P] [US1] Create agent at

  .github/agents/agdt.pull-request-review.summary.agent.md — description: "PR
  .github/agents/agdt.pull-request-review.summary.agent.md — description: "PR
  Review – Summary: Generate review summary (step 3 of 5)"; required state:
  pull_request_id; CLI: agdt-generate-pr-summary; handoff → decision

- [x] T029 [P] [US1] Create agent at

  .github/agents/agdt.pull-request-review.decision.agent.md — description: "PR
  .github/agents/agdt.pull-request-review.decision.agent.md — description: "PR
  Review – Decision: Approve or request changes (step 4 of 5)"; required state:
  pull_request_id; CLI: agdt-approve-pull-request; handoff → completion

- [x] T030 [P] [US1] Create agent at

  .github/agents/agdt.pull-request-review.completion.agent.md — description: "PR
  .github/agents/agdt.pull-request-review.completion.agent.md — description: "PR
  Review – Completion: Finalize review (step 5 of 5)"; required state:
  pull_request_id; CLI: agdt-add-jira-comment; no handoff

### pull-request-review prompts (5 files)

- [x] T031 [P] [US1] Create prompt at

  .github/prompts/agdt.pull-request-review.initiate.prompt.md — agent:
  .github/prompts/agdt.pull-request-review.initiate.prompt.md — agent:
  agdt.pull-request-review.initiate

- [x] T032 [P] [US1] Create prompt at

  .github/prompts/agdt.pull-request-review.file-review.prompt.md — agent:
  .github/prompts/agdt.pull-request-review.file-review.prompt.md — agent:
  agdt.pull-request-review.file-review

- [x] T033 [P] [US1] Create prompt at

  .github/prompts/agdt.pull-request-review.summary.prompt.md — agent:
  .github/prompts/agdt.pull-request-review.summary.prompt.md — agent:
  agdt.pull-request-review.summary

- [x] T034 [P] [US1] Create prompt at

  .github/prompts/agdt.pull-request-review.decision.prompt.md — agent:
  .github/prompts/agdt.pull-request-review.decision.prompt.md — agent:
  agdt.pull-request-review.decision

- [x] T035 [P] [US1] Create prompt at

  .github/prompts/agdt.pull-request-review.completion.prompt.md — agent:
  .github/prompts/agdt.pull-request-review.completion.prompt.md — agent:
  agdt.pull-request-review.completion

### Single-step workflow agents (5 files)

- [x] T036 [P] [US1] Create agent at

  .github/agents/agdt.create-jira-issue.initiate.agent.md — description: "Create
  .github/agents/agdt.create-jira-issue.initiate.agent.md — description: "Create
  Jira Issue – Initiate: Create a new Jira issue"; required state:
  jira.project_key; CLI: agdt-initiate-create-jira-issue-workflow; no handoff

- [x] T037 [P] [US1] Create agent at

  .github/agents/agdt.create-jira-epic.initiate.agent.md — description: "Create
  .github/agents/agdt.create-jira-epic.initiate.agent.md — description: "Create
  Jira Epic – Initiate: Create a new Jira epic"; required state:
  jira.project_key; CLI: agdt-initiate-create-jira-epic-workflow; no handoff

- [x] T038 [P] [US1] Create agent at

  .github/agents/agdt.create-jira-subtask.initiate.agent.md — description:
  .github/agents/agdt.create-jira-subtask.initiate.agent.md — description:
  "Create Jira Subtask – Initiate: Create a Jira subtask"; required state:
  jira.parent_key; CLI: agdt-initiate-create-jira-subtask-workflow; no handoff

- [x] T039 [P] [US1] Create agent at

  .github/agents/agdt.update-jira-issue.initiate.agent.md — description: "Update
  .github/agents/agdt.update-jira-issue.initiate.agent.md — description: "Update
  Jira Issue – Initiate: Update an existing Jira issue"; required state:
  jira.issue_key; CLI: agdt-initiate-update-jira-issue-workflow; no handoff

- [x] T040 [P] [US1] Create agent at

  .github/agents/agdt.apply-pr-suggestions.initiate.agent.md — description:
  .github/agents/agdt.apply-pr-suggestions.initiate.agent.md — description:
  "Apply PR Suggestions – Initiate: Apply PR review suggestions"; required
  state: pull_request_id; CLI: agdt-initiate-apply-pr-suggestions-workflow; no
  handoff

### Single-step workflow prompts (5 files)

- [x] T041 [P] [US1] Create prompt at

  .github/prompts/agdt.create-jira-issue.initiate.prompt.md — agent:
  .github/prompts/agdt.create-jira-issue.initiate.prompt.md — agent:
  agdt.create-jira-issue.initiate

- [x] T042 [P] [US1] Create prompt at

  .github/prompts/agdt.create-jira-epic.initiate.prompt.md — agent:
  .github/prompts/agdt.create-jira-epic.initiate.prompt.md — agent:
  agdt.create-jira-epic.initiate

- [x] T043 [P] [US1] Create prompt at

  .github/prompts/agdt.create-jira-subtask.initiate.prompt.md — agent:
  .github/prompts/agdt.create-jira-subtask.initiate.prompt.md — agent:
  agdt.create-jira-subtask.initiate

- [x] T044 [P] [US1] Create prompt at

  .github/prompts/agdt.update-jira-issue.initiate.prompt.md — agent:
  .github/prompts/agdt.update-jira-issue.initiate.prompt.md — agent:
  agdt.update-jira-issue.initiate

- [x] T045 [P] [US1] Create prompt at

  .github/prompts/agdt.apply-pr-suggestions.initiate.prompt.md — agent:
  .github/prompts/agdt.apply-pr-suggestions.initiate.prompt.md — agent:
  agdt.apply-pr-suggestions.initiate

**Checkpoint**: All 21 agents + 21 prompts created. Every workflow step is
accessible via `/agdt.<workflow>.<step>` in Copilot Chat.

---

## Phase 4: User Story 2 – Consistent step guidance (Priority: P2)

**Goal**: All agent bodies follow the same structure, tone, and section order
defined in the agent schema contract.

**Independent Test**: Open two different step agents and verify identical
section order (Purpose → Prerequisites → Actions → Expected Outcome → Next
Step).

- [x] T046 [US2] Review all 11 work-on-jira-issue agents (T004–T014) against

  contracts/agent-schema.md body structure and fix any deviations in section
  contracts/agent-schema.md body structure and fix any deviations in section
  order, heading names, or missing sections

- [x] T047 [US2] Review all 5 pull-request-review agents (T026–T030) against

  contracts/agent-schema.md body structure and fix any deviations
  contracts/agent-schema.md body structure and fix any deviations

- [x] T048 [US2] Review all 5 single-step workflow agents (T036–T040) against

  contracts/agent-schema.md body structure and fix any deviations
  contracts/agent-schema.md body structure and fix any deviations

- [x] T049 [US2] Verify all agent descriptions are ≤ 120 characters and include

  step position (e.g., "step 4 of 11") for multi-step workflows
  step position (e.g., "step 4 of 11") for multi-step workflows

- [x] T050 [US2] Verify all handoff agent references point to existing agent

  files (no broken links)
  files (no broken links)

**Checkpoint**: All agents are structurally consistent. A developer reading any
agent sees the same sections in the same order.

---

## Phase 5: User Story 3 – Maintain step coverage (Priority: P3)

**Goal**: A coverage verification script detects missing agents/prompts when new
workflow steps are added.

**Independent Test**: Run `python scripts/verify-agent-coverage.py` and see
21/21 coverage with exit code 0.

- [x] T051 [US3] Create coverage verification script at

  scripts/verify-agent-coverage.py that reads WORKFLOW_REGISTRY from
  scripts/verify-agent-coverage.py that reads WORKFLOW_REGISTRY from
  agentic_devtools/cli/workflows/manager.py and checks for matching
  .github/agents/agdt.<workflow>.<step>.agent.md and
  .github/prompts/agdt.<workflow>.<step>.prompt.md files

- [x] T052 [US3] Add support in scripts/verify-agent-coverage.py for

  single-step workflows (create-jira-issue, create-jira-epic,
  single-step workflows (create-jira-issue, create-jira-epic,
  create-jira-subtask, update-jira-issue, apply-pull-request-review-suggestions)
  that are not in WORKFLOW_REGISTRY but defined in commands.py. Include explicit
  name mapping for apply-pull-request-review-suggestions →
  agdt.apply-pr-suggestions.* agent namespace

- [x] T053 [US3] Run scripts/verify-agent-coverage.py and verify output shows

  21/21 steps covered with exit code 0
  21/21 steps covered with exit code 0

**Checkpoint**: Coverage script works end-to-end. Any future missing
agent/prompt is detectable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and final validation

- [x] T054 [P] Update README.md to document the new `/agdt.*` chat commands and

  link to quickstart.md
  link to quickstart.md

- [x] T055 [P] Update .github/copilot-instructions.md to mention the new agent

  namespace and usage pattern
  namespace and usage pattern

- [x] T056 Verify all 21 prompt files contain only YAML frontmatter with

  correct agent reference (no extra content)
  correct agent reference (no extra content)

- [ ] T057 Run a manual smoke test: open Copilot Chat, type `/agdt.` and verify

  that all 21 commands appear in the palette
  that all 21 commands appear in the palette

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — all 42 agent/prompt files can be

  created in parallel
  created in parallel

- **US2 (Phase 4)**: Depends on Phase 3 — reviews agent content created in US1
- **US3 (Phase 5)**: Depends on Phase 2 only — coverage script can be built in

  parallel with US1
  parallel with US1

- **Polish (Phase 6)**: Depends on Phase 3 and Phase 5

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — no

  dependencies on other stories
  dependencies on other stories

- **User Story 2 (P2)**: Depends on US1 (needs agent files to review)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) — independent

  of US1
  of US1

### Within Phase 3 (US1)

All 42 file creation tasks are marked [P] and can run in parallel — each creates
a separate file with no cross-dependencies.

### Parallel Opportunities

- T004–T045 (all 42 files) can run in parallel
- T051–T052 (coverage script) can run in parallel with T004–T045
- T054–T055 (docs updates) can run in parallel with each other

---

## Parallel Example: User Story 1

```bash
# All agent files for work-on-jira-issue can be launched together:
Task: T004 "Create agdt.work-on-jira-issue.initiate.agent.md"
Task: T005 "Create agdt.work-on-jira-issue.setup.agent.md"
...
Task: T014 "Create agdt.work-on-jira-issue.completion.agent.md"

# All prompt files can be launched together with agents:
Task: T015 "Create agdt.work-on-jira-issue.initiate.prompt.md"
...
Task: T045 "Create agdt.apply-pr-suggestions.initiate.prompt.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (template)
2. Complete Phase 2: Foundational (validate pattern)
3. Complete Phase 3: User Story 1 (all 42 files)
4. **STOP and VALIDATE**: Type `/agdt.work-on-jira-issue.planning` in Copilot
   Chat
5. Deploy if ready

### Incremental Delivery

1. Setup + Foundational → Pattern ready
2. Add US1 (42 files) → All steps accessible from chat (MVP!)
3. Add US2 (consistency review) → All agents structurally uniform
4. Add US3 (coverage script) → Automated gap detection
5. Polish → Documentation updated

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:

   - Developer A: work-on-jira-issue agents + prompts (T004–T025)
   - Developer B: pull-request-review agents + prompts (T026–T035)
   - Developer C: single-step agents + prompts (T036–T045) + coverage script

     (T051–T053)
     (T051–T053)
3. All merge, then one person does US2 consistency review (T046–T050)
4. Polish in parallel (T054–T057)

---

## Notes

- All [P] tasks create separate files with no cross-dependencies
- [US1] is the vast majority of work (42 files); US2 and US3 are lightweight

  validation
  validation

- No Python package changes — no `pyproject.toml` edits, no new CLI commands
- Agent body content references existing `agdt-*` CLI commands; does NOT

  duplicate Jinja2 templates
  duplicate Jinja2 templates

- Handoffs create a navigable chain: each step links to the next in the workflow
