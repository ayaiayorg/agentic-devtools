# Spec: SpecKit prompts: Require language specifier on fenced code blocks

## Summary

SpecKit prompt templates must consistently instruct the model to include a language specifier on
every fenced code block it produces. The instruction must be defined once in a dedicated shared
markdown file and then loaded into all in-scope templates and runtime-generated prompts using a
consistent, minimal inclusion mechanism.

## Problem

Today, fenced code block language guidance is either absent, inconsistently applied, or embedded
only in limited prompt sources such as the constitution. Because the constitution is not loaded
by all relevant templates, generated outputs can omit language identifiers on fenced code blocks,
reducing readability and downstream tooling compatibility.

## Scope

This spec covers:

- command templates (all files matching `.specify/templates/commands/*.md`),
- agent files (all files matching `.github/agents/speckit.*.agent.md`),
- the pipeline/runtime prompt assembly path,
- the dedicated shared markdown rules file used to inject the guidance.

This spec does not require broader markdown-style enforcement beyond fenced code block language tagging.

## Clarified decisions

1. **Shared location** → New repo file `.specify/memory/markdown-rules.md`; in prompt text and template instructions, reference it as virtual path `/memory/markdown-rules.md`.
2. **Path mapping** → `/memory/markdown-rules.md` maps to `.specify/memory/markdown-rules.md` for command templates, runtime-generated prompts, and agent files.
3. **Inclusion mechanism** → Explicit one-line load instruction in each template's context step using `/memory/markdown-rules.md`.
4. **Pipeline script** → Read `.specify/memory/markdown-rules.md` at runtime using `cat` (bash) or `Get-Content -Raw` (PowerShell) and inject its contents into prompt strings.
5. **Agent files** → Same one-line load instruction as command templates, using virtual path `/memory/markdown-rules.md`; agent runtimes must provide the same `/memory/*` mapping for these references.
6. **NFR-001 scope** → 500-char limit applies to shared file content; reference line length ≤ 100 chars (counted separately).

## User stories

### User Story 1 - Consistent markdown output guidance

As a template author, I want markdown output rules for fenced code blocks to live in one shared file so that all relevant prompts stay consistent and easy to maintain.

**Acceptance criteria**

- A dedicated shared file exists at `.specify/memory/markdown-rules.md`.
- The shared file contains the normative rule requiring language specifiers on fenced code blocks.
- Templates do not duplicate the full rule text inline when the shared file can be referenced instead.

### User Story 2 - Reliable prompt behavior across templates

As a user of SpecKit prompts, I want every in-scope prompt template to load the same markdown rule so that generated code fences consistently include language identifiers.

**Acceptance criteria**

- Every in-scope command template includes the one-line load instruction using `/memory/markdown-rules.md` in the appropriate context/setup section.
- Every in-scope agent file includes the same style of one-line load instruction using `/memory/markdown-rules.md`.
- In the assembled prompt text, either the injected markdown rule text or an explicit load instruction referencing `/memory/markdown-rules.md` appears before the generation instructions begin.

### User Story 3 - Runtime parity for generated prompts

As a maintainer of the pipeline script, I want runtime-generated prompts to inject the same shared markdown rule content so that CLI/pipeline execution matches static template behavior.

**Acceptance criteria**

- The pipeline script reads `.specify/memory/markdown-rules.md` using `cat` (bash) or `Get-Content -Raw` (PowerShell).
- The script injects the file contents into the prompt string used at runtime.
- If the shared file is missing, the script degrades gracefully and does not crash unexpectedly.

### User Story 4 - Actionable Phase 3 implementation scope

As an implementer planning Phase 3, I want this spec to explicitly cover command templates, agent files, and the pipeline script so that no prompt source is missed.

**Acceptance criteria**

- The scope explicitly includes command templates, agent files, and pipeline/runtime assembly.
- The requirements identify both the shared-file location and the inclusion/injection mechanisms.
- Success criteria verify template coverage and pipeline behavior.

## Functional requirements

### FR-001 - Pipeline injection mechanism (Must)

The pipeline/runtime prompt assembly path must read the contents of `.specify/memory/markdown-rules.md` using `cat` (bash) or the
platform-equivalent command (`Get-Content -Raw` for PowerShell) per decision #4, and inject those contents into the generated prompt
string used for model execution.

### FR-002 - Shared markdown rules file (Must)

The markdown rule requiring language specifiers on fenced code blocks must be stored in a dedicated shared file at `.specify/memory/markdown-rules.md`.

