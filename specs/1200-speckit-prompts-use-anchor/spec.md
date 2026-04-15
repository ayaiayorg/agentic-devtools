# Feature Specification: Semantic Anchors in SpecKit Task Descriptions

**Feature Branch**: `speckit/1200/phase-1-specify`
**Created**: 2026-04-15
**Status**: Draft
**Input**: User description: "Update SpecKit prompts to use semantic anchors instead of hardcoded line numbers in task descriptions"
**Source Issue**: #1200 (<https://github.com/ayaiayorg/agentic-devtools/issues/1200>)

## Problem Statement

SpecKit-generated `tasks.md` files currently contain hardcoded line number references (e.g., `~line 36–39`, `~line 198`)
when describing where code modifications should occur. These references are inherently brittle because tasks execute sequentially —
each earlier task that adds or removes lines invalidates the line numbers referenced by subsequent tasks.
This causes the implementing LLM to target the wrong code locations, introducing bugs or requiring manual correction.

The root cause is that the SpecKit task generation prompts (`.github/agents/speckit.tasks.agent.md` and
`.specify/templates/tasks-template.md`) contain no guidance instructing the LLM to describe code locations
using semantic anchors (function names, class definitions, import blocks, comment markers) rather than absolute line numbers.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Task Descriptions Use Semantic Anchors by Default (Priority: P1)

As a developer using `speckit.tasks` to generate an implementation plan,
I want task descriptions to reference code locations by semantic anchors (function names, class names, structural landmarks)
so that tasks remain valid even after earlier tasks modify the same files.

**Why this priority**: This is the core value proposition. Without semantic anchors in the generated output,
every multi-task plan targeting existing files risks cascading location drift.
This is the most frequently encountered failure mode reported in #1200.

**Independent Test**: Run `speckit.tasks` against any spec that involves modifying existing source files.
Inspect the generated `tasks.md` — every code location reference should use a semantic anchor.
No task description should contain a bare line number as the sole locator.

**Acceptance Scenarios**:

1. **Given** a spec requiring modifications to an existing Python file with multiple functions,
**When** `speckit.tasks` generates the task list,
**Then** each task referencing a location within that file uses a semantic anchor
(e.g., "inside the `process_request` function", "after the `import` block",
"in the `UserService` class definition") and does NOT use a bare line number as the primary locator.

2. **Given** a spec requiring insertion of new code between existing structures,
**When** `speckit.tasks` generates the task list,
**Then** insertion points are described relative to named code structures
(e.g., "after the `validate_input` method in `RequestHandler`",
"between the `setup` and `teardown` functions") rather than absolute line positions.

3. **Given** a spec where multiple tasks modify the same file sequentially,
**When** `speckit.tasks` generates the task list,
**Then** no task's location reference is invalidated by the execution of a preceding task,
because all references use stable semantic anchors.

---

### User Story 2 — Line Numbers Permitted Only as Secondary Hints (Priority: P2)

As a developer reading a generated task, I want line numbers to appear only as supplementary hints alongside a semantic anchor
so that I can quickly locate the target area while still having a stable primary reference if the file changes.

**Why this priority**: Line numbers provide useful orientation for humans scanning large files.
Banning them entirely would reduce usability. The key is demoting them from primary locator to optional hint.

**Independent Test**: Generate tasks for a spec that references specific locations in large files.
Verify that any line numbers present are always accompanied by a semantic anchor
and are clearly marked as approximate (e.g., using `~` prefix or parenthetical).

**Acceptance Scenarios**:

1. **Given** a generated task that includes a line number,
**When** reviewing the task description,
**Then** the line number appears as a secondary hint
(e.g., "in the `get_auth_headers` function (~line 45)")
and a semantic anchor is always the primary locator.

2. **Given** a generated task that targets a well-known code structure,
**When** reviewing the task description,
**Then** no line number is present at all, because the semantic anchor alone is sufficient
(e.g., "at the top of the imports block" rather than "at line 1–5").

---

### User Story 3 — Prompt Template Examples Demonstrate the Pattern (Priority: P2)

As a contributor modifying SpecKit prompts, I want the task generation rules and template to include explicit examples
of semantic anchor usage (and anti-examples of bare line numbers) so that the pattern is self-documenting
and consistently applied by any LLM.

**Why this priority**: Without concrete examples embedded in the prompt, LLMs may regress to line-number habits.
Examples in the prompt template serve as few-shot guidance and are the primary enforcement mechanism.

**Independent Test**: Read the updated `.github/agents/speckit.tasks.agent.md` and `.specify/templates/tasks-template.md`.
Verify that both contain at least two positive examples of semantic anchors
and at least one negative example showing a bare line number marked as incorrect.

**Acceptance Scenarios**:

1. **Given** the `speckit.tasks` agent definition,
**When** a contributor reads the Task Generation Rules section,
**Then** there is a clearly labeled subsection (or addition to the existing format rules) explaining
the semantic anchor requirement with correct and incorrect examples.

2. **Given** the tasks template file,
**When** a contributor reads the sample tasks,
**Then** at least one sample task demonstrates a semantic anchor pattern
(e.g., referencing a function name or import block rather than a line number).

---

### User Story 4 — Implement Agent Recognizes Semantic Anchors (Priority: P3)

