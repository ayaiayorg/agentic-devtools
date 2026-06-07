# Feature Specification: Dedicated commit-body.md for Commit Body

**Feature Branch**: `speckit/1831/phase-1-specify`
**Created**: 2026-06-07
**Status**: Draft
**Source Issue**: #1831 (<https://github.com/ayaiayorg/agentic-devtools/issues/1831>)

## Problem Statement

The current `agentic-devtools` commit workflow stores the entire commit message — both title and body — in a single `commit_message` state key. This flat string approach introduces significant
friction when AI agents or human developers need to compose detailed, multi-paragraph commit bodies with rich formatting such as bullet lists, nested content, or structured metadata. The state key
mechanism was designed for short scalar values; attempting to pack a multi-line markdown document into a JSON string value results in awkward escaping, loss of readability when inspecting state via
`agdt-show`, and an inability to use standard text editors or IDE markdown preview for body composition.

Furthermore, the single-key approach makes it impossible to attach structured metadata — such as checklist completion status, review notes, or issue cross-references — to the commit body in a
machine-parseable way. AI agents frequently need to embed structured data alongside prose in commit messages, but without a formal mechanism like YAML frontmatter, this data must be flattened into
ad-hoc text formats that are fragile to parse and easy to corrupt. The lack of separation between title and body also means that agents must carefully manage newline placement within a single string
value, which is error-prone and leads to malformed commit messages.

The proposed solution introduces a dedicated `commit-body.md` file located within the per-worktree state directory at `.agdt/workflows/{identity}/{worktree_key}/files/commit-body.md`. This file is
inherently gitignored (the entire `.agdt/workflows` directory is excluded from version control), supports full markdown editing with optional YAML frontmatter for structured metadata, and cleanly
separates the commit title (still passed via CLI or state) from the commit body (always read from this file). A new `agdt-commit-body-show` command enables AI agents to inspect the current body
content before committing, providing a verification checkpoint in the automated workflow.

## User Scenarios & Testing

### User Story 1 - Commit Body Injection into Git Commit (Priority: P1)

As an AI agent executing the `agdt-git-save-work` workflow, I need the commit body to be automatically read from `commit-body.md` and injected after the commit title so that I can compose rich
multi-paragraph commit messages without encoding issues or escaping problems in the state JSON.

**Why this priority**: This is the core behavior change that enables the entire feature. Without automatic body injection, the file has no effect on the commit workflow and the feature delivers no
value. Every other user story depends on this foundational integration working correctly.

**Independent Test**: Can be fully tested by creating a `commit-body.md` file with known content, running `agdt-git-save-work`, and verifying the resulting git commit message contains the title
followed by a blank line followed by the body content verbatim.

**Acceptance Scenarios**:

1. **Given** a `commit-body.md` file exists at the expected worktree path with markdown content including bullet lists and nested paragraphs, **When** `agdt-git-save-work` executes the commit
   operation, **Then** the resulting git commit message consists of the title from the `commit_message` state key followed by a blank separator line followed by the full body content from
   `commit-body.md`.

2. **Given** no `commit-body.md` file exists at the expected worktree path, **When** `agdt-git-save-work` executes the commit operation, **Then** no additional body is injected and the existing
   `commit_message` state value is used unchanged, maintaining full backward compatibility with existing workflows that already store a multi-line commit message.

3. **Given** a `commit-body.md` file exists but contains only whitespace or is empty, **When** `agdt-git-save-work` executes, **Then** the empty body is treated as absent: no additional body is
   injected and the existing `commit_message` state value is used unchanged.

---

### User Story 2 - Show Command for Body Inspection (Priority: P1)

As an AI agent preparing to commit changes, I need to inspect the current commit body content via a CLI command so that I can verify the body is correct and complete before triggering the irreversible
commit operation.

**Why this priority**: AI agents operate without visual feedback. Without a show command, an agent cannot verify body content before committing, which could result in malformed or incomplete commit
messages that require amending. This verification step is essential for reliable autonomous operation.

**Independent Test**: Can be fully tested by writing known content to `commit-body.md`, running `agdt-commit-body-show`, and asserting the structured stdout includes the body content verbatim (with
any YAML frontmatter presented in its own clearly delineated section).

**Acceptance Scenarios**:

1. **Given** a `commit-body.md` file exists with markdown body content and no YAML frontmatter, **When** `agdt-commit-body-show` is executed, **Then** the full body content is printed to stdout with a
   clear header indicating the file path and content length.

2. **Given** a `commit-body.md` file exists with YAML frontmatter followed by markdown body content, **When** `agdt-commit-body-show` is executed, **Then** both the parsed frontmatter (as key-value
   pairs) and the body content are displayed in clearly delineated sections.

