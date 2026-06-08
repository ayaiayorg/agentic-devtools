# Feature Specification: Persist Commit Params and Rendered Messages to State

**Feature Branch**: `speckit/1832/phase-1-specify`  
**Created**: 2026-06-07  
**Status**: Draft  
**Input**: User description: "Persist commit params and rendered messages to state"  
**Source Issue**: #1832 (<https://github.com/ayaiayorg/agentic-devtools/issues/1832>)

## Clarifications

### Session 2026-06-08

- Q: Where in the `commit_cmd()` flow should the state persistence occur — immediately after
  the `create_commit()`/`amend_commit()` call returns (before rebase/push), or after the entire
  workflow (including push) succeeds? → A: Immediately after a successful non-dry-run
  `create_commit()`/`amend_commit()` operation returns (before rebase/push). The persistence
  records what was committed to git locally;
  push failures should not prevent state persistence since the commit itself exists in the local repository.
- Q: For FR-007's "single all-or-nothing update," should the implementation use
  `save_state_locked()` (file-locking variant) or the standard `save_state()`
  given that `agdt-git-save-work` already runs as a background task? → A: Use an
  exclusive-locking read/modify/write (e.g., `read_modify_write_state()` with a
  single lock across load→mutate→save), since multiple background
  tasks/processes can update state concurrently. This preserves the
  all-or-nothing guarantee without risking lost updates from interleaved writes.
- Q: When the `git.last_commit_message` fallback is used (FR-001, no `--commit-message` and empty `commit_message` state key), should `get_commit_message()` be modified in `core.py` or should the
  fallback logic live in `commit_cmd()` before calling `get_commit_message()`? → A: The fallback logic should live in `commit_cmd()` (in `commands.py`), checking `git.last_commit_message` from state
  before calling `get_commit_message()`. This keeps `get_commit_message()` as a simple state reader for the `commit_message` key and avoids coupling the fallback into the shared utility function.
- Q: Should `commit_message_title` (top-level key) be cleared/removed when `agdt-clear` is run, consistent with other top-level state keys? → A: Yes. `commit_message_title` is a standard top-level
  state key and MUST be cleared by `agdt-clear` like all other keys. No special handling is needed — `agdt-clear` already removes all keys.
- Q: Does FR-001's `git.last_commit_message` fallback apply only to amend operations (where reusing the prior message is natural) or also to new-commit operations on the same branch? → A: It applies
  to both new-commit and amend operations. The fallback fires when no `commit_message` is provided regardless of create-vs-amend path. In practice, under the single-commit-per-PR policy, this
  primarily benefits the amend path, but it is not restricted to it.

## Problem Statement

When `agdt-git-save-work` executes a commit or amend operation, `commit_message` is written to state as a pre-commit input parameter (whether supplied via state or `--commit-message`), but it is
set *before* the background task runs — not after the commit succeeds. There is no dedicated, authoritative snapshot of the **last successfully committed** message and its constituent parts
(title, body). Downstream tooling that needs to know exactly what was committed must therefore resort to re-parsing git log output.

Currently, an AI agent that creates a pull request after committing must either re-read the commit message from git (`git log -1 --format=%B`), reconstruct the title from memory, or rely on the user
to re-supply it. This is fragile because the agent may have lost conversational context, the worktree may have changed, or the commit message may have been auto-modified during the amend process.
There is no single authoritative place in the workflow state where an agent can look up "what did I just commit?" — a question that arises routinely during PR creation, Jira comment posting, and audit
logging.

The absence of persisted commit metadata also makes it harder to inspect the most recent commit's content without running git commands. The `all-background-tasks.json` file records that an
`agdt-git-save-work` task ran, but not the substantive content of the commit. When a session needs to know what was last committed — for example to understand why a PR title differs from the expected
commit message, or why an amend produced a different result — this requires manual git forensics rather than simple state inspection.

