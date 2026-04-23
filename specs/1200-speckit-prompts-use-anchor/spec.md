# Spec: SpecKit prompts: Use anchor descriptions instead of hardcoded line numbers in tasks

## Summary

Update the relevant SpecKit prompt templates so task descriptions use **semantic anchors**
instead of hardcoded line numbers when referring to code, configuration, documentation, or
other file content. The goal is to make generated implementation tasks more stable under
normal editing, rebasing, and regeneration, while preserving clarity and keeping prompt size
within acceptable bounds.

## Problem Statement

Current task text can reference files using hardcoded line numbers such as "edit lines 42-57"
or "insert below line 18". These references become stale as soon as the file changes, which
creates ambiguity for implementers and increases the likelihood of edits being applied in the
wrong place. This is especially fragile in iterative workflows where plans are reviewed,
refined, regenerated, or executed after adjacent edits have already shifted file content.

The task format should instead describe locations using stable, human-readable anchors such as:

- existing symbols or declarations
- nearby headings, sections, or keys
- recognizable snippets or comments
- insertion points relative to semantic structure

This change should improve implementation reliability without materially increasing prompt
complexity or token usage.

## Clarifications

### Q1. What replaces hardcoded line numbers?

**Answer:** Use **semantic anchors** as the umbrella term for all location descriptions. A
semantic anchor may refer to a function, class, constant, heading, JSON/YAML key, Markdown
section, test case name, comment marker, or another stable content landmark.

### Q2. Are line numbers always forbidden?

**Answer:** The intended output should avoid hardcoded line numbers in generated tasks. If a
source artifact contains line numbers, prompts should still transform task instructions into
semantic-anchor-based references rather than propagating those line numbers as the primary
execution guidance.

### Q3. Which files are in scope for implementation?

**Answer:** Scope is intentionally narrow. The implementation should be limited to the **two
prompt files** responsible for task-generation wording in this workflow. No broader planner,
parser, renderer, or agent behavior changes are required unless already strictly necessary to
update those prompt texts.

### Q4. Must the implement agent prompt also change?

**Answer:** No. Validation should confirm the implement experience still works with
semantic-anchor-based tasks, but no implement-agent prompt rewrite is required in this spec.
That requirement is captured as validation only.

### Q5. How should tasks refer to symbols created earlier in the same plan?

**Answer:** Tasks should use cross-task semantic references where appropriate, such as
"update the helper introduced in Task 2" or "extend the `build_anchor_map` function created in
the previous step," especially when the exact final line location is unknowable at planning
time.

## Goals

- Replace hardcoded line-number instructions with semantic-anchor wording in generated tasks.
- Improve task robustness when files change between planning and execution.
- Keep prompt changes minimal and localized.
- Preserve readability and actionability for implementers.
- Support both code and non-code file references under one consistent terminology.

## Non-Goals

- Rewriting the implement agent prompt.
- Changing the execution engine, checklist engine, or workflow state machine.
- Introducing AST parsing, repository indexing, or runtime code navigation.
- Guaranteeing a unique anchor in every possible repository layout.
- Retrofitting old generated artifacts already produced before this change.

## Scope

In scope:

- Prompt wording updates that instruct the planner to describe file changes with semantic
  anchors.
- Examples and guidance inside prompt templates showing acceptable anchor styles.
- Guidance for referring to insertion points, modifications, and cross-task follow-up edits.
- Validation that the revised prompt output avoids hardcoded line numbers in normal cases.

### Scope Boundary

This spec explicitly limits implementation changes to **2 files**:
`.github/agents/speckit.tasks.agent.md` and `.specify/templates/tasks-template.md`.
These are the prompt files that define the relevant planning/task-generation behavior. No
other source files should be edited as part of satisfying this spec unless a trivial adjacent
documentation tweak is unavoidable.

Out of scope:

- Changes to unrelated prompts.
- Changes to runtime code that consumes already-generated tasks.
- Changes to implement-agent prompt text beyond validating compatibility.

## Dependencies and Assumptions

- The existing SpecKit task-generation pipeline (`.github/agents/speckit.tasks.agent.md` and
  `.specify/templates/tasks-template.md`) is stable and will not undergo unrelated structural
  changes during this work.
- The `speckit.implement` agent already uses search-based code navigation (grep, glob, file
  view) and does not depend on line numbers to locate edit targets, so semantic-anchor-based
  tasks are compatible without implement-agent prompt changes.
- The OpenAI `cl100k_base` tokenizer is available for measuring prompt token counts as
  required by NFR-001.

## Users / Stakeholders

- **Primary:** AI planning agents generating implementation task lists.
- **Secondary:** AI implementation agents consuming those tasks.
- **Tertiary:** Human reviewers reading plans and verifying task clarity.

## User Stories

### US1 — Planner emits stable task locations (Priority: P1)

As a planning agent, I want to describe edit locations using semantic anchors so that tasks
remain understandable even if nearby file contents shift.