3. **Given** no `commit-body.md` file exists, **When** `agdt-commit-body-show` is executed, **Then** a message is printed to stderr indicating no commit body file was found, and the command exits with
   a non-zero exit code.

---

### User Story 3 - YAML Frontmatter for Structured Metadata (Priority: P2)

As an AI agent managing a multi-step workflow, I need to embed structured metadata (such as checklist completion status, review flags, or cross-references) in the commit body file's YAML frontmatter
so that other tools and workflow steps can read this metadata programmatically without parsing free-form markdown.

**Why this priority**: While the core body injection (P1) delivers immediate value, frontmatter parsing enables advanced automation scenarios like checklist-aware commits and workflow state
propagation. It builds on the P1 foundation but is not required for the minimum viable feature.

**Independent Test**: Can be tested by writing a `commit-body.md` with YAML frontmatter containing known keys and values, then calling the frontmatter parsing function and asserting the returned
dictionary matches expected structure. Independent of git operations.

**Acceptance Scenarios**:

1. **Given** a `commit-body.md` with valid YAML frontmatter between `---` delimiters containing keys like `checklist_items_completed: [1, 2, 3]` and `review_status: approved`, **When** the frontmatter
   parsing function is invoked, **Then** a Python dictionary is returned with correctly typed values (list of integers, string).

2. **Given** a `commit-body.md` with no frontmatter (content starts immediately without `---` delimiters), **When** the frontmatter parsing function is invoked, **Then** an empty dictionary is
   returned and the entire file content is treated as the body.

3. **Given** a `commit-body.md` with malformed YAML frontmatter (invalid YAML syntax between `---` delimiters), **When** the frontmatter parsing function is invoked, **Then** a warning is printed to
   stderr, the frontmatter is treated as empty, and the entire file content (including the malformed frontmatter section) is used as the body to avoid data loss.

---

### User Story 4 - Worktree Isolation of Commit Body Files (Priority: P2)

As a developer working across multiple git worktrees on different feature branches simultaneously, I need each worktree to have its own independent `commit-body.md` file so that commit body content
for one branch never leaks into or conflicts with another branch's commit workflow.

**Why this priority**: Multi-worktree isolation is a core architectural property of `agentic-devtools`. Without it, parallel work on multiple issues would be impossible. However, since the file lives
within the already-isolated `.agdt/workflows/{identity}/{worktree_key}/` directory, this is largely inherited behavior that needs verification rather than new implementation.

**Independent Test**: Can be tested by simulating two different worktree key directories, writing different content to each `commit-body.md`, and verifying that reads from each path return only the
content written to that specific path.

**Acceptance Scenarios**:

1. **Given** two active worktrees with different worktree keys, each having a `commit-body.md` with distinct content, **When** `agdt-commit-body-show` is executed in each worktree context, **Then**
   only the content specific to that worktree is displayed.

2. **Given** a `commit-body.md` exists in worktree A but not in worktree B, **When** `agdt-git-save-work` is executed in worktree B's context, **Then** no additional body is injected, the existing
   `commit_message` value for worktree B is used unchanged, and worktree A's body file is never read.

---

### Edge Cases

The following edge cases must be handled gracefully by the implementation:

What happens when the `files/` subdirectory does not exist yet? Read paths such as `agdt-git-save-work` and `agdt-commit-body-show` must treat that the same as a missing `commit-body.md`, and any
helper that provisions the path for creating `commit-body.md` must create `files/` on demand. What happens when `commit-body.md` contains only YAML frontmatter with no body after the closing `---`?
The body should be treated as empty (equivalent to absent): no additional body is injected and `commit_message` is used unchanged. How does the system handle extremely large
body files (e.g., accidentally writing a log file)? A reasonable size limit or warning should be considered. What happens if the file has a BOM (byte-order mark) or non-UTF-8 encoding? The system
should read as UTF-8 and fail gracefully with a clear error if decoding fails.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST read the commit body from `.agdt/workflows/{identity}/{worktree_key}/files/commit-body.md` when the file exists, map that body text to the `commitMessageBody`
  template variable, and inject it after the commit title (separated by a blank line) during `agdt-git-save-work` commit creation and amend operations. When `commit-body.md` is present and non-empty,
  only the first line of `commit_message` is treated as the commit title.

- **FR-002**: The system MUST treat the commit body as absent when `commit-body.md` does not exist, is empty, or contains only whitespace. In those cases, no additional body may be appended and the
  existing `commit_message` value MUST be used unchanged, maintaining full backward compatibility with existing workflows that already store the full commit message in that state key.