Finally, the commit message title (the first line of the commit message) is a high-value piece of metadata that downstream commands such as `agdt-create-pull-request` could reuse as a default PR
title. Today there is no mechanism to carry this forward automatically. This feature persists the title to both `commit_message_title` (for downstream reuse as data) and `git.last_commit_title`
(for debugging/audit visibility) after each commit or amend. In this spec, `commit_message_title` is a persisted output snapshot, not an implicit create/amend intent signal for subsequent
`agdt-git-save-work` invocations. With these keys persisted, subsequent commands gain access to sensible defaults without requiring the agent to redundantly specify them.

## User Scenarios & Testing

### User Story 1 - Agent Reuses Commit Title for PR Creation (Priority: P1)

An AI agent working through the `work-on-jira-issue` workflow commits code using `agdt-git-save-work` and then immediately proceeds to create a pull request. The agent expects the commit message title
to be available in state so that `agdt-create-pull-request` can use it as the default PR title without the agent having to re-specify it or parse git log output.

**Why this priority**: This is the most common end-to-end workflow — commit then create PR — and eliminating the redundant title specification reduces agent errors and simplifies prompt design. It
delivers immediate value to every agent session that follows the standard workflow.

**Independent Test**: Can be fully tested by running `agdt-git-save-work` with a known commit message, then verifying that both `agdt-get commit_message_title` and
`agdt-get git.last_commit_title` return the expected title string.
Delivers value by enabling downstream commands to consume the title without additional git operations.

**Acceptance Scenarios**:

1. **Given** an agent has set `commit_message` to
   <!-- markdownlint-disable-next-line MD013 -->
   `"feat([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): add webhook support\n\n- Implemented handler\n- Added tests\n\n[#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)"`
   and runs `agdt-git-save-work`, **When** the commit completes successfully, **Then** state key
   `commit_message_title` and `git.last_commit_title` both contain exactly
   `"feat([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): add webhook support"`.
2. **Given** an agent runs `agdt-git-save-work` which amends an existing commit with a new message, **When** the amend completes, **Then** both `commit_message_title` and
   `git.last_commit_title` are updated to reflect the new (amended) message title, not the original.
3. **Given** state key `git.last_commit_title` was persisted from a previous commit, **When** the agent runs `agdt-create-pull-request` without setting `title` explicitly, **Then** the PR creation
   command can read `git.last_commit_title` as a candidate default title.
4. **Given** a previous `agdt-git-save-work` invocation persisted `git.last_commit_message` as a
   full conventional commit message (title + footer with issue link), no `--commit-message` CLI
   argument is passed to the next invocation, and the `commit_message` state key is absent or
   empty, **When** the agent runs `agdt-git-save-work` again, **Then** the command uses the
   persisted `git.last_commit_message` value as the default commit message (preserving the full
   message including footer), avoiding the need for the agent to re-specify it and ensuring the
   commit convention is not violated.

---

### User Story 2 - Debugging Last Commit (Priority: P2)

A human developer inspects the workflow state file to understand what was most recently committed in a session. They expect to find the full rendered commit message and its body stored in state,
making it possible to verify commit content without running git commands in the worktree (which may have since changed branches or been deleted).

**Why this priority**: Being able to inspect the last commit's content from state is important for debugging, but it is not blocking for the core commit-then-PR flow. It adds significant value for
diagnosing workflow issues without affecting the happy path.

**Independent Test**: Can be tested by performing a commit, then reading the state file directly (or via `agdt-get git.last_commit_message`) and verifying the full multi-line message is stored
verbatim. Delivers value by enabling post-hoc inspection without git access.

**Acceptance Scenarios**:

1. **Given** an agent commits with a multi-line message containing title, body, and footer, **When** the commit succeeds, **Then** `git.last_commit_message` in state contains the complete rendered
   message exactly as passed to git.
2. **Given** an agent commits with a message that has only a title line and no body, **When** the commit succeeds, **Then** `git.last_commit_body` is set to an empty string (not null or absent).
3. **Given** an agent amends a commit, **When** the amend succeeds, **Then** both `git.last_commit_message` and `git.last_commit_body` are updated to reflect the amended message, overwriting any
   previously stored values.

---

### User Story 3 - Title Persistence Across Amends (Priority: P2)

