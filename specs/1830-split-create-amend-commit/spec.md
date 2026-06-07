# Feature Specification: Split create vs. amend commit title parameters & transparency logging

**Feature Branch**: `speckit/1830/phase-1-specify`
**Created**: 2026-06-07
**Status**: Draft
**Source Issue**: #1830 (<https://github.com/ayaiayorg/agentic-devtools/issues/1830>)

## Problem Statement

The `agdt-git-save-work` command currently accepts a single commit message source — the `commit_message` state key or the `--commit-message` CLI flag — regardless of whether the operation will
create a new commit or amend an existing one. This means an agent or user provides the same parameter in both paths, with no explicit signal of intent. When the command silently decides to amend
(based on `should_amend_instead_of_commit` heuristics), the caller has no indication that the existing commit message will be replaced.

Two concrete problems result from this design:

1. **Ambiguous intent for agents**: An AI agent setting `commit_message` cannot express whether it expects to create a brand-new commit or to overwrite the title of an existing one. If the heuristic
   makes the wrong decision the result is either an unintended amend that discards a carefully composed prior title, or an unintended new commit that breaks the single-commit-per-branch policy.

2. **No transparency on the resolved message**: Neither `create_commit` nor `amend_commit` currently prints the full final commit message before executing. Agents reviewing their own run logs, and
   humans auditing CI output, have no visible record of what title was actually committed. For amend operations there is also no before/after diff, so it is impossible to determine what changed
   without running a separate `git log` command.

This feature addresses both problems by introducing dedicated parameters for the two commit paths and adding mandatory transparency logging at every commit point.

## User Scenarios & Testing

### User Story 1 — New Commit via `--commit-message-title` (Priority: P1)

As an AI agent or developer creating the first commit ahead of `main` on a branch, I want to pass
`--commit-message-title "feat([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): add feature"` to `agdt-git-save-work` so that the system creates a new commit
using that title (combined with the body from the existing `commit_message` content after the first line), with no risk of accidentally amending a commit that is already ahead of `main`.

**Why this priority**: This is the primary new-commit path for all AI agent workflows. Providing an explicit, intent-declaring parameter eliminates the ambiguity of the existing heuristic and is the
foundational input for downstream transparency logging.

**Independent Test**: On a branch with no commits ahead of `main`, invoke
`agdt-git-save-work --commit-message-title "feat([#99](https://github.com/ayaiayorg/agentic-devtools/issues/99)): test title"` and verify: (a) a new commit is created, (b) the resolved final
message is printed to stdout before the commit executes, and (c) the commit message title matches the supplied value.

**Acceptance Scenarios**:

1. **Given** a branch with no commits ahead of `main` and
   `--commit-message-title "feat([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): add feature"` is supplied,
   **When** `agdt-git-save-work` runs, **Then** a new commit is created with
   that title and the resolved commit message is printed to stdout immediately before the commit executes.

2. **Given** `--commit-message-title` is supplied alongside a `commit_message` state key, **When** the command resolves the message, **Then** the CLI flag takes precedence over the state key.

3. **Given** neither `--commit-message-title`, `--overwrite-commit-message-title`, nor `commit_message` is available, **When** `agdt-git-save-work` runs, **Then** the command exits with a non-zero
   status and prints a clear error message identifying which parameter is required.

---

### User Story 2 — Amend Commit via `--overwrite-commit-message-title` (Priority: P1)

As an AI agent or developer amending a commit, I want to pass
`--overwrite-commit-message-title "fix([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): correct description"` to `agdt-git-save-work` so that the intent to overwrite is explicit,
and the system does not silently apply the new title as a fresh commit.

**Why this priority**: Without an explicit overwrite flag, agents cannot express intent unambiguously. The `--overwrite-commit-message-title` parameter is the counterpart to `--commit-message-title`
and together they form the complete, intent-explicit parameter model required by the issue.

**Independent Test**: On a branch with at least one commit ahead of `main`, invoke
`agdt-git-save-work --overwrite-commit-message-title "fix([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): new title"` and verify: (a) the command amends rather than creates
a new commit, (b) stdout includes the before (old) and after (new) commit message titles, and (c) the amended commit title matches the supplied value.

**Acceptance Scenarios**:

1. **Given** a branch with at least one commit ahead of `main` and
   `--overwrite-commit-message-title "fix([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): new title"`
   is supplied, **When** `agdt-git-save-work` runs, **Then** the existing commit ahead of `main` is amended
   with the new title and a before/after diff of the commit message titles is printed to stdout.

2. **Given** `--overwrite-commit-message-title` is supplied, **When** the command determines the operation type, **Then** it always amends regardless of the `should_amend_instead_of_commit` heuristic
   result — the explicit parameter overrides the heuristic.

3. **Given** `--overwrite-commit-message-title` is supplied but the branch has no commits ahead of
   `main` to amend, **When** the command attempts to amend, **Then** it exits with a non-zero status and a
   clear error message explaining that there is no commit to amend.

