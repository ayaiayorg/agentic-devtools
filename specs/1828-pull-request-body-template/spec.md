# Feature Specification: Pull Request Body Template with Commit Aggregation Fallback

**Feature Branch**: `1828-pull-request-body-template`
**Created**: 2026-06-07
**Status**: Draft
**Source Issue**: #1828 (<https://github.com/ayaiayorg/agentic-devtools/issues/1828>)

## Clarifications

### Session 2026-06-07

- Q: The spec uses `git.last_commit_message` as the state key for the cached commit message, but the existing codebase uses `commit_message` (in `STATE_COMMIT_MESSAGE = "commit_message"` in
  `core.py`). Should FR-008 persist to a new `git.last_commit_message` key or reuse the existing `commit_message` key? → A: Introduce a new `git.last_commit_message` state key specifically for this
  feature. The existing `commit_message` key is the *input* to `agdt-git-save-work` (what message to use for the commit), while `git.last_commit_message` is the *output* (what message was actually
  committed). These serve different lifecycle purposes — input is consumed and potentially modified during commit, output persists as a record for downstream PR creation.

- Q: The spec references "AGDT setup process" for creating the default template, but no `agdt-setup` command currently exists. Should the template creation be triggered by a new dedicated `agdt-setup`
  command, integrated into `agdt-initiate-work-on-jira-issue-workflow`, or handled by a new `agdt-init-pr-template` command? → A: Create a new `agdt-init-pr-template` command that creates the default
  template if it does not exist. This avoids coupling to a general "setup" command that doesn't exist yet and keeps the feature self-contained. When `agdt-create-pull-request` is run and the template
  is missing, the command should issue a warning and degrade gracefully — using the resolved `fullCommitMessage` value (state → git log → literal fallback) as the PR body — while suggesting the user
  run `agdt-init-pr-template` to create the template. The template is not auto-created during PR creation; setup is the user's explicit responsibility.

- Q: The `create_pull_request()` function currently exists in `azure_devops/commands.py` (for Azure DevOps via `az repos pr create`). GitHub PR creation via `gh pr create` does not yet have a
  dedicated `create_pull_request()` implementation in the codebase. Should the template interpolation logic be applied to both platforms or only Azure DevOps? → A: The template interpolation logic
  must apply to both platforms. The interpolation should be implemented as a shared utility function (e.g., in a new `agentic_devtools/cli/pr_template.py` module) that resolves the PR body before it is
  passed to the platform-specific creation command. `azure_devops/commands.py` already has a `create_pull_request()` entry point and will call this utility directly. GitHub will require a new PR
  creation command/module (not the existing `github/async_commands.py`, which handles issue creation) that also calls the shared utility to resolve the PR body value.

- Q: When `origin/main` does not exist (e.g., newly initialized repo or remote uses `master`), should the git log fallback try alternative branch names like `origin/master`, `main`, or `master` before
  falling through to the literal fallback? → A: Yes, the fallback should mirror the existing `branch_has_commits_ahead_of_main()` logic in `operations.py` which already tries `origin/main` first, then
  `main` without origin prefix. The git log fallback should use the same resolution order: `origin/main` → `main` → literal fallback. Do not add `master` support — this repository standardizes on
  `main`.

- Q: The spec does not specify whether `agdt-git-save-work` should persist `git.last_commit_message` with the *effective* message (after potential amend modifications) or the *input* message provided
  by the user. Which should it be? → A: Persist the *effective* committed message — i.e., the actual message that ends up on the commit after the operation completes (read back via `git log -1
  --format=%B`). This ensures `git.last_commit_message` always reflects reality, even after amend operations where the message may have been modified.

## Problem Statement

When AI agents or developers create pull requests using `agdt-create-pull-request`, the PR body is currently either a free-form string passed through state or a minimal placeholder. This results in
inconsistent PR descriptions across the team, missing operational checklists, and a lack of structured context for reviewers. Teams that rely on standardized review processes — particularly those with
cross-functional responsibilities involving operations, infrastructure, and documentation — lose valuable review time because PR authors must manually remember which checklist items to include, and
reviewers must ask for missing information that could have been provided upfront.

The absence of a templating mechanism also means that commit messages — which often contain the most accurate and up-to-date summary of what changed — are not automatically surfaced in the PR body.
Developers frequently write detailed commit messages following the Conventional Commits specification, yet this information is buried in the git log rather than being presented prominently to
reviewers. This disconnect forces reviewers to manually inspect commit history or ask the author to summarize changes that have already been documented in the commit itself.