An agent working on a feature branch makes multiple amend cycles (code change → amend → force push). The commit message title remains stable across these cycles unless explicitly changed. The agent
expects `git.last_commit_title` to always reflect the most recent commit title, enabling consistent PR title references and Jira comment formatting across the session.

**Why this priority**: Multi-amend workflows are the norm under the single-commit-per-PR policy. Ensuring the title persists correctly prevents drift between what git contains and what state reports.
This builds on User Story 1 and is tested independently.

**Independent Test**: Can be tested by running `agdt-git-save-work` twice (simulating two amend cycles with the same title), then verifying `git.last_commit_title` still holds the correct value.
Also testable with a changed title on the second amend to verify it updates.

**Acceptance Scenarios**:

1. **Given** an agent runs `agdt-git-save-work` once with title
   `"feat([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): initial implementation"`,
   **When** the agent runs `agdt-git-save-work` again with the same `commit_message`, **Then**
   `git.last_commit_title` remains
   `"feat([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): initial implementation"`.
2. **Given** an agent previously committed with title
   `"feat([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): initial implementation"`,
   **When** the agent changes `commit_message` to use title
   `"feat([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): complete implementation"`
   and runs `agdt-git-save-work`, **Then** `git.last_commit_title` is updated to
   `"feat([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): complete implementation"`.

---

### User Story 4 - Session Recovery After Crash (Priority: P3)

An agent session crashes or is interrupted after a successful commit but before creating a PR. When a new session starts in the same worktree, it can read `git.last_commit_title` and
`git.last_commit_message` from state to understand what was previously committed and resume the workflow without re-deriving this information from git history.

**Why this priority**: Session recovery is a resilience concern. The primary workflows function without it (agents can always fall back to `git log`), but persisted state makes recovery faster and
more reliable. This is a quality-of-life improvement rather than a core functional requirement.

**Independent Test**: Can be tested by simulating a commit (writing state as the command would), then in a fresh process reading the state keys and verifying they contain expected values. Delivers
value by proving state survives process boundaries.

**Acceptance Scenarios**:

1. **Given** a previous session committed successfully and state contains `git.last_commit_message` and `git.last_commit_title`, **When** a new agent session starts in the same worktree, **Then**
   both keys are readable via `agdt-get` and contain the values from the last successful commit.

---

### Edge Cases

What happens when a commit fails (non-zero exit code from git)? The state keys must NOT be updated if the commit operation itself did not succeed, because the persisted values would be inaccurate —
they would describe a commit that does not exist in git history. The implementation must only persist state after confirming a successful commit or amend.

What happens when `--dry-run` is active? In dry-run mode, no actual git operations occur. The state keys must NOT be updated during a dry run, since no real commit was created. The agent should see
the previously persisted values (if any) unchanged.

What happens when the commit message contains only a title with no body? The `git.last_commit_body` key must be set to an empty string to distinguish "title-only message" from "no commit has ever been
made" (where the key would be absent or null). The `git.last_commit_message` must still contain the full message (which in this case equals the title).

What happens when the commit message title exceeds conventional length limits? The system persists the title as-is without truncation. Validation of commit message format is outside the scope of this
feature — the persistence layer is a faithful recorder, not a linter.

What happens when `agdt-git-save-work` succeeds at the commit step but fails during rebase or push? The state keys ARE persisted because the commit was created successfully in the local repository.
Push/rebase failures do not invalidate the local commit. The persistence occurs immediately after `create_commit()`/`amend_commit()` returns, before rebase or push operations begin.