---

### User Story 3 — Transparency Logging of Final Resolved Commit Message (Priority: P1)

As an AI agent reviewing its own run log, or a developer auditing CI output, I want to see the full resolved final commit message printed to stdout on every `agdt-git-save-work` execution — both
create and amend — so that I can confirm exactly what was committed without running a separate `git log` command.

**Why this priority**: The issue explicitly requires that the resolved final message is always printed. This is the minimal transparency requirement that applies to all commit paths. Without it,
agents cannot verify their own output.

**Independent Test**: Run `agdt-git-save-work` with `--commit-message-title` on a clean branch and capture stdout. Verify that the full resolved commit message (title + body) appears in stdout
between a clearly identifiable delimiter before the `git commit` command runs.

**Acceptance Scenarios**:

1. **Given** `agdt-git-save-work` is about to create a new commit, **When** the command runs, **Then** the full resolved commit message is printed to stdout with a separator line before the commit
   executes (not after), so that log output is present even if the commit fails.

2. **Given** `agdt-git-save-work` is about to amend an existing commit, **When** the command runs, **Then** the full resolved new commit message is printed to stdout before the amend executes.

3. **Given** `--dry-run` is specified, **When** the command prints the resolved message, **Then** the output is identical in format to the non-dry-run case (the message is always printed regardless of
   the dry-run flag; the dry-run only suppresses the actual git command).

---

### User Story 4 — Before/After Diff on Amend/Overwrite (Priority: P1)

As an AI agent or developer performing an amend, I want to see a clear diff of the old and new commit message titles printed to stdout, so that I can confirm the change was intentional and trace any
unintended modifications during a post-run audit.

**Why this priority**: The issue acceptance criteria explicitly require a before/after diff for amend/overwrite operations. This is the key audit transparency mechanism for agentic commit workflows.

**Independent Test**: Create a branch with one commit with title
`feat([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): original`. Run
`agdt-git-save-work --overwrite-commit-message-title "feat([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): updated"`. Verify that stdout contains
lines showing the old title prefixed with `-` and the new title prefixed with `+` (or an equivalent clearly labeled before/after format).

**Acceptance Scenarios**:

1. **Given** an existing commit with title
   `feat([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): original title` and
   `--overwrite-commit-message-title "feat([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): updated title"`
   is supplied, **When** the command runs, **Then** stdout
   includes both the old title (prefixed with a `-` line) and the new title (prefixed with a `+` line), or equivalent labeled before/after lines, before the amend executes.

2. **Given** the old and new titles are identical, **When** the command runs, **Then** stdout still prints the before/after block (with no visible diff lines) to confirm no change occurred, rather
   than silently suppressing the diff.

3. **Given** the branch has no commits ahead of `main` (nothing to read as
   "before"), **When** an amend is requested, **Then** the command exits with a
   non-zero status and an error message before any git operation — no partial
   output is printed that could mislead the caller.

---

### User Story 5 — State Key Equivalents for Both Parameters (Priority: P2)

As an AI agent using the state-based workflow, I want to set `commit_message_title` or `overwrite_commit_message_title` in state instead of supplying CLI flags, so that I can integrate with the
existing state-driven command model without requiring changes to the agent invocation scripts.

**Why this priority**: State-based invocation is the standard pattern for all `agdt-*` commands. CLI flags are the primary interface but state keys must be supported as a fallback so that agent
instruction files do not need to be updated to pass new flags explicitly.

**Acceptance Scenarios**:

1. **Given** `commit_message_title` is set in state (and no CLI flags are provided), **When**
   `agdt-git-save-work` runs on a branch with no commits ahead of `main`, **Then** it reads the title from
   state and
   creates a new commit, with the resolved message printed to stdout.

2. **Given** `overwrite_commit_message_title` is set in state (and no CLI flags are provided), **When**
   `agdt-git-save-work` runs on a branch with at least one commit ahead of `main`, **Then** it reads the
   title from
   state and amends the commit, printing the before/after diff to stdout.

3. **Given** both a CLI flag and a matching state key are present, **When** the command resolves the message, **Then** the CLI flag takes precedence over the state key.

---

### User Story 6 — Backward Compatibility with `commit_message` State Key (Priority: P2)

As an agent or developer using the existing `commit_message` state key workflow, I want `agdt-git-save-work` to continue working exactly as before when neither `--commit-message-title` nor
`--overwrite-commit-message-title` is supplied, so that no existing agent instructions or workflows break.

**Why this priority**: Backward compatibility is mandatory for incremental adoption. All currently deployed workflows set `commit_message` and must not be broken by this change.

**Acceptance Scenarios**:

1. **Given** only `commit_message` is set in state and no new flags are provided, **When** `agdt-git-save-work` runs, **Then** the behavior is identical to the current implementation —
   `should_amend_instead_of_commit` determines the operation type and the existing message is used as-is (while also being printed to stdout per US3).