- **FR-003**: The system MUST provide an `agdt-commit-body-show` CLI command registered as a console script entry point that prints the current commit body content to stdout, displays parsed YAML
  frontmatter separately, and exits with code 0 on success or non-zero when no body file exists.

- **FR-004**: The system MUST parse optional YAML frontmatter delimited by `---` lines at the start of `commit-body.md`, returning the parsed metadata as a Python dictionary accessible to other tools
  and workflow steps. When frontmatter parses successfully, the parsed frontmatter MUST be excluded from the commit body text injected into the git message. Malformed frontmatter behavior is
  defined by FR-007.

- **FR-005**: The system MUST scope the `commit-body.md` file to the per-worktree state directory (inheriting the existing `.agdt/workflows/{identity}/{worktree_key}/` isolation), ensuring that commit
  body content is never shared across worktrees and never committed to git.

- **FR-006**: The system MUST treat a missing `files/` subdirectory within the worktree state directory as equivalent to a missing `commit-body.md` file for `agdt-git-save-work` and
  `agdt-commit-body-show`. Commands or helpers that create or edit `commit-body.md` for the current worktree MUST create `files/` on demand to prevent file-not-found errors during initial usage.

- **FR-007**: The system MUST handle malformed YAML frontmatter gracefully by emitting a warning to stderr and treating the entire file content as the body (no frontmatter parsed), ensuring that
  invalid YAML never causes a commit failure or data loss.

- **FR-008**: The system MUST read `commit-body.md` as UTF-8 encoded text and produce a clear error message to stderr if the file cannot be decoded, exiting with a non-zero code rather than producing
  a corrupt commit message.

- **FR-009**: The `agdt-commit-body-show` command MUST display the file path, content length in characters, and whether YAML frontmatter was detected, in addition to the body content itself, providing
  AI agents with sufficient context for verification.

- **FR-010**: The system MUST update user-facing documentation to define `commit-body.md` as the canonical commit-body workflow, including where the file lives, how it is consumed by
  `agdt-git-save-work`, and when the `commit_message` title is still used.

### Non-Functional Requirements

- **NFR-001**: Reading and parsing `commit-body.md` (including YAML frontmatter extraction) MUST complete in under 100 milliseconds for files up to 100KB, ensuring no perceptible delay in the
  `agdt-git-save-work` workflow.

- **NFR-002**: The `agdt-commit-body-show` command MUST follow the same output formatting conventions as other `agdt-*` CLI commands (clear headers, stderr for errors, stdout for content) to maintain
  CLI UX consistency.

- **NFR-003**: All new code paths MUST achieve 100% branch coverage in unit tests, consistent with the repository's existing CI enforcement policy.

- **NFR-004**: The feature MUST NOT introduce any new external dependencies beyond the Python standard library and packages already in the project's dependency set (PyYAML or equivalent must already
  be available, or frontmatter parsing must use only stdlib).

- **NFR-005**: The implementation MUST follow the existing 1:1:1 test structure policy, with test files placed under `tests/unit/` mirroring the source file path hierarchy.

### Key Entities

- **commit-body.md**: A markdown file containing the commit message body with optional YAML frontmatter. Lives at `.agdt/workflows/{identity}/{worktree_key}/files/commit-body.md`. Never tracked by
  git.
- **YAML Frontmatter**: Optional structured metadata block at the start of `commit-body.md`, delimited by `---` lines. Parsed into a Python dictionary for programmatic access.
- **commitMessageBody**: The template variable name used when injecting the body content into the final commit message (body text only, frontmatter excluded).

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of existing `agdt-git-save-work` tests continue to pass without modification when no `commit-body.md` file is present, confirming zero backward-compatibility regressions.

- **SC-002**: The new `agdt-commit-body-show` command executes and returns output in under 200 milliseconds for body files up to 50KB, measured across 10 consecutive invocations on the CI runner.

- **SC-003**: Unit test coverage for all new source files (body reading, frontmatter parsing, show command) achieves 100% branch coverage as verified by the repository coverage gate and targeted
  `agdt-test-pattern` checks against the corresponding `tests/unit/` 1:1:1 test paths.

- **SC-004**: 100% of commit body round-trip scenarios covered by the integration test suite (write file → commit → inspect git log) preserve the body content byte-for-byte, allowing only one
  normalization rule: comparisons may ignore a single final `\n` at end-of-file (present or absent), with no other whitespace or newline transformations, as verified by integration test assertions.

- **SC-005**: The feature adds zero new external package dependencies to `pyproject.toml`, keeping the installation footprint unchanged.

- **SC-006**: Documentation pages and command guidance that describe commit message composition explicitly reference `commit-body.md` as the canonical body source and pass docs validation checks in CI.

---
*Generated by Copilot SDK (claude-opus-4.6)*