**Acceptance Criteria**

- Generated tasks do not rely on hardcoded line numbers as the primary location reference.
- Tasks identify edit targets using stable landmarks such as symbols, headings, keys, or
  recognizable surrounding content.
- The task remains actionable to an implementer without needing to recalculate line offsets.

**Acceptance Scenarios**

1. **Given** a spec requiring modifications to an existing source file with multiple named
   symbols,
   **When** `speckit.tasks` generates the task list,
   **Then** each task referencing a location within that file uses a semantic anchor (e.g.,
   "inside the `process_request` function", "after the import block") and does NOT use a bare
   line number as the primary locator.

2. **Given** a spec where multiple tasks modify the same file sequentially,
   **When** `speckit.tasks` generates the task list,
   **Then** no task's location reference is invalidated by the execution of a preceding task,
   because all references use stable semantic anchors.

### US2 — Implementer can find where to change a file (Priority: P1)

As an implementation agent, I want task instructions to point to meaningful file landmarks so I
can apply changes correctly after intervening edits or regeneration.

**Acceptance Criteria**

- A task that previously would have said "edit line X" instead says where to edit relative to a
  semantic anchor.
- Insertion tasks specify placement relative to an existing semantic structure, such as "below
  the `load_config` function" or "under the `## Testing` heading".
- Tasks remain concise and understandable.

**Acceptance Scenarios**

