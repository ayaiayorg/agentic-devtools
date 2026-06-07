# Feature Specification: Pull Request Body Template with Commit Aggregation Fallback

**Feature Branch**: `1828-pull-request-body-template`
**Created**: 2026-06-07
**Status**: Draft
**Source Issue**: #1828 (<https://github.com/ayaiayorg/agentic-devtools/issues/1828>)

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

As a developer who has made commits on a feature branch but whose state does not contain a cached commit message, I expect the system to automatically aggregate commit messages from the branch history
so that the PR body still contains meaningful context about what changed rather than an empty or placeholder description.

**Why this priority**: State may not always contain the commit message — for example, if the developer used raw git commands for some commits, or if state was cleared between sessions. The git log
fallback ensures the PR body is always informative regardless of how commits were created. This is a critical reliability path.

**Independent Test**: Can be tested by clearing `git.last_commit_message` from state, making multiple commits on a branch ahead of `origin/main`, and verifying that `agdt-create-pull-request`
aggregates all commit messages from those commits into the template.

**Acceptance Scenarios**:

1. **Given** a branch with three commits ahead of `origin/main` and no `git.last_commit_message` in state, **When** the developer runs `agdt-create-pull-request`, **Then** the system executes `git log
   --format=%B origin/main..HEAD`, concatenates all three commit messages separated by appropriate delimiters, and injects the combined result into `{{fullCommitMessage}}`.

2. **Given** a branch with one commit ahead of `origin/main` and no state value, **When** the PR is created, **Then** only that single commit's full message (subject + body + footer) is injected
   without any concatenation markers or separators.

3. **Given** a branch with no commits ahead of `origin/main` and no state value, **When** the PR is created, **Then** the fallback message "No commit message could be found." is injected in place of
   `{{fullCommitMessage}}`.

---

### User Story 3 - Initial Template Setup (Priority: P1)

As a developer setting up the agentic-devtools configuration in a repository for the first time, I expect the setup process to create a default PR template at `.agdt/config/pull-request-template.md`
so that I have a starting point that I can customize to match my team's operational requirements without having to write the template from scratch.

**Why this priority**: Without the initial template creation, the entire feature has no template to work with. This is the bootstrapping path that enables all other scenarios. It must be reliable and
idempotent.

**Independent Test**: Can be tested by running the setup command in a repository that has no `.agdt/config/` directory and verifying the template file is created with the expected default content
including the German-language operational checklist.

**Acceptance Scenarios**:

1. **Given** a repository where `.agdt/config/pull-request-template.md` does not exist, **When** the AGDT setup process runs, **Then** the file is created with the default template content containing
   the operational checklist sections (Getestet, Database Schema Changes, Mgm-CLI Updates, Workbench Infrastruktur Updates, Infrastruktur Kommunikation, Dokumentation) and the `{{fullCommitMessage}}`
   placeholder in the Zusatzinformationen section.

2. **Given** a repository where `.agdt/config/pull-request-template.md` already exists with user customizations, **When** the AGDT setup process runs again, **Then** the existing file is NOT
   overwritten and the user's customizations are preserved intact.

3. **Given** a repository where `.agdt/config/` directory exists but the template file is missing, **When** setup runs, **Then** only the template file is created without modifying any other files in
   the config directory.

---

### User Story 4 - Template Validation at PR Creation Time (Priority: P2)

As a developer attempting to create a PR, I expect the system to validate that the template file exists and provide a clear error message if it is missing so that I understand why PR creation failed
and know how to fix the issue rather than getting an opaque error or a PR with no body.

**Why this priority**: This is a defensive scenario that improves the developer experience when something goes wrong. While it does not deliver primary value, it prevents confusion and support
requests when templates are accidentally deleted or when working in a fresh clone that skipped setup.

**Independent Test**: Can be tested by deleting the template file and running `agdt-create-pull-request`, then verifying the error output directs the user to re-run setup or manually create the
template.

**Acceptance Scenarios**:

1. **Given** a repository where `.agdt/config/pull-request-template.md` has been deleted, **When** the developer runs `agdt-create-pull-request`, **Then** the command outputs a clear warning message
   indicating the template is missing, suggests running setup to recreate it, and still creates the PR using the raw commit message as the body (graceful degradation rather than hard failure).

2. **Given** a repository where the template exists but contains no `{{fullCommitMessage}}` placeholder, **When** the developer runs `agdt-create-pull-request`, **Then** the PR is created with the
   template content as-is (without any interpolation), and no error is raised since the placeholder is optional for user-managed templates.

---

### User Story 5 - User Customization Persistence (Priority: P2)