As an AI agent executing tasks via `speckit.implement`, I want task descriptions to use semantic anchors
so that I can reliably locate the target code using search/grep rather than counting lines,
even in files that have been modified by earlier tasks in the same session.

**Why this priority**: The implement agent is the consumer of tasks.md.
If it cannot reliably resolve task locations, the entire pipeline breaks.
However, the implement agent already uses search-based code navigation (grep, glob, view),
so this story is primarily about ensuring the input format aligns with the agent's natural resolution strategy.

**Independent Test**: Execute `speckit.implement` against a tasks.md that uses semantic anchors.
Verify the agent correctly locates and modifies the target code for each task,
including tasks that target files already modified by earlier tasks in the same run.

**Acceptance Scenarios**:

1. **Given** a tasks.md with semantic anchor references generated by the updated `speckit.tasks`,
**When** `speckit.implement` executes the tasks in order,
**Then** each task correctly locates and modifies the intended code location,
even when earlier tasks have changed line counts in the same file.

---

### Edge Cases

- What happens when a target code structure has a non-unique name (e.g., multiple `__init__` methods across classes)?
The anchor must be qualified with the enclosing scope (e.g., "the `__init__` method of `UserService`").
- What happens when the target is in a file with no named structures (e.g., a JSON config file, a plain text file)?
The task should use content-based anchors (e.g., "after the `"scripts"` key in `package.json`")
or structural descriptions (e.g., "at the end of the top-level object").
- What happens when the target is a newly created file?
No anchor is needed — the task describes what to create, not where to insert within existing code.
The anchor guidance only applies to modifications of existing files.
- How does the system handle minified or generated files where semantic structures are absent?
These files should not typically be targets of task modifications.
If they are, the task should note the lack of stable anchors and use content-based matching.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `speckit.tasks` agent prompt (`.github/agents/speckit.tasks.agent.md`) MUST include explicit instructions
requiring task descriptions to reference code locations by semantic anchors
(function names, class names, method names, import blocks, named constants, comment markers, or unique string literals).

- **FR-002**: The `speckit.tasks` agent prompt MUST include explicit instructions prohibiting bare line numbers
as the sole locator in any task description.

- **FR-003**: The `speckit.tasks` agent prompt MUST permit line numbers only when accompanied by a semantic anchor
and clearly marked as approximate (e.g., using `~` prefix or parenthetical notation).

- **FR-004**: The tasks template (`.specify/templates/tasks-template.md`) MUST include at least two positive examples
demonstrating correct semantic anchor usage and at least one negative example
showing a bare line number marked as incorrect in its illustrative examples.

- **FR-005**: The `speckit.tasks` agent prompt MUST include at least two positive examples (correct semantic anchors)
and at least one negative example (bare line number marked as incorrect) in the Task Generation Rules section.

- **FR-006**: Semantic anchors MUST be scoped to be unambiguous — when a name is non-unique within a file,
the anchor MUST include the enclosing scope
(e.g., "`__init__` in `UserService`" rather than just "`__init__`").

- **FR-007**: For non-code files (JSON, YAML, TOML, plain text), the guidance MUST instruct the use of
content-based anchors (key names, section headers, unique string values) instead of line numbers.

### Non-Functional Requirements

- **NFR-001**: The prompt additions MUST NOT increase the `speckit.tasks` agent prompt token count by more than ~15%
to avoid degrading LLM task generation quality through prompt bloat.

- **NFR-002**: The guidance MUST be expressed in clear, direct language that any LLM (Claude, GPT, etc.)
can follow without ambiguity — avoiding jargon or indirect phrasing.

- **NFR-003**: The changes MUST be backward-compatible — existing tasks.md files with line numbers remain valid
and executable; only newly generated tasks.md files are affected.

- **NFR-004**: The format of the checklist items (`- [ ] [ID] [P?] [Story?] Description`, e.g.,
`- [ ] T001 [P] [US1] Update ...` for a user-story task, or `- [ ] T002 Update ...` for a non-story task)
MUST NOT change — the story label is optional except for user-story tasks, and semantic anchors are part of
the Description text, not a new structural element.

### Key Entities

- **Semantic Anchor**: A stable, content-based reference to a code location —
a function name, class name, method name, import block, named constant, comment marker,
or unique string literal that survives line-count changes.
- **Task Description**: The free-text portion of a tasks.md checklist item that describes what to do and where to do it.
This is where anchors appear.
- **Task Generation Rules**: The `## Task Generation Rules` section in
`.github/agents/speckit.tasks.agent.md` that governs the format and content requirements for generated tasks.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of task descriptions in newly generated tasks.md files that reference locations within existing files
use a semantic anchor as the primary locator,
verified by manual review of at least 3 generated tasks.md files across different project types.

- **SC-002**: 0% of task descriptions in newly generated tasks.md files contain a bare line number
(a line number without an accompanying semantic anchor) as the sole location reference.

- **SC-003**: The `speckit.implement` agent successfully resolves and executes all tasks in a generated tasks.md
that uses semantic anchors, with no location-drift failures caused by earlier tasks modifying the same file.

- **SC-004**: The combined prompt additions to `speckit.tasks.agent.md` and `tasks-template.md` total fewer than 40 lines
of new content (excluding examples moved or reformatted), keeping prompt size manageable.

---
*Generated by Copilot SDK (claude-opus-4.6)*