1. **Given** a generated task that targets a well-known code structure,
   **When** an implementation agent reads the task,
   **Then** the task describes the edit location using a semantic anchor (e.g., "in the
   `get_auth_headers` function") rather than a bare line number.

2. **Given** a generated task that requires inserting new content between existing structures,
   **When** an implementation agent reads the task,
   **Then** the insertion point is described relative to named structures (e.g., "after the
   `validate_input` method in `RequestHandler`") rather than absolute line positions.

### US3 — Reviewer sees consistent terminology across file types (Priority: P2)

As a reviewer, I want one consistent concept for location references across code and non-code
files so the task format is easier to evaluate and teach.

**Acceptance Criteria**

- The prompts use the term **semantic anchor** consistently.
- Older phrasing such as "content-based anchor" is removed or normalized.
- Examples cover both code and non-code artifacts.

**Acceptance Scenarios**

1. **Given** the updated prompt templates,
   **When** a reviewer searches for location-reference terminology,
   **Then** only the term "semantic anchor" is used — no legacy terms like "content-based
   anchor" or "structural reference" appear.

### US4 — Validation only: implement prompt remains compatible (Priority: P2)

As a maintainer, I want confidence that semantic-anchor-based tasks still work with the current
implementation prompt so that this change stays narrowly scoped.

**Acceptance Criteria**

- Validation confirms no implement-agent prompt rewrite is required.
- The spec does not require changes to implement-agent prompt files.
- Review notes or test evidence can demonstrate compatibility.

**Acceptance Scenarios**

1. **Given** the implement agent's existing prompt text,
   **When** it receives tasks that use semantic-anchor-based location descriptions,
   **Then** the agent can still locate and apply changes correctly without prompt modifications.

## Functional Requirements

- **FR-001:** The planning prompt(s) in scope MUST instruct task generation to use semantic
  anchors instead of hardcoded line numbers when describing where to edit a file.
- **FR-002:** The prompt(s) MUST describe acceptable anchor forms for source-code files,
  including symbols such as functions, methods, classes, constants, tests, or comments.
- **FR-003:** The prompt(s) MUST describe acceptable anchor forms for non-code files,
  including headings, sections, keys, table rows, bullet groups, or recognizable text blocks.
- **FR-004:** The prompt(s) MUST guide insertion tasks to describe placement relative to an
  anchor, such as before/after/inside/under a semantic landmark.
- **FR-005:** The prompt(s) MUST prefer stable and distinctive anchors over vague references
  such as "near the top" or "in the middle of the file."
- **FR-006:** The prompt(s) MUST preserve task clarity and directness so instructions remain
  executable by an implementation agent without additional interpretation.
- **FR-007:** The prompt(s) MUST use the unified term **semantic anchor** for all supported
  anchor types across code and non-code files.
- **FR-008:** The prompt(s) MUST support cross-task references to newly created symbols or
  structures when a later task depends on something introduced earlier in the same plan.

## Non-Functional Requirements

- **NFR-001 Prompt size:** The revised prompt content MUST stay within a modest token-growth
  envelope. Measured baseline is approximately **1,601 tokens** and the expected ceiling after
  this change is approximately **1,841 tokens**. For validation, measure the full rendered text
  of each changed in-scope prompt template using the OpenAI `cl100k_base` tokenizer (the same
  tokenizer family used by GPT-4/4o prompt budgeting), and record the measured token count plus
  the tokenizer name in the validation evidence for checklist item **CHK008**.
- **NFR-002 Minimal surface area:** The change SHOULD be localized to the two in-scope prompt
  files and SHOULD not require broad refactoring.
- **NFR-003 Readability:** Added guidance SHOULD be concise, scannable, and understandable by
  both AI agents and human reviewers.
- **NFR-004 Backward compatibility:** Existing workflows MUST continue to operate; only the
  wording and quality of generated tasks SHOULD change.
- **NFR-005 Determinism:** Prompt guidance MUST be explicit enough that planners reliably
  prefer semantic anchors over line numbers across repeated runs.

## Edge Cases

- A file has repeated symbols or repeated section headings; the task should include enough
  nearby context to disambiguate the intended anchor.
- The target change is an insertion into an empty or very short file; the task should anchor to
  the file-level structure or intended section placement.
- The target is a non-code file such as Markdown, YAML, or JSON where no code symbol exists;
  the task should still use a semantic anchor such as a heading or key path.
- A task depends on a symbol that will be created by an earlier task; the later task should
  reference that newly created symbol or explicitly refer to "the helper/type/module created in
  Task N".
- A prior plan draft used line numbers; regenerated output should normalize to semantic-anchor
  phrasing instead of preserving brittle numeric references.
- A file has no recognizable semantic structure (e.g., an auto-generated file, a binary
  placeholder, or a flat text file with no headings or named symbols); the task should fall
  back to describing the location by surrounding content or file-level placement.
- The intended anchor target has been deleted or the file has been renamed since the plan was
  drafted; the task should be treated as stale and regenerated rather than guessing a new
  location.
- An anchor exists but is ambiguous or unusable (e.g., a minified file where symbol names are
  single characters); the task should include enough surrounding context or a distinctive
  content snippet to disambiguate.

## Key Entities and Terminology

- **Semantic anchor:** A stable, human-readable description of a location in a file, including
  code symbols, headings, keys, comment markers, named tests, table sections, or recognizable
  text blocks.
- **Hardcoded line number reference:** A task instruction that identifies edit location
  primarily by numeric line positions or ranges.
- **Task:** A generated implementation instruction produced by the planning prompt.
- **Cross-task symbol reference:** A later task's reference to a symbol, helper, section, or
  structure introduced by an earlier task in the same plan.

## Success Criteria

This spec is successful when:

- **SC-001 (quantitative):** 100% of task descriptions in newly generated `tasks.md` files
  that reference locations within existing files use a semantic anchor as the primary locator,
  and 0% contain a bare line number as the sole location reference — verified by manual review
  of at least 3 generated `tasks.md` files across different spec types.
- Generated tasks from the updated prompt(s) consistently use semantic anchors rather than
  hardcoded line numbers.
- Example outputs remain clear and actionable for implementation agents.
- Non-code files are covered under the same terminology and guidance.
- Cross-task references to newly created symbols are supported in the prompt guidance.
- The prompt-size increase remains within the defined NFR-001 ceiling.
- Only the two intended prompt files need to change.

## Validation Approach

- Review the two in-scope prompt files and confirm line-number-based wording has been replaced
  with semantic-anchor guidance.
- Generate or inspect representative task output for:
  - an existing-symbol edit
  - an insertion relative to an existing anchor
  - a non-code file edit
  - a cross-task reference to a newly created symbol
- Run a backward-compatibility regression check for legacy task artifacts:
  - **Given** an older `tasks.md` (or equivalent) that still contains line-number wording such
    as "edit lines 42-57" or "insert below line 18",
  - **When** `speckit.implement` is run against that artifact, or its task-loading/execution
    path is inspected using that artifact as input,
  - **Then** the workflow remains executable without requiring semantic-anchor-only wording,
    confirming this prompt-only planner change does not break existing implementation flows.
- Confirm implement-agent prompt changes were not required.
- Confirm prompt size remains within the NFR-001 target envelope.

## Risks and Mitigations

- **Risk:** Anchors may be too vague in files with repeated structures.
  **Mitigation:** Prompt guidance should instruct planners to include distinctive nearby
  context when needed.
- **Risk:** Additional prompt wording could increase token count.
  **Mitigation:** Keep examples compact and reuse one unified term.
- **Risk:** Some tasks may still mention line numbers out of habit or copied context.
  **Mitigation:** Make avoidance explicit in the prompt requirements and examples.

## Open Questions

- None at clarify-phase completion.

## What Changed in Clarify Phase

1. Clarifications section added after Problem Statement with 5 Q&A pairs.
2. US4 marked as "Validation Only" — no implement agent prompt changes needed.
3. NFR-001 now includes measured baseline (~1,601 tokens, ceiling ~1,841).
4. Scope Boundary subsection added — explicitly limits changes to 2 files.
5. Terminology normalized — "content-based anchor" retired; "semantic anchor" is the umbrella
   term for all file types.
6. FR-007/FR-008 updated — FR-007 uses unified terminology; FR-008 covers cross-task
   references to newly created symbols.
7. Edge cases expanded with cross-task symbol reference scenario.
8. Key Entities definition broadened to include non-code anchor types under the single term.
