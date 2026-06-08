# Feature Specification: Issue type config in project.json with validation/defaults

**Source Issue**: #1833 (<https://github.com/ayaiayorg/agentic-devtools/issues/1833>)

## Problem Statement

When AI agents or developers use `agdt-git-save-work` to commit changes, the commit message must
follow Conventional Commits format which requires a type prefix (e.g., `feat`, `fix`, `refactor`).
Currently, `agdt-git-save-work` only receives the free-form `commit_message` string, so the issue
type used in commit messages is determined entirely at the point of use when that string is
composed manually by the agent or developer. `specs/1829-jinja2-commit-message-template/spec.md`
introduces the `versionControl.commitMessageType` input used when rendering commit messages, but there is still no
project-level default and no mechanism to validate that the chosen type is appropriate for the
project.

This creates two problems in practice. First, when an AI agent is constructing a commit message and
no explicit issue type has been provided, it must guess or ask the user. Different agents may default
to different types, leading to inconsistent commit history across a team. A project-level default
(e.g., `feat` for feature-heavy projects, or `fix` for maintenance-oriented repositories) would
eliminate this ambiguity and ensure consistency without requiring per-commit configuration. Second,
there is no guardrail preventing an agent or user from using a non-standard or project-inappropriate
type. A project team may want to restrict commit types to a curated subset of Conventional Commits
types, and the system currently provides no validation feedback when an invalid type is supplied.

The `.agdt/config/project.json` file already serves as the per-repo, team-shareable configuration
surface, currently storing Jira project keys, corporate network hosts, and the default Copilot
model. This feature adds two new camelCase fields as specified in the source issue:
canonical `defaultCommitIssueType` / `availableCommitIssueTypes`, with snake_case aliases
`default_commit_issue_type` / `available_commit_issue_types` accepted on read for compatibility
with other existing snake_case config keys. Adding these fields is a natural extension that keeps
all project-level configuration in one versionable location. The resolution order — explicit
CLI/state first, then project config default — preserves existing explicit-override behavior while
providing a sensible fallback for the common case where no type is specified.

**Acceptance Criteria:**

- If no explicit `versionControl.commitMessageType` is provided, the project-level default is used; if also absent, falls back to "feat".
- Warning is visible to agents/humans if an invalid (non-allowed) value is supplied.
- Fields are documented in setup and config reference.
- Unit tests cover fallback resolution and validation logic.

## User Scenarios & Testing

### User Story 1 - Default Issue Type Fallback (Priority: P1)

An AI agent is working through the `work-on-jira-issue` workflow and reaches the commit step. The
workflow prompt instructs it to commit its changes, but no explicit
`versionControl.commitMessageType` has been set in state or passed as a CLI parameter. The agent
needs the system to resolve the correct issue type from project configuration so it can construct a
valid Conventional Commits message without guessing or prompting the user.

**Why this priority**: This is the core value proposition of the feature — eliminating ambiguity
when no explicit type is provided. Without this, every commit requires explicit type specification,
adding friction to every workflow run.

**Independent Test**: Can be fully tested by loading a `project.json` with
`defaultCommitIssueType` set to `"fix"` (or its snake_case alias), then resolving the issue type
without any CLI/state override, and verifying that `"fix"` is returned.

**Acceptance Scenarios**:

1. **Given** a `project.json` containing "defaultCommitIssueType": "fix" and no
   `versionControl.commitMessageType` in state or CLI args, and no tracker-derived mapping yields a commit type,
   **When** the system resolves the issue type for a commit message, **Then** "fix" is used as the issue type.
2. **Given** a `project.json` containing "defaultCommitIssueType": "feat" and an explicit
   `versionControl.commitMessageType` of "refactor" in state, **When** the system resolves the
   issue type, **Then**
   "refactor" is used (explicit override wins).
3. **Given** no `project.json` exists, no explicit `versionControl.commitMessageType` in state, and no tracker-derived mapping yields a commit type,
   **When** the system resolves the issue type, **Then** "feat" is used as the hardcoded fallback
   default.

---

### User Story 2 - Validation Against Allowed Types (Priority: P2)

A developer or AI agent provides an issue type (either explicitly or resolved from default) that is
not in the project's configured list of allowed types. The system should emit a visible warning so
the user or agent is aware the type may be incorrect, while still allowing the operation to proceed
(non-blocking validation).

**Why this priority**: Validation adds safety and consistency but is secondary to the default
resolution behavior. Teams benefit from catching typos (`feat` vs `feta`) and non-standard types
early, but blocking on an invalid type would be overly restrictive for edge cases.