Furthermore, organizations need the ability to customize the PR template to match their specific operational requirements without those customizations being overwritten by tool updates. A user-managed
template that is created once during setup and then owned by the repository team provides the right balance between automation and customization. The template must support variable interpolation —
specifically a `{{fullCommitMessage}}` placeholder — so that dynamic content (the aggregated commit message) is injected at PR creation time while the surrounding checklist and structure remain under
human control.

## User Scenarios & Testing

### User Story 1 - Standard PR Creation with Template (Priority: P1)

Covers: FR-003, FR-004, FR-005, FR-006, FR-007, FR-009

As a developer creating a pull request after completing feature work, I expect the PR body to automatically include the team's operational checklist and my commit message so that reviewers immediately
have the context they need without me having to manually copy information from the git log into the PR description.

**Why this priority**: This is the primary workflow that every PR creation passes through. Without this working correctly, the entire feature delivers no value. Every developer on the team creates PRs
multiple times per week, making this the highest-impact scenario.

**Independent Test**: Can be fully tested by running `agdt-create-pull-request` after a normal commit workflow and verifying the resulting PR body contains both the checklist template content and the
interpolated commit message.

**Acceptance Scenarios**:

1. **Given** a repository with `.agdt/config/pull-request-template.md` present and a commit message stored in `git.last_commit_message` state, **When** the developer runs `agdt-create-pull-request`,
   **Then** the PR body contains the full template content with `{{fullCommitMessage}}` replaced by the stored commit message, and all checklist items are present and unchecked.

2. **Given** a repository with the template present and a multi-line commit message in state including a subject line, body paragraphs, and footer references, **When** the PR is created, **Then** the
   entire commit message is injected verbatim without truncation or reformatting, preserving line breaks and markdown formatting within the commit message.

3. **Given** a repository with the template present, **When** the developer inspects the created PR in Azure DevOps or GitHub, **Then** the checklist renders as interactive checkboxes that reviewers
   can tick off during the review process.

---

### User Story 2 - Fallback to Git Log Aggregation (Priority: P1)

Covers: FR-004, FR-005, FR-008

As a developer who has made commits on a feature branch but whose state does not contain a cached commit message, I expect the system to automatically aggregate commit messages from the branch history
so that the PR body still contains meaningful context about what changed rather than an empty or placeholder description.

**Why this priority**: State may not always contain the commit message — for example, if the developer used raw git commands for some commits, or if state was cleared between sessions. The git log
fallback ensures the PR body is always informative regardless of how commits were created. This is a critical reliability path.

**Independent Test**: Can be tested by clearing `git.last_commit_message` from state, making multiple commits on a branch ahead of `origin/main`, and verifying that `agdt-create-pull-request`
aggregates all commit messages from those commits into the template.

**Acceptance Scenarios**:

1. **Given** a branch with three commits ahead of `origin/main` and no `git.last_commit_message` in state, **When** the developer runs `agdt-create-pull-request`, **Then** the system executes `git log
   --format=%B%x1e origin/main..HEAD`, splits entries on the explicit `\x1e` delimiter, concatenates all three commit messages
   separated by markdown horizontal rules (`---`), and injects the combined result into
   `{{fullCommitMessage}}`.

2. **Given** a branch with one commit ahead of `origin/main` and no state value, **When** the PR is created, **Then** only that single commit's full message (subject + body + footer) is injected
   without any concatenation markers or separators.

3. **Given** a branch with no commits ahead of `origin/main` and no state value, **When** the PR is created, **Then** the fallback message "No commit message could be found." is injected in place of
   `{{fullCommitMessage}}`.

---

### User Story 3 - Initial Template Setup (Priority: P1)

Covers: FR-001, FR-002

As a developer setting up the agentic-devtools configuration in a repository for the first time, I expect `agdt-init-pr-template` to create a default PR template at
`.agdt/config/pull-request-template.md` so that I have a starting point that I can customize to match my team's operational requirements without having to write the template from scratch.

**Why this priority**: Without the initial template creation, the entire feature has no template to work with. This is the bootstrapping path that enables all other scenarios. It must be reliable and
idempotent.

**Independent Test**: Can be tested by running `agdt-init-pr-template` in a repository that has no `.agdt/config/` directory and verifying the template file is created with the expected default
content
including the German-language operational checklist.

**Acceptance Scenarios**:

1. **Given** a repository where `.agdt/config/pull-request-template.md` does not exist, **When** the developer runs `agdt-init-pr-template`, **Then** the file is created with the default template
   content containing
   the operational checklist sections (Getestet, Database Schema Changes, Mgm-CLI Updates, Workbench Infrastruktur Updates, Infrastruktur Kommunikation, Dokumentation) and the `{{fullCommitMessage}}`
   placeholder in the Zusatzinformationen section.