What happens when `agdt-clear` is run? All persisted keys (`commit_message_title`, `git.last_commit_title`, `git.last_commit_message`, `git.last_commit_body`) are cleared along with all other state
keys, consistent with standard `agdt-clear` behavior.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST persist the commit message title (first line of the rendered commit message, defined as all characters up to but not including the first newline) to both state keys
  `commit_message_title` and `git.last_commit_title` after every successful commit or amend operation, so the title is reusable by later commands and available for state inspection. Additionally,
  if a subsequent `agdt-git-save-work` invocation on the same worktree has no `--commit-message`
  CLI flag passed and the `commit_message` state key is absent or empty, the implementation MUST
  use the previously persisted `git.last_commit_message` value as the default commit message for
  that invocation (preserving the complete message including footer), so the commit convention
  (footer repeating issue link) is not violated and no previously-established body or footer
  content is silently dropped. This defaulting applies to both new-commit and amend paths and is independent
  of create-vs-amend path selection (see FR-009). The fallback logic MUST reside in `commit_cmd()` (in `commands.py`), checking `git.last_commit_message` from state before calling
  `get_commit_message()`, so that `get_commit_message()` in `core.py` remains a simple state reader for the `commit_message` key.

  **Note — relationship between `commit_message_title` reuse and `git.last_commit_message` fallback**:
  The source issue (#1832) states that `commit_message_title` should be "reusable on the next
  commit if not specified again." This spec satisfies that intent via the `git.last_commit_message`
  fallback mechanism: when no `commit_message` is provided, the full persisted message (which
  includes the title as its first line) is reused verbatim. `commit_message_title` itself is NOT
  used as a standalone commit-message fallback for `agdt-git-save-work` because a title-only
  message would omit the mandatory footer (issue link), violating the repository commit convention
  (see COMMIT_CONVENTION.md). `commit_message_title` remains purely output metadata consumed by
  downstream commands such as `agdt-create-pull-request` (e.g., as a default PR title). The
  `git.last_commit_message` fallback is the chosen mechanism for full-message reuse on subsequent
  `agdt-git-save-work` invocations.

- **FR-002**: The system MUST persist the full rendered commit message exactly as provided to git to state key `git.last_commit_message` after every successful commit or amend operation. This
  includes the title, blank separator line, body, and any footers — the complete string that git receives.

- **FR-003**: The system MUST persist the commit body to state key `git.last_commit_body` after every successful commit or amend operation. Body extraction starts after the first newline (title line),
  and if that remaining content begins with a blank separator line, that single separator line is excluded. If the commit message has no newline (title-only), this key MUST be set to an empty string
  `""`.

- **FR-004**: The system MUST NOT update any state keys when the commit or amend operation fails (non-zero git exit code), ensuring state always reflects the last successful operation. This applies
  to all four keys: `commit_message_title`, `git.last_commit_title`, `git.last_commit_message`, and `git.last_commit_body`.

- **FR-005**: The system MUST NOT update any of the persisted state keys (`commit_message_title`, `git.last_commit_title`, `git.last_commit_message`, `git.last_commit_body`) when
  `agdt-git-save-work` runs in dry-run mode (`--dry-run` flag or `dry_run` state key is true), because no actual commit is created during a dry run.

- **FR-006**: The system MUST overwrite previously stored values of all persisted keys (`commit_message_title`, `git.last_commit_title`, `git.last_commit_message`, `git.last_commit_body`) on each
  successful commit or amend operation so they always reflect the most recent commit.

- **FR-007**: The system MUST write all persisted keys (`commit_message_title`, `git.last_commit_title`, `git.last_commit_message`, `git.last_commit_body`) as a single all-or-nothing update after a
  confirmed successful operation. Either all keys are written or none are written. This prevents partial state (e.g., title written but body missing) that could arise from a crash between
  individual writes. This is an application-level atomicity guarantee (no partial key writes) achieved by batching all state updates into one exclusive-locking read/modify/write operation (for
  example via `read_modify_write_state()` with a single lock spanning load→mutate→save). It does not imply that the git operation and the state write are a single atomic filesystem transaction.

- **FR-008**: The persisted keys (`commit_message_title`, `git.last_commit_title`, `git.last_commit_message`, `git.last_commit_body`) MUST be readable via the standard `agdt-get` command (e.g.,
  `agdt-get commit_message_title`, `agdt-get git.last_commit_title`) and follow existing key naming conventions.

- **FR-009**: To reconcile with existing `agdt-git-save-work` intent semantics specified elsewhere, this feature makes an explicit compatibility decision: persisted `commit_message_title` is output
  metadata only and `agdt-git-save-work` MUST NOT use it as a create/amend intent signal. Any state-based create-intent contract that currently uses `commit_message_title` (including spec #1830)
  MUST be migrated to a non-colliding dedicated input key in follow-on phases (for example, `create_commit_message_title`) so persisted output cannot change operation-path selection.

### Non-Functional Requirements

- **NFR-001**: The state persistence operation MUST complete within 50 milliseconds on a standard filesystem, adding negligible latency to the `agdt-git-save-work` command. Since the state file is
  already written during the command for other purposes (e.g., background task tracking), this should be a trivial addition to an existing write.

- **NFR-002**: The persisted commit message MUST faithfully reproduce the exact string passed to git, preserving all whitespace, line breaks, and special characters without transformation or escaping
  beyond what JSON serialization requires.

- **NFR-003**: The feature MUST maintain 100% branch coverage in unit tests for all new code paths, consistent with the repository's existing coverage requirements enforced by CI.

- **NFR-004**: The state key names (`commit_message_title`, `git.last_commit_title`, `git.last_commit_message`, `git.last_commit_body`) MUST be documented in
  the `.github/copilot-instructions.md` file under
  the appropriate section, following the existing pattern for state key documentation.

### Key Entities

- **Reusable Commit Title Param** (`commit_message_title`): Persisted commit-title metadata that downstream commands (for example PR/Jira helpers) can reuse when a title is not explicitly
  re-specified; this key is output metadata and MUST NOT act as an implicit create/amend intent switch in `agdt-git-save-work`.

- **Commit Message Title** (`git.last_commit_title`): The first line of the rendered commit message, representing the subject line per conventional commits format. Used as a candidate default for
  PR titles and Jira comment references.

- **Full Commit Message** (`git.last_commit_message`): The complete multi-line string passed to git during commit creation/amend, including title, separator, body, and footers. Serves as the
  authoritative record of what was committed. Also serves as the fallback commit message for subsequent `agdt-git-save-work` invocations when no `commit_message` is explicitly provided.

- **Commit Body** (`git.last_commit_body`): Content after the title line (first newline), excluding one optional leading blank separator line. Contains bullet points, explanations, breaking change
  notices, and issue references. Empty string when the message is title-only.

### Implementation Placement

The state persistence logic MUST be placed in `commit_cmd()` within `agentic_devtools/cli/git/commands.py`, immediately after the `create_commit()` or `amend_commit()` call returns successfully
(before rebase/push steps). This ensures:

1. The commit exists in the local repository before state is written.
2. Push/rebase failures do not prevent state persistence.
3. The persistence is co-located with the orchestration logic that knows whether the operation succeeded.

The `git.last_commit_message` fallback logic (FR-001) MUST also reside in `commit_cmd()`, before the existing `get_commit_message()` call, so that `get_commit_message()` in `core.py` remains a simple
single-key state reader.

## Success Criteria

### Measurable Outcomes

- **SC-001**: After implementation: 100% of successful, non-dry-run `agdt-git-save-work` invocations (both new-commit and amend paths) result in all persisted state keys
  (`commit_message_title`, `git.last_commit_title`, `git.last_commit_message`, `git.last_commit_body`) being populated, verified by unit tests with assertions on state content.

- **SC-002**: The unit test suite for the new persistence logic achieves 100% branch coverage as measured by `agdt-test-pattern` targeting the relevant test module(s), with zero uncovered
  branches. (`agdt-test-file --source-file` is not used here because this repo follows the 1:1:1 test layout under `tests/unit/` rather than the legacy `tests/test_<module>.py` layout that
  `agdt-test-file` infers.)

- **SC-003**: The state write latency added by this feature is less than 10 milliseconds per invocation, measurable by timing the single atomic state update path used to persist all keys together
  after a successful commit/amend.

- **SC-004**: Zero regressions in existing `agdt-git-save-work` tests — the full test suite (`agdt-test`) passes with no new failures after the feature is implemented.

- **SC-005**: All persisted state keys (`commit_message_title`, `git.last_commit_title`, `git.last_commit_message`, `git.last_commit_body`) are documented in
  `.github/copilot-instructions.md` within the Git Workflow Actions section, verified by grep for the key names in the documentation file.

---
*Generated by Copilot SDK (claude-opus-4.6)*