**Independent Test**: Can be tested by configuring `availableCommitIssueTypes` to
`["feat", "fix"]` (or its snake_case alias), then resolving an issue type of `"chore"`, and
verifying that a warning is emitted to stderr while the type is still returned for use.

**Acceptance Scenarios**:

1. **Given** a `project.json` with `"availableCommitIssueTypes": ["feat", "fix", "docs"]` and
   an explicit `versionControl.commitMessageType` of `"perf"`, **When** the system validates the
   issue type, **Then** a warning is printed to stderr indicating `"perf"` is not in the allowed
   list, and the type is still used.
2. **Given** a `project.json` with `"availableCommitIssueTypes": ["feat", "fix", "docs"]` and
   an explicit `versionControl.commitMessageType` of `"feat"`, **When** the system validates the
   issue type, **Then** no warning is emitted.
3. **Given** no `availableCommitIssueTypes` field in `project.json`, **When** any issue type is
   provided, **Then** validation uses the full Conventional Commits default list and no warning is
   emitted for standard types.

---

### User Story 3 - Configuration Discovery and Documentation (Priority: P3)

A team lead is setting up `agentic-devtools` for their project and wants to configure the default
commit type and restrict available types. They need clear documentation on the new fields, and the
`agdt-setup` flow should surface these options so teams can configure them during initial setup.

**Why this priority**: Documentation and discoverability are important for adoption but are not
runtime-critical. Teams that don't configure these fields get sensible defaults, so this is an
enhancement to the onboarding experience rather than a functional necessity.

**Independent Test**: Can be tested by running `agdt-setup` and inspecting
`.agdt/config/project.json` after setup, verifying the new fields are present with their defaults
and that documentation accurately describes the resolution order and validation behavior.

**Acceptance Scenarios**:

1. **Given** a fresh repository with no `project.json`, **When** a user runs the setup flow,
   **Then** the generated `project.json` includes `"defaultCommitIssueType": "feat"` and
   `"availableCommitIssueTypes"` (camelCase canonical keys as specified in issue #1833) with the
   full Conventional Commits list.
2. **Given** existing documentation for `project.json`, **When** this feature is complete,
   **Then** the config reference documents both new fields, their defaults, and the resolution
   priority order.

---

### Edge Cases

- What happens when `defaultCommitIssueType` in `project.json` is itself not in the
  `availableCommitIssueTypes` list? The system should emit a warning when resolving the
  commit message issue type (i.e., when this feature is exercised) indicating the
  misconfiguration, and still use the default (non-blocking).
- What happens when `availableCommitIssueTypes` is set to an empty array? The system should
  treat this as equivalent to the field being absent: the full standard Conventional Commits list
  is used as the allowed set. A non-standard type supplied alongside an empty array config will
  still trigger a warning, consistent with FR-004.
- What happens when the `defaultCommitIssueType` value is an empty string? The system should
  ignore it and fall through to the hardcoded default of `"feat"`.
- What happens when `project.json` contains these fields with non-string/non-array types (e.g.,
  `defaultCommitIssueType: 42`)? The system should ignore malformed values with a stderr
  warning and use defaults.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST read `defaultCommitIssueType` from `.agdt/config/project.json`
  when resolving the issue type for commit messages. The system MUST also accept
  `default_commit_issue_type` as a snake_case alias for compatibility, with camelCase taking
  precedence when both are present. This field specifies the type to use when no explicit value is
  provided via CLI parameter or state.

- **FR-002**: The system MUST read `availableCommitIssueTypes` from `.agdt/config/project.json`
  as an array of strings representing valid Conventional Commits type prefixes. The system MUST
  also accept `available_commit_issue_types` as a snake_case alias for compatibility, with camelCase
  taking precedence when both are present. When the field is absent **or an empty array**, the
  system MUST use the full standard list: `["feat", "fix", "docs", "style", "refactor", "perf",
  "test", "build", "ci", "chore", "revert"]`.

- **FR-003**: The system MUST resolve the issue type using the following priority order:
  (1) explicit override from `agdt-git-save-work --commit-message-type <type>` (mapped into state as
  `versionControl.commitMessageType`) or directly provided state value
  `versionControl.commitMessageType`,
  (2) `defaultCommitIssueType` (or alias `default_commit_issue_type`) from `project.json`,
  (3) hardcoded fallback of `"feat"`.
  The first non-empty value in this chain is used.

  Note: Tracker-derived mapping (e.g., from `issueManagement.issueType`/`jira.issue_type`) is defined
  in `specs/1829-jinja2-commit-message-template/spec.md` and is out of scope for #1833; #1833 only
  defines the project.json default fallback used when `versionControl.commitMessageType` is unset.

- **FR-004**: The system MUST validate the resolved issue type against
  `availableCommitIssueTypes`.
  When the resolved type is not in the allowed list, the system MUST emit a warning to stderr in the
  format:
  `Warning: Issue type '<type>' is not in availableCommitIssueTypes. Allowed: [<list>]`.
  The operation MUST NOT be blocked by this validation — it is advisory only.

- **FR-005**: The system MUST emit a warning to stderr when `defaultCommitIssueType` in
  `project.json` is not present in `availableCommitIssueTypes`, alerting the user to a
  misconfiguration. If this misconfigured default is also the resolved issue type (no explicit
  override), the system MUST NOT emit an additional duplicate warning beyond FR-004.

- **FR-006**: The system MUST gracefully handle malformed values for both fields — non-string values
  for `defaultCommitIssueType`/`default_commit_issue_type` and non-array or
  array-with-non-string-elements for `availableCommitIssueTypes`/`available_commit_issue_types` —
  by ignoring the malformed value, emitting a stderr warning, and falling back to defaults.

- **FR-007**: The `agdt-setup` command MUST write `defaultCommitIssueType` and
  `availableCommitIssueTypes` (camelCase canonical keys matching issue #1833) with their default
  values when generating or updating `project.json`. Existing keys in the file (e.g.
  `jira_project_keys`, `vpn_url`, `default_copilot_model`) MUST be preserved as-is and MUST NOT be
  renamed or re-cased; only the two new fields are written in camelCase. snake_case aliases
  (`default_commit_issue_type`, `available_commit_issue_types`) are accepted on read but are not
  written by setup.

### Non-Functional Requirements

- **NFR-001**: Reading `project.json` and resolving the issue type MUST add no more than 5ms of
  latency to the commit message resolution path per invocation. The implementation MAY meet this via
  explicit caching/memoization or a lightweight direct read/parse, but this requirement MUST NOT
  assume `project.json` has already been loaded by another subsystem.

- **NFR-002**: Warning messages MUST follow the existing stderr warning format used by
  `agentic_devtools/cli/config/project_config.py` (i.e., `Warning: <message>` printed to `sys.stderr`) to maintain CLI UX
  consistency.

- **NFR-003**: The validation logic MUST be implemented as a deterministic, unit-testable helper
  that returns an optional warning message string (or `None`) rather than printing to stderr
  directly. The caller is responsible for emitting any returned warning to stderr. This design
  avoids side effects inside the helper, enabling straightforward unit testing without mocking
  file I/O, state, or stderr.

### Key Entities

- **Project Config** (`project.json`): The per-repo configuration file that gains two new canonical
  fields: `defaultCommitIssueType` (string) and `availableCommitIssueTypes` (array of strings),
  with snake_case aliases accepted for compatibility.
- **Issue Type Resolution**: The logic path that determines which Conventional Commits type prefix
  to use for a given commit, consulting CLI args, state, and project config in priority order.

## Success Criteria

- **SC-001**: 100% branch coverage for the new issue type resolution function and validation logic,
  verified by running `scripts/targeted-checks.sh` (or `python -m agentic_devtools.cli.checks`),
  which scopes `--cov-branch --cov-fail-under=100` to the implementing source module only (1:1:1
  layout), avoiding spurious failures from the whole-package coverage default in `pyproject.toml`.

- **SC-002**: Zero additional warnings emitted when `project.json` contains valid default values
  (`defaultCommitIssueType` present in `availableCommitIssueTypes`), verified across the full
  test suite.

- **SC-003**: Resolution logic introduces no additional file I/O in the hot path when
  `project.json` is already loaded, and continues to satisfy NFR-001's ≤5ms latency goal under
  normal CI execution without requiring timing-based unit test assertions.

- **SC-004**: At least 8 unit tests covering: default fallback, explicit override, validation pass,
  validation warning, empty array handling, malformed value handling, missing file handling, and
  misconfigured default detection.

- **SC-005**: Documentation updated in at least 2 locations: the `.github/copilot-instructions.md`
  project config section and user-facing `agdt-setup` prompt/help text describing the
  `project.json` fields and defaults.