2. **Given** a repository where `.agdt/config/pull-request-template.md` already exists with user customizations, **When** `agdt-init-pr-template` runs again, **Then** the existing file is NOT
   overwritten and the user's customizations are preserved intact.

3. **Given** a repository where `.agdt/config/` directory exists but the template file is missing, **When** `agdt-init-pr-template` runs, **Then** only the template file is created without modifying
   any other files in
   the config directory.

---

### User Story 4 - Template Validation at PR Creation Time (Priority: P2)

Covers: FR-006, FR-007

As a developer attempting to create a PR, I expect the system to check whether the template file exists and warn me clearly if it is missing so that I understand the situation and know how to fix it,
while the PR is still created using the resolved `fullCommitMessage` value (state → git log → literal fallback) as a fallback body rather than failing outright.

**Why this priority**: This is a defensive scenario that improves the developer experience when something goes wrong. While it does not deliver primary value, it prevents confusion and support
requests when templates are accidentally deleted or when working in a fresh clone that skipped setup.

**Independent Test**: Can be tested by deleting the template file and running `agdt-create-pull-request`, then verifying warning output directs the user to run
`agdt-init-pr-template` or manually create the template, and that the PR is still created using the resolved `fullCommitMessage` value as the fallback body.

**Acceptance Scenarios**:

1. **Given** a repository where `.agdt/config/pull-request-template.md` has been deleted, **When** the developer runs `agdt-create-pull-request`, **Then** the command outputs a clear warning message
   indicating the template is missing, suggests running `agdt-init-pr-template` to recreate it, and still creates the PR using the resolved `fullCommitMessage` value
   (state → git log → literal fallback) as the body (graceful degradation rather than hard failure).

2. **Given** a repository where the template exists but contains no `{{fullCommitMessage}}` placeholder, **When** the developer runs `agdt-create-pull-request`, **Then** the PR is created with the
   template content as-is (without any interpolation), and no error is raised since the placeholder is optional for user-managed templates.

---

### User Story 5 - User Customization Persistence (Priority: P2)

Covers: FR-002, FR-003, FR-009

As a team lead who has customized the PR template to include additional checklist items specific to our team's compliance requirements, I expect that no AGDT update or command will overwrite my
customizations so that I maintain full ownership of the template content after initial creation.

**Why this priority**: Trust in user-managed files is essential for adoption. If teams cannot rely on their customizations persisting, they will avoid using the template feature entirely. This
scenario protects the user-managed contract.

**Independent Test**: Can be tested by modifying the template content, running various AGDT commands including `agdt-init-pr-template` and PR creation, and verifying the file content remains exactly
as the user left
it.

**Acceptance Scenarios**:

1. **Given** a customized template with additional checklist items and modified section headings, **When** any AGDT command runs (including `agdt-create-pull-request`, `agdt-init-pr-template`, or
   workflow commands),
   **Then** the template file on disk remains byte-for-byte identical to what the user saved.

2. **Given** a customized template with the `{{fullCommitMessage}}` placeholder moved to a different location within the file, **When** a PR is created, **Then** the commit message is injected at the
   new placeholder location, respecting the user's structural choices.

---

### Edge Cases

The system must handle several boundary conditions gracefully. When the commit message contains markdown characters (backticks, pipes, brackets), these must be preserved verbatim since the commit
message is already authored in markdown-compatible format by the developer. When the git log command fails (for example, because `origin/main` does not exist in a newly initialized repository), the
system must try `main` (without origin prefix) before falling through to the final fallback message rather than crashing. When multiple commits exist on the branch but some have empty bodies
(subject-only commits), the aggregation must still
produce clean output without excessive blank lines or separators between empty entries. When the template file exists but is completely empty (zero bytes), the PR body should be just the interpolated
commit message without any surrounding template content.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST provide an `agdt-init-pr-template` command that creates a default PR template file at `.agdt/config/pull-request-template.md` when the file does not already exist,
  containing the operational checklist
  with sections for testing, database schema changes, CLI updates, workbench infrastructure updates, infrastructure communication, and documentation, plus a `{{fullCommitMessage}}` placeholder in the
  Zusatzinformationen section.

- **FR-002**: The system MUST NOT overwrite or modify `.agdt/config/pull-request-template.md` if it already exists during `agdt-init-pr-template` execution or any other AGDT command execution,
  preserving the user-managed
  contract for the template file.