As a team lead who has customized the PR template to include additional checklist items specific to our team's compliance requirements, I expect that no AGDT update or command will overwrite my
customizations so that I maintain full ownership of the template content after initial creation.

**Why this priority**: Trust in user-managed files is essential for adoption. If teams cannot rely on their customizations persisting, they will avoid using the template feature entirely. This
scenario protects the user-managed contract.

**Independent Test**: Can be tested by modifying the template content, running various AGDT commands including setup and PR creation, and verifying the file content remains exactly as the user left
it.

**Acceptance Scenarios**:

1. **Given** a customized template with additional checklist items and modified section headings, **When** any AGDT command runs (including `agdt-create-pull-request`, setup, or workflow commands),
   **Then** the template file on disk remains byte-for-byte identical to what the user saved.

2. **Given** a customized template with the `{{fullCommitMessage}}` placeholder moved to a different location within the file, **When** a PR is created, **Then** the commit message is injected at the
   new placeholder location, respecting the user's structural choices.

---

### Edge Cases

The system must handle several boundary conditions gracefully. When the commit message contains markdown characters (backticks, pipes, brackets), these must be preserved verbatim since the commit
message is already authored in markdown-compatible format by the developer. When the git log command fails (for example, because `origin/main` does not exist in a newly initialized repository), the
system must fall through to the final fallback message rather than crashing. When multiple commits exist on the branch but some have empty bodies (subject-only commits), the aggregation must still
produce clean output without excessive blank lines or separators between empty entries. When the template file exists but is completely empty (zero bytes), the PR body should be just the interpolated
commit message without any surrounding template content.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST create a default PR template file at `.agdt/config/pull-request-template.md` during AGDT setup when the file does not already exist, containing the operational checklist
  with sections for testing, database schema changes, CLI updates, workbench infrastructure updates, infrastructure communication, and documentation, plus a `{{fullCommitMessage}}` placeholder in the
  Zusatzinformationen section.

- **FR-002**: The system MUST NOT overwrite or modify `.agdt/config/pull-request-template.md` if it already exists during setup or any other AGDT command execution, preserving the user-managed
  contract for the template file.

- **FR-003**: The `agdt-create-pull-request` command MUST read the template from `.agdt/config/pull-request-template.md`, replace all occurrences of `{{fullCommitMessage}}` with the resolved commit
  message, and use the resulting content as the PR body when submitting the pull request to the target platform (Azure DevOps or GitHub).

- **FR-004**: The system MUST resolve the `fullCommitMessage` value using a three-step fallback chain in strict priority order: first, the value of `git.last_commit_message` from state; second, the
  output of `git log --format=%B origin/main..HEAD` (with multiple commit messages concatenated if the branch has more than one commit ahead); third, the literal string "No commit message could be
  found." if both previous sources yield no content.

- **FR-005**: When aggregating multiple commit messages from `git log`, the system MUST separate individual commit messages with a markdown horizontal rule (`---`) and preserve the full format of each
  message including subject line, body, and footer sections without truncation.

- **FR-006**: The system MUST validate that the template file exists at PR creation time and, if the file is missing, emit a warning to stderr indicating the template path and a suggestion to run
  setup, then gracefully degrade by using the resolved `fullCommitMessage` value alone as the PR body.

- **FR-007**: The system MUST treat the `{{fullCommitMessage}}` placeholder as optional within the template — if a user-customized template removes the placeholder, the PR body is rendered from the
  template content without any interpolation and without raising an error. If the template file exists but is empty (zero bytes or whitespace-only), the system MUST use the resolved
  `fullCommitMessage` value alone as the PR body.

- **FR-008**: The `agdt-git-save-work` command MUST persist the commit message to `git.last_commit_message` in state after a successful commit or amend operation, ensuring the primary fallback source
  is populated for subsequent PR creation.

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

- **SC-003**: Setup idempotency is verified by running setup 10 consecutive times on a repository with a customized template and confirming zero byte changes to the template file across all runs,
  validated by automated test assertions that compare file content (byte-for-byte) before and after each run and/or assert the write path is not invoked when the template already exists.

- **SC-004**: All 5 functional requirements related to template handling (FR-001 through FR-005) achieve 100% branch coverage in unit tests, with dedicated test cases for each fallback path,
  empty-state scenarios, and multi-commit aggregation.

- **SC-005**: End-to-end PR creation time (from command invocation to background task spawn) remains under 500 milliseconds with the template feature enabled, representing no more than 50 milliseconds
  of added latency compared to the baseline without template interpolation.

---
*Generated by Copilot SDK (claude-opus-4.6)*
