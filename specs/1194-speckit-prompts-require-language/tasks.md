# Tasks: SpecKit Markdown Rules for Fenced Code Blocks

## Phase 1: Setup

- [ ] T001 Audit all in-scope prompt sources and confirm file inventory: 9 command templates in
  `.specify/templates/commands/*.md`, 9 agent files in `.github/agents/speckit.*.agent.md`,
  2 pipeline prompt-assembly scripts (`.specify/scripts/bash/update-agent-context.sh` and
  `.specify/scripts/powershell/update-agent-context.ps1`)

## Phase 2: Foundational

- [ ] T002 Identify existing inclusion pattern for `/memory/constitution.md` in command templates and
  `.specify/memory/constitution.md` in agent files to establish the *wording and placement* pattern for the new
  markdown-rules load instruction (note: agent files use the virtual path `/memory/markdown-rules.md`,
  not the filesystem path — only the phrasing and section placement are borrowed from the constitution reference)
  - Depends on: T001

## Phase 3: User Story 1 — Consistent markdown output guidance (P1)

- [ ] T003 [US1] Create `.specify/memory/markdown-rules.md` with normative rule requiring language specifiers on all fenced code blocks, including fallback to `text` for non-code blocks (FR-002,
  FR-003, FR-005)
  - Depends on: T002
- [ ] T004 [US1] Validate `.specify/memory/markdown-rules.md` content is ≤ 500 characters including newlines/formatting (NFR-001)
  - Depends on: T003
- [ ] T005 [US1] Draft the one-line load instruction text and verify it is ≤ 100 characters (NFR-001)
  - Depends on: T003

## Phase 4: User Story 2 — Reliable prompt behavior across templates (P1)

### Command templates

- [ ] T006 [P] [US2] Add one-line load instruction to `.specify/templates/commands/plan.md` — step 2 (Load context), alongside constitution load (FR-004, FR-008)
  - Depends on: T005
- [ ] T007 [P] [US2] Add one-line load instruction to `.specify/templates/commands/analyze.md` — step 2 (Load Artifacts), alongside constitution load (FR-004, FR-008)
  - Depends on: T005
- [ ] T008 [P] [US2] Add one-line load instruction to `.specify/templates/commands/constitution.md` — step 1, alongside constitution load (FR-004, FR-008)
  - Depends on: T005
- [ ] T009 [P] [US2] Add one-line load instruction to `.specify/templates/commands/specify.md` — step 3 (Load template) context section (FR-004, FR-008)
  - Depends on: T005
- [ ] T010 [P] [US2] Add one-line load instruction to `.specify/templates/commands/tasks.md` — step 2 (Load design documents) context section (FR-004, FR-008)
  - Depends on: T005
- [ ] T011 [P] [US2] Add one-line load instruction to `.specify/templates/commands/clarify.md` — step 2 (Load spec file) context section (FR-004, FR-008)
  - Depends on: T005
- [ ] T012 [P] [US2] Add one-line load instruction to `.specify/templates/commands/implement.md` — step 3 (Load context) context section (FR-004, FR-008)
  - Depends on: T005
- [ ] T013 [P] [US2] Add one-line load instruction to `.specify/templates/commands/checklist.md` — step 4 (Load feature context) context section (FR-004, FR-008)
  - Depends on: T005
- [ ] T014 [P] [US2] Add one-line load instruction to `.specify/templates/commands/taskstoissues.md` — after step 1 (setup) context section (FR-004, FR-008)
  - Depends on: T005

### Agent files

- [ ] T015 [P] [US2] Add one-line load instruction to `.github/agents/speckit.plan.agent.md` using `/memory/markdown-rules.md` virtual path (FR-006, FR-008)
  - Depends on: T005
- [ ] T016 [P] [US2] Add one-line load instruction to `.github/agents/speckit.analyze.agent.md` using `/memory/markdown-rules.md` virtual path (FR-006, FR-008)
  - Depends on: T005
- [ ] T017 [P] [US2] Add one-line load instruction to `.github/agents/speckit.constitution.agent.md` using `/memory/markdown-rules.md` virtual path (FR-006, FR-008)
  - Depends on: T005
- [ ] T018 [P] [US2] Add one-line load instruction to `.github/agents/speckit.specify.agent.md` using `/memory/markdown-rules.md` virtual path (FR-006, FR-008)
  - Depends on: T005
- [ ] T019 [P] [US2] Add one-line load instruction to `.github/agents/speckit.tasks.agent.md` using `/memory/markdown-rules.md` virtual path (FR-006, FR-008)
  - Depends on: T005