- **FR-003**: The `agdt-create-pull-request` command MUST read the template from `.agdt/config/pull-request-template.md`, replace all occurrences of `{{fullCommitMessage}}` with the resolved commit
  message, and use the resulting content as the PR body when submitting the pull request to the target platform (Azure DevOps or GitHub). The template interpolation logic MUST be implemented as a
  shared utility function (e.g., in `agentic_devtools/cli/pr_template.py`) consumed by both platform-specific creation commands.

- **FR-004**: The system MUST resolve the `fullCommitMessage` value using a three-step fallback chain in strict priority order: first, the value of `git.last_commit_message` from state; second, the
  output of `git log --format=%B%x1e origin/main..HEAD` (falling back to `main` if `origin/main` does not exist, mirroring the resolution order in `branch_has_commits_ahead_of_main()`), parsed using
  the explicit `\x1e` delimiter and concatenated when the branch has more than one commit ahead; third, the literal string "No commit message could be found." if both previous sources yield no
  content.

- **FR-005**: When aggregating multiple commit messages from `git log`, the system MUST separate individual commit messages with a markdown horizontal rule (`---`) and preserve the full format of each
  message including subject line, body, and footer sections without truncation. When only a single commit exists, no separator is added. Empty commit bodies (subject-only commits) MUST NOT produce
  excessive blank lines or orphaned separators.

- **FR-006**: The system MUST validate that the template file exists at PR creation time and, if the file is missing, emit a warning to stderr indicating the template path and a suggestion to run
  `agdt-init-pr-template`, then gracefully degrade by using the resolved `fullCommitMessage` value alone as the PR body.

- **FR-007**: The system MUST treat the `{{fullCommitMessage}}` placeholder as optional within the template — if a user-customized template removes the placeholder, the PR body is rendered from the
  template content without any interpolation and without raising an error. If the template file exists but is empty (zero bytes or whitespace-only), the system MUST use the resolved
  `fullCommitMessage` value alone as the PR body.

- **FR-008**: The `agdt-git-save-work` command MUST persist the effective committed message (read back via `git log -1 --format=%B` after the commit/amend operation completes) to
  `git.last_commit_message` in state, ensuring the primary fallback source
  is populated for subsequent PR creation. This is distinct from the input `commit_message` state key which represents the user's requested message.

- **FR-009**: The system MUST support the template file containing arbitrary markdown content including checkboxes (`- [ ]`), headings, links, code blocks, and other formatting without corrupting or
  escaping any of that content during the interpolation process.

### Non-Functional Requirements

- **NFR-001**: Template interpolation MUST complete in under 100 milliseconds for templates up to 50 KB in size, ensuring no perceptible delay is added to the PR creation workflow.

- **NFR-002**: The fallback chain evaluation (state lookup, git log execution, literal fallback) MUST complete in under 2 seconds even on repositories with large commit histories, using the
  `origin/main..HEAD` range specifier to limit git log scope.

- **NFR-003**: Error messages related to missing templates or failed git log commands MUST follow the existing AGDT CLI output conventions (structured messages to stderr, no stack traces in normal
  operation) to maintain UX consistency across all commands.

- **NFR-004**: The template file MUST be stored in a location (`.agdt/config/`) that is committed to version control and shared across team members, ensuring all developers on the same repository use
  the same PR template without per-user configuration.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of PRs created via `agdt-create-pull-request` when a template exists include the rendered template content in the PR body, verified by integration tests that assert the presence of
  checklist items and interpolated commit message in the output.

- **SC-002**: The fallback chain resolves a non-empty `fullCommitMessage` value in at least 99% of real-world PR creation scenarios (measured as: state value present OR branch has commits ahead of
  main), with only the literal fallback used when the branch is empty and state is cleared.

- **SC-003**: Setup idempotency is verified by running `agdt-init-pr-template` 10 consecutive times on a repository with a customized template and confirming zero byte changes to the template file
  across all runs,
  validated by automated test assertions that compare file content (byte-for-byte) before and after each run and/or assert the write path is not invoked when the template already exists.

- **SC-004**: All 9 functional requirements related to template handling (FR-001 through FR-009) achieve 100% branch coverage in unit tests, with dedicated test cases for each fallback path,
  empty-state scenarios, and multi-commit aggregation.

- **SC-005**: End-to-end PR creation time (from command invocation to background task spawn) remains under 500 milliseconds with the template feature enabled, representing no more than 50 milliseconds
  of added latency compared to the baseline without template interpolation.

---
*Generated by Copilot SDK (claude-opus-4.6)*
