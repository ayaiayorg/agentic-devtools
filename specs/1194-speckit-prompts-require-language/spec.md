# Feature Specification: Require Language Specifier on Fenced Code Blocks in SpecKit Prompts

**Feature Branch**: `speckit/1194/phase-1-specify`
**Created**: 2026-04-15
**Status**: Draft
**Input**: GitHub Issue #1194 — SpecKit generation prompts do not instruct the LLM to specify a language on fenced code blocks,
causing MD040 violations in generated artifacts
**Source Issue**: #1194 (<https://github.com/ayaiayorg/agentic-devtools/issues/1194>)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Generated spec.md passes markdownlint without remediation (Priority: P1)

As a developer running `speckit.specify`, I want the generated `spec.md` to have language identifiers on all fenced code blocks
so that the output passes `markdownlint` (MD040) on the first attempt without requiring the reactive LLM remediation loop in the pipeline.

**Why this priority**: The `specify` command is the most frequently executed SpecKit step and produces the most fenced code blocks
(shell examples, JSON snippets, plain-text diagrams). Eliminating MD040 violations here provides the highest impact —
fewer remediation iterations, faster pipeline runs, and lower LLM token costs.

**Independent Test**: Run `speckit.specify` with a feature description that naturally produces code examples
(e.g., "Add a CLI command that accepts JSON input and outputs TOML").
Verify every fenced code block in the generated `spec.md` has a language identifier.
Run `npx markdownlint-cli2 specs/<dir>/spec.md` and confirm zero MD040 violations.

**Acceptance Scenarios**:

1. **Given** a SpecKit `specify` command prompt that includes the code-block formatting instruction,
**When** the LLM generates a `spec.md` containing fenced code blocks,
**Then** every fenced code block includes a language identifier (e.g., `bash`, `python`, `json`, `text`).
2. **Given** a generated `spec.md`, **When** `markdownlint-cli2` is run against it,
**Then** zero MD040 (fenced-code-language) violations are reported.
3. **Given** a feature description that involves no code examples,
**When** `speckit.specify` generates output with no fenced code blocks,
**Then** the output is unaffected by the new instruction (no false positives or empty code blocks injected).

---

### User Story 2 — Generated plan.md and tasks.md pass MD040 (Priority: P1)

As a developer running `speckit.plan` or `speckit.tasks`, I want generated `plan.md` and `tasks.md` files to include
language identifiers on all fenced code blocks so that the full SpecKit pipeline produces lint-clean artifacts end-to-end.

**Why this priority**: The `plan` and `tasks` commands are the next most common artifact generators after `specify`,
and `plan.md` was the specific file that triggered the MD040 violation in PR #1178.
These commands must receive the same instruction to close the gap that motivated issue #1194.

**Independent Test**: Run `speckit.plan` and `speckit.tasks` for a feature that involves shell commands and code snippets.
Verify every fenced code block in `plan.md` and `tasks.md` has a language identifier.
Run `markdownlint-cli2` and confirm zero MD040 violations.

**Acceptance Scenarios**:

1. **Given** a `speckit.plan` prompt with the code-block instruction,
**When** the LLM generates `plan.md` containing code examples,
**Then** every fenced code block has a language identifier.
2. **Given** a `speckit.tasks` prompt with the code-block instruction,
**When** the LLM generates `tasks.md` containing fenced code blocks,
**Then** every fenced code block has a language identifier.

---

### User Story 3 — All remaining SpecKit generation prompts enforce code-block language (Priority: P2)

As a developer using any SpecKit command that generates or modifies markdown artifacts
(`clarify`, `checklist`, `implement`, `analyze`, `constitution`),
I want the code-block formatting instruction to be present so that all SpecKit-generated markdown is MD040-compliant.

**Why this priority**: While these commands generate fewer code blocks than `specify`/`plan`/`tasks`,
consistency across the full SpecKit suite prevents edge-case violations and establishes a uniform quality standard.
This also eliminates the risk of MD040 violations migrating to less-tested commands.

**Independent Test**: For each of the remaining SpecKit commands (`clarify`, `checklist`, `implement`, `analyze`, `constitution`),
run the command with input that would produce code blocks.
Verify language identifiers are present on all generated fenced code blocks.

**Acceptance Scenarios**:

1. **Given** any SpecKit command prompt that includes the code-block instruction,
**When** the LLM generates markdown output with fenced code blocks,
**Then** every code block has a language identifier.
2. **Given** the `speckit.implement` command,
**When** the LLM creates or modifies files that contain fenced code blocks,
**Then** language identifiers are preserved or added.

---

### User Story 4 — Shared instruction block avoids duplication (Priority: P2)

As a maintainer of the SpecKit prompt system, I want the code-block language instruction to be defined once in a shared location
and referenced by all SpecKit prompts so that future updates to the formatting rule only require a single change.

**Why this priority**: There are 9 SpecKit command templates. Duplicating the instruction in each one creates a maintenance burden
and risks drift. A shared instruction block aligns with the DRY principle and the existing constitution/template architecture.

**Independent Test**: Verify that the code-block instruction text exists in exactly one shared location
(not copy-pasted across 9 files). Confirm each SpecKit command template references or includes this shared block.
Modify the shared instruction and verify the change propagates to all commands.

**Acceptance Scenarios**:

1. **Given** a shared markdown formatting instruction block,
**When** a SpecKit command template is loaded,
**Then** the code-block language rule is included in the prompt sent to the LLM.
2. **Given** a change to the shared instruction (e.g., adding a new language mapping),
**When** any SpecKit command is subsequently run,
**Then** the updated instruction is used without modifying individual command templates.

---