2. **Given** the `--commit-message` CLI flag is supplied (the current flag), **When** the command runs, **Then** it continues to work as before with the heuristic-driven amend detection.

## Requirements

### Functional Requirements

- **FR-001**: `agdt-git-save-work` MUST accept a `--commit-message-title` CLI flag whose presence signals intent to create a **new** commit. When this flag is present, the command MUST skip
  `should_amend_instead_of_commit` and always call `create_commit`. Validation order MUST be deterministic: (1) reject branches with commits ahead of `main` with an error directing the caller to use
  `--overwrite-commit-message-title`; then (2) resolve the body from the existing `commit_message` body portion. Scope note: this change does **not** add a new file-read source in
  `agdt-git-save-work`; if upstream automation renders `commit_message` from a markdown file, that remains the body source indirectly through `commit_message`. If `commit_message` cannot be resolved
  (from CLI or state), exit with status 1 and print an error to stderr explaining that a body source is required. This prevents creating a second commit in violation of the single-commit-per-PR
  policy.

- **FR-002**: `agdt-git-save-work` MUST accept a `--overwrite-commit-message-title` CLI flag whose presence signals intent to **amend** the existing commit. When this flag is present, the command
  MUST skip `should_amend_instead_of_commit` and always call `amend_commit`. If the branch has no commits ahead of `main`, the command MUST exit with status 1 and print an error to stderr. If both
  create-intent and amend-intent signals are present in the same invocation (CLI flags, state keys, or mixed), the command MUST exit with status 1 and print a single stable conflict error message that
  explicitly says to provide exactly one of `--commit-message-title` or `--overwrite-commit-message-title`, instead of choosing one path implicitly.

- **FR-003**: State keys `commit_message_title` (str) and `overwrite_commit_message_title` (str) MUST be read as fallback sources when the corresponding CLI flags are absent. CLI flags take
  precedence over state keys. The existing `commit_message` state key continues to serve as the legacy fallback when neither new key/flag is present.

- **FR-004**: On every `create_commit` call, the system MUST print the full resolved commit message to stdout, enclosed in separator lines (e.g., `--- Commit Message ---` / `---`), before the
  `git commit` command is executed. This requirement applies equally in dry-run mode (the message is always printed; only the git command is suppressed).

- **FR-005**: On every `amend_commit` call, the system MUST print: (a) the old commit message title derived from the first line of `get_last_commit_message()` output, prefixed with a `-` character;
  (b) the new commit message title, prefixed with a `+` character; and (c) the full resolved new commit message, before the `git commit --amend` command is executed. The before/after block MUST
  appear even when old and new titles are identical.

- **FR-006**: All existing invocations using `--commit-message` CLI flag or `commit_message` state key MUST continue to work without modification. The heuristic-based `should_amend_instead_of_commit`
  MUST remain the default decision path when neither `--commit-message-title` nor `--overwrite-commit-message-title` is present.

- **FR-007**: The `amend_cmd` entry point (`agdt-git-amend`) MUST also adopt the transparency logging requirements from FR-004 and FR-005.

- **FR-008**: Documentation in `commands.py` docstrings for `commit_cmd` and `amend_cmd` MUST be updated to describe the new flags, state keys, and logging behavior in the "State keys" and "CLI
  args" sections, so that AI agents consuming the command docs receive accurate guidance.

### Non-Functional Requirements

- **NFR-001**: The transparency logging added by FR-004 and FR-005 MUST complete synchronously before the git command runs, with negligible overhead on overall `agdt-git-save-work` wall-clock time.

- **NFR-002**: The implementation MUST maintain 100% test coverage on `commands.py`, `operations.py`, and any new helper functions introduced (per the project's `--cov-fail-under=100` pytest
  configuration).

- **NFR-003**: The new CLI flags MUST be documented in the agent-facing docs (command docstrings and any relevant `.github/agents/` instruction files that reference `agdt-git-save-work`) so that
  AI agents receive up-to-date guidance when working on issues.

## Success Criteria

- **SC-001**: `agdt-git-save-work --commit-message-title "..."` creates a new commit and prints the resolved message to stdout on a branch with no commits ahead of `main`.

- **SC-002**: `agdt-git-save-work --overwrite-commit-message-title "..."` amends the existing commit and prints the before/after diff to stdout on a branch with at least one commit ahead of `main`.

- **SC-003**: All existing usages of `commit_message` state key continue to work without modification, confirmed by existing unit tests passing without change.

- **SC-004**: New unit tests cover: (a) `--commit-message-title` new-commit path with logging assertion, (b) `--overwrite-commit-message-title` amend path with before/after diff assertion, (c) state
  key fallback for both new parameters, (d) error when `--overwrite-commit-message-title` is used on a branch with no commits ahead of `main`, and (e) both new paths in dry-run mode.

- **SC-005**: `markdownlint` passes on all modified documentation files, including updated command docstrings exported as markdown.

---

*Generated by Copilot SDK (claude-opus-4.6)*