- [ ] T020 [P] [US2] Add one-line load instruction to `.github/agents/speckit.clarify.agent.md` using `/memory/markdown-rules.md` virtual path (FR-006, FR-008)
  - Depends on: T005
- [ ] T021 [P] [US2] Add one-line load instruction to `.github/agents/speckit.implement.agent.md` using `/memory/markdown-rules.md` virtual path (FR-006, FR-008)
  - Depends on: T005
- [ ] T022 [P] [US2] Add one-line load instruction to `.github/agents/speckit.checklist.agent.md` using `/memory/markdown-rules.md` virtual path (FR-006, FR-008)
  - Depends on: T005
- [ ] T023 [P] [US2] Add one-line load instruction to `.github/agents/speckit.taskstoissues.agent.md` using `/memory/markdown-rules.md` virtual path (FR-006, FR-008)
  - Depends on: T005

## Phase 5: User Story 3 — Runtime parity for generated prompts (P2)

- [ ] T024 [US3] Update `.specify/scripts/bash/update-agent-context.sh` to `cat .specify/memory/markdown-rules.md` and inject contents into the prompt string during runtime assembly (FR-001)
  - Depends on: T004
- [ ] T025 [US3] Add graceful degradation to `.specify/scripts/bash/update-agent-context.sh` — if shared file is missing, log warning to stderr and continue without injecting (FR-007)
  - Depends on: T024
- [ ] T026 [US3] Update `.specify/scripts/powershell/update-agent-context.ps1` to read
  `.specify/memory/markdown-rules.md` via `Get-Content -Raw` (the platform-equivalent of `cat`) and
  inject contents into the prompt string during runtime assembly (FR-001)
  - Depends on: T004
- [ ] T027 [US3] Add graceful degradation to `.specify/scripts/powershell/update-agent-context.ps1` — if shared file is missing, log warning to stderr and continue without injecting (FR-007)
  - Depends on: T026

## Phase 6: User Story 4 — Actionable implementation scope verification (P3)

- [ ] T028 [US4] Verify SC-001: `.specify/memory/markdown-rules.md` exists and contains the fenced code block language specifier rule
  - Depends on: T003
- [ ] T029 [US4] Verify SC-002: all 9 command templates include the one-line load instruction with `/memory/markdown-rules.md` virtual path in context/setup section
  - Depends on: T006, T007, T008, T009, T010, T011, T012, T013, T014
- [ ] T030 [US4] Verify SC-003: all 9 agent files include the one-line load instruction with `/memory/markdown-rules.md` virtual path in context/setup section
  - Depends on: T015, T016, T017, T018, T019, T020, T021, T022, T023
- [ ] T031 [US4] Verify SC-004: shared file content ≤ 500 chars, reference line ≤ 100 chars, combined overhead per prompt source ≤ 600 chars
  - Depends on: T029, T030
- [ ] T032 [US4] Verify SC-005: the spec document remains standalone and actionable — user stories, requirements, edge cases, and success criteria are defined directly without referencing missing
  external definitions
- [ ] T033 [US4] Verify SC-006 (bash): `.specify/scripts/bash/update-agent-context.sh` reads `.specify/memory/markdown-rules.md` via `cat` and injects contents into the runtime prompt string
  - Depends on: T025
- [ ] T034 [US4] Verify SC-006 (PowerShell): `.specify/scripts/powershell/update-agent-context.ps1` reads `.specify/memory/markdown-rules.md` via `Get-Content -Raw` and injects contents into the
  runtime
  prompt string
  - Depends on: T027
- [ ] T035 [US4] Verify scope completeness: confirm command templates, agent files, and pipeline scripts are all explicitly addressed with no prompt source missed
  - Depends on: T031, T033, T034

## Final Phase: Polish & Cross-Cutting

- [ ] T036 Run `npx markdownlint-cli2@0.17.2` from within the spec directory (to use per-spec `.markdownlint.json` and avoid root config override) against sample generated `spec.md`, `plan.md`,
  and `tasks.md` artifacts and confirm zero `MD040` (`fenced-code-language`) violations — mirror the invocation in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` for CI parity (SC-007)
  - Depends on: T035
- [ ] T037 Verify no templates duplicate the full rule text inline — only the one-line load instruction is present (NFR-002)
  - Depends on: T029, T030
- [ ] T038 End-to-end integration test: run a SpecKit command (e.g., `speckit.specify`) and verify the assembled prompt contains the markdown rule content before generation instructions
  - Depends on: T035
- [ ] T039 Verify graceful degradation end-to-end: temporarily rename `.specify/memory/markdown-rules.md`, run pipeline scripts, confirm stderr warning and no crash (FR-007)
  - Depends on: T025, T027

---
*Generated by Copilot SDK (claude-opus-4.6)*