### User Story 5 — `taskstoissues` command preserves code-block language in GitHub Issues (Priority: P3)

As a developer converting tasks to GitHub Issues via `speckit.taskstoissues`,
I want any code blocks included in issue bodies to retain their language identifiers
so that the issues render correctly on GitHub.

**Why this priority**: `taskstoissues` transforms existing markdown rather than generating new content.
The risk of MD040 violations is lower since the source tasks.md should already be compliant (from User Story 2),
but the instruction serves as a safety net for any code blocks the LLM adds during issue creation.

**Independent Test**: Run `speckit.taskstoissues` on a `tasks.md` that contains code blocks with language identifiers.
Verify the resulting GitHub Issues preserve the language identifiers in their body markdown.

**Acceptance Scenarios**:

1. **Given** a `tasks.md` with properly labeled code blocks,
**When** `speckit.taskstoissues` creates GitHub Issues,
**Then** the code blocks in each issue body retain their language identifiers.

---

### Edge Cases

- What happens when the LLM generates a code block where no obvious language applies
(e.g., pseudo-code, free-form diagrams, or plain output)?
The instruction MUST specify a fallback language (`text`) for these cases.
- What happens when a code block contains mixed content (e.g., shell commands interleaved with output)?
The instruction MUST provide guidance to use the primary language (`bash` for shell sessions)
rather than omitting the identifier.
- What happens when the SpecKit prompt template itself contains example code blocks in its instructional text?
These template code blocks MUST also have language identifiers to remain self-consistent with the rule.
- How does this interact with the existing pipeline remediation loop in `generate-spec-from-issue.sh`?
The remediation loop remains as a safety net but SHOULD be triggered less frequently for MD040 after this change.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All SpecKit command templates (`.specify/templates/commands/*.md`) MUST include an instruction
directing the LLM to specify a language identifier on every fenced code block it generates.
This requirement also applies to the hard-coded phase prompts in the GitHub Action pipeline script
(`.github/scripts/speckit-trigger/generate-spec-from-issue.sh` — e.g., `run_specify_phase`, `run_tasks_phase`)
and any inline fenced-code examples within those prompt strings.

- **FR-002**: The instruction MUST enumerate common language identifiers and their use cases:
`bash` for shell commands, `python` for Python code, `json` for JSON, `toml` for TOML,
`yaml` for YAML, `text` for plain text, diagrams, or ASCII art, and `markdown` for markdown examples.

- **FR-003**: The instruction MUST explicitly state that bare triple backticks (without a language) are never permitted.

- **FR-004**: The instruction MUST specify `text` as the fallback language for code blocks where no specific language applies.

- **FR-005**: The code-block instruction SHOULD be defined in a single shared location to avoid duplication
across the 9 SpecKit command templates. [NEEDS CLARIFICATION: should the shared instruction be a new file
(e.g., `.specify/memory/markdown-rules.md`) or appended to the existing constitution (`.specify/memory/constitution.md`)?]

- **FR-006**: The corresponding VS Code Copilot agent files (`.github/agents/speckit.*.agent.md`) MUST receive the same
instruction, either by direct inclusion or by reference to the shared block.

- **FR-007**: The `generate-spec-from-issue.sh` pipeline script MUST continue to include MD040 remediation as a fallback
for any violations that slip through despite the proactive instruction.

### Non-Functional Requirements

- **NFR-001**: The added instruction text MUST NOT increase any individual prompt template by more than 500 characters
to avoid materially impacting LLM context window usage.

- **NFR-002**: The instruction MUST be clear, unambiguous, and positioned prominently enough in each prompt
that LLMs consistently follow it (e.g., near the top of formatting rules, not buried at the end).

- **NFR-003**: The change MUST NOT break existing markdownlint configuration —
no `.markdownlint.json` files should be modified.

- **NFR-004**: The change MUST be backward-compatible —
existing specs, plans, and tasks files generated before this change are unaffected.

### Key Entities

- **SpecKit Command Template**: A markdown file in `.specify/templates/commands/` that defines the system prompt
and instructions for an LLM-driven SpecKit step.
There are 9 templates: `specify`, `plan`, `tasks`, `taskstoissues`, `implement`, `analyze`, `clarify`, `constitution`, `checklist`.

- **VS Code Copilot Agent File**: A markdown file in `.github/agents/` that mirrors a command template
for use in VS Code Copilot Chat. Each `speckit.*.agent.md` corresponds to a command template.

- **Shared Instruction Block**: A centralized definition of markdown formatting rules
(including the code-block language rule) that is referenced by all SpecKit command templates.
This may be a new file or an addition to the existing constitution.

- **Pipeline Remediation Loop**: The LLM-based post-processing step in `generate-spec-from-issue.sh`
that reactively fixes markdownlint violations (including MD040) in generated artifacts.
This remains as a safety net.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of SpecKit command templates (9 of 9) include or reference
the code-block language instruction after implementation.

- **SC-002**: Running `speckit.specify` on 5 diverse feature descriptions produces zero MD040 violations
in the generated `spec.md` files without the pipeline remediation loop intervening.

- **SC-003**: For newly generated artifacts, the first `markdownlint-cli2` run (before any remediation loop iteration)
reports zero MD040 (fenced-code-language) violations
(i.e., MD040 violations are prevented at generation time, not fixed after the fact).

- **SC-004**: The code-block instruction is defined in exactly 1 shared location (not duplicated across templates),
reducing future maintenance cost to a single edit for formatting rule changes.

- **SC-005**: All existing markdownlint checks (`npx markdownlint-cli2 "**/*.md"`) continue to pass
after the prompt changes — no regressions introduced.

---
*Generated by Copilot SDK (claude-opus-4.6)*