### FR-003 - Normative rule content (Must)

The shared markdown rules file must instruct the model to include an explicit language specifier on every fenced code block it emits.
When a specific language can be identified from context, the model must use that language label; otherwise, it must use an explicit fallback label such as `text`.
Bare fenced code blocks without a language specifier are not permitted.

### FR-004 - Template usage model (Must)

In-scope templates must reference the shared markdown rules through a one-line load instruction using `/memory/markdown-rules.md` rather than duplicating the full markdown rule content inline.

### FR-005 - Source of truth (Must)

`.specify/memory/markdown-rules.md` is the authoritative source of truth for this markdown rule; the constitution is not the primary storage location for this requirement.

### FR-006 - Agent file coverage (Must)

Agent files that participate in prompt construction must include the same one-line load instruction pattern using `/memory/markdown-rules.md` as command templates.

### FR-007 - Graceful degradation (Should)

If `.specify/memory/markdown-rules.md` is unavailable at runtime, the affected template or
pipeline path must log a clear warning to stderr, continue without terminating the workflow,
and skip injecting markdown rules from that file.

### FR-008 - Placement in all in-scope prompt sources (Must)

The one-line load instruction must be added in the context/setup section of every in-scope template
and agent file so the markdown rule is presented before the model is asked to generate substantive
output.

## Non-functional requirements

### NFR-001 - Size budget

The content of `.specify/memory/markdown-rules.md` must be limited to 500 characters maximum
(including newlines/formatting). The one-line reference/load instruction added to any template
or agent file must be ≤ 100 characters (counted separately). The combined overhead per prompt
source must not exceed 600 characters.

### NFR-002 - Maintainability

The solution should minimize duplication by keeping the rule text in one shared file and using a standard one-line inclusion pattern across prompt sources.

### NFR-003 - Clarity

The wording in the shared file and in the one-line load instruction must be unambiguous so maintainers can easily identify where the markdown requirement comes from and how it is applied.

## Edge cases

- **Missing shared file**: If `.specify/memory/markdown-rules.md` does not exist, the pipeline/template path must degrade gracefully rather than hard-failing unexpectedly.
- **Constitution also contains related guidance**: The dedicated shared file remains the source of truth for this requirement even if similar wording exists elsewhere.
- **Non-code fenced blocks**: If the model produces a fenced block that is not code or no language
  can reasonably be inferred, the prompt guidance must require a fallback language identifier such as
  `text` rather than an unlabeled fenced block; code examples should always use the most specific
  determinable language identifier.
- **Partial rollout risk**: Updating only some templates is insufficient; all in-scope prompt sources must be covered for the change to be considered complete.

## Success criteria

### SC-001

A dedicated file exists at `.specify/memory/markdown-rules.md` and contains the markdown rule for fenced code block language specifiers.

### SC-002

All in-scope command templates include the one-line load instruction in the intended context/setup location using the `/memory/markdown-rules.md` virtual path.

### SC-003

All in-scope agent files include the one-line load instruction in the intended context/setup location using the `/memory/markdown-rules.md` virtual path.

### SC-004

The shared file content remains within the 500-character limit, and the combined file-plus-reference overhead remains within 600 characters per prompt source.

### SC-005

The document remains standalone and actionable by containing user stories, requirements, edge cases, and success criteria directly rather than referencing missing definitions elsewhere.

### SC-006

The pipeline/runtime path is verified to read the `.specify/memory/markdown-rules.md` file via `cat` (bash) or `Get-Content -Raw` (PowerShell) and inject its content into the prompt string used for execution.

### SC-007

For generated `spec.md`, `plan.md`, and `tasks.md` artifacts produced by the in-scope prompt flow,
`markdownlint-cli2` reports zero `MD040` (`fenced-code-language`) violations,
ideally on the initial generation pass before any remediation loop runs.

## Key entities

- **Shared markdown rules file**: `.specify/memory/markdown-rules.md` (mapped virtually to `/memory/markdown-rules.md` in prompts), the canonical source of the fenced code block language requirement.
- **One-line load instruction**: The standard short reference placed in each in-scope template or agent context/setup section to load the shared markdown rules.
- **Pipeline script**: The runtime assembly path that reads the shared file with `cat` (bash) or `Get-Content -Raw` (PowerShell) and injects its content into generated prompts.
- **In-scope prompt sources**: Command templates and agent files that participate in model prompt construction.
