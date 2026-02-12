# Feature Specification: GitHub Action SpecKit Trigger

**Feature Branch**: `002-github-action-speckit-trigger`
**Created**: 2026-02-03
**Status**: Draft
**Input**: User description: "I wanna add the capability of starting
the speckit process with the creation of an issue within the repository.
I would love to have a github action that on adding a label, the process
of SDD should start"

---

## 📊 Workflow Sequence Diagram

For a comprehensive visual representation of the complete workflow showing all
actors, phases, and decision points, see the
[Workflow Sequence Diagram](./workflow-sequence-diagram.md).

The diagram illustrates:

- All 8 workflow phases from initiation to completion
- Interactions between User, GitHub, SpecKit Action, AI Provider,
  and Repository
- Decision points for idempotency checks and error handling
- Integration with the SDD pattern
- Next steps for continuing the SDD workflow

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trigger SDD Process via Issue Label (Priority: P1)

As a repository maintainer, I want the Specification-Driven Development
(SDD) process to automatically start when I add a `speckit` label to an
issue, so that feature specifications are created without manual
intervention.

**Why this priority**: This is the core functionality that enables
automated SDD initiation from GitHub issues, removing friction from the
specification creation workflow.

**Independent Test**: Can be fully tested by creating a GitHub issue,
adding the `speckit` label, and verifying that the `/speckit.specify`
process initiates and creates a spec draft.

**Acceptance Scenarios**:

1. **Given** a GitHub repository with the SpecKit Action installed,
   **When** the `speckit` label is added to an issue, **Then** the GitHub
   Action triggers and initiates the `/speckit.specify` command with the
   issue title and body as input.
2. **Given** an issue that already had the label removed and re-added,
   **When** the `labeled` event fires, **Then** the SDD process starts
   using the current issue content.
3. **Given** a label other than `speckit` added to an issue, **When** the
   `labeled` event fires, **Then** no action is taken and the workflow
   exits silently.

---

### User Story 2 - Configurable Trigger Label (Priority: P2)

As a repository administrator, I want to configure which label triggers
the SDD process, so that I can customize the workflow to fit my team's
setup.

**Why this priority**: Different teams may use different labeling
conventions, making configurability essential for adoption.

**Independent Test**: Can be tested by setting the `SPECKIT_TRIGGER_LABEL`
repository variable to a different label name and verifying that only
that label triggers the process.

**Acceptance Scenarios**:

1. **Given** a repository with `SPECKIT_TRIGGER_LABEL` set to
   `sdd-start`, **When** the `sdd-start` label is added to an issue,
   **Then** the SDD process triggers.
2. **Given** no custom configuration, **When** the workflow runs, **Then**
   the default `speckit` label is used as the trigger.
3. **Given** a custom trigger label, **When** the default `speckit` label
   is added instead, **Then** no action is taken.

---

### User Story 3 - Spec Creation Feedback via Issue Comment (Priority: P2)

As an issue author, I want to receive feedback on the specification
creation process directly in the GitHub issue, so that I can track
progress and review the generated specification without leaving GitHub.

**Why this priority**: Immediate feedback in the issue thread creates a
seamless user experience and enables collaboration on the specification.

**Independent Test**: Can be tested by triggering the SDD process and
verifying that comments are posted to the issue with status updates and
the generated spec content or link.

**Acceptance Scenarios**:

1. **Given** an issue that triggers the SDD process, **When** the process
   starts, **Then** a comment is posted to the issue indicating that
   specification creation has begun.
2. **Given** a successful specification creation, **When** the process
   completes, **Then** a comment is posted with a link to the generated
   spec file or PR.
3. **Given** a failed specification creation, **When** the process errors,
   **Then** a comment is posted explaining the failure and suggesting next
   steps.

---

### User Story 4 - Automatic Spec Branch and PR Creation (Priority: P3)

As a repository maintainer, I want the GitHub Action to automatically
create a feature branch with the generated specification and open a pull
request, so that the spec can be reviewed through the standard PR
workflow.

**Why this priority**: Integrating with the PR workflow enables code
review of specifications and maintains a clean commit history.

**Independent Test**: Can be tested by triggering the SDD process and
verifying that a new branch is created with the spec files and a PR is
opened against the main branch.

**Acceptance Scenarios**:

1. **Given** a successful specification creation, **When** the process
   completes, **Then** a new branch (e.g., `specs/NNN-feature-name`) is
   created with the spec files.
2. **Given** a new spec branch, **When** the branch is pushed, **Then** a
   pull request is automatically opened with a summary of the
   specification.
3. **Given** an issue with labels, **When** the PR is created, **Then** the
   same labels are applied to the PR for consistency.

---

### User Story 5 - Issue-to-Spec Linking (Priority: P3)

As a project manager, I want the generated specification to be linked back
to the originating GitHub issue, so that I can trace requirements from
issue to implementation.

**Why this priority**: Traceability between issues and specifications is
important for project management but not critical for the core
functionality.

**Independent Test**: Can be tested by verifying that the generated
spec.md file contains a reference to the originating issue number and URL.

**Acceptance Scenarios**:

1. **Given** a specification generated from an issue, **When** the spec.md
   is created, **Then** it includes a `Source Issue` field with the issue
   number and URL.
2. **Given** a PR created from the spec, **When** the PR description is
   generated, **Then** it includes `Closes #NNN` or `Relates to #NNN` to
   link the issue.

---

### Edge Cases

- What happens when the issue body is empty or contains only minimal
  information?
- How does the system handle rate limiting from the GitHub API?
- What happens if the trigger label is added and removed quickly before
  the workflow starts?
- How does the system behave if the spec directory already exists for the
  same feature name?
- What happens if the GitHub Action lacks permissions to create branches
  or PRs?
- How does the system handle the trigger label being added to multiple
  issues concurrently?
- What happens if the issue title contains special characters that are
  invalid for branch names?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST listen for GitHub `issues.labeled` webhook
  events.
- **FR-002**: System MUST compare the added label against a configurable
  trigger label (default: `speckit`).
- **FR-003**: System MUST extract the issue title and body as input for
  the `/speckit.specify` command.
- **FR-004**: System MUST create a new spec directory following the
  `NNN-feature-name` naming convention.
- **FR-005**: System MUST generate a `spec.md` file using the SpecKit
  specification template.
- **FR-006**: System MUST post status comments to the originating GitHub
  issue.
- **FR-007**: System MUST create a feature branch for the specification
  (if PR creation is enabled).
- **FR-008**: System MUST open a pull request with the generated
  specification (if PR creation is enabled).
- **FR-009**: System MUST sanitize issue titles to create valid branch and
  directory names.
- **FR-010**: System MUST include the source issue reference in the
  generated specification.

### Non-Functional Requirements

- **NFR-001**: The GitHub Action MUST complete initial acknowledgment
  (posting "started" comment) within 30 seconds of the label event.
- **NFR-002**: The full specification generation process MUST complete
  within 5 minutes for typical issue descriptions.
- **NFR-003**: The Action MUST be idempotent - re-running on the same
  issue should not create duplicate specs or branches.
- **NFR-004**: The Action MUST fail gracefully with clear error messages
  when GitHub API permissions are insufficient.
- **NFR-005**: The Action MUST support GitHub Enterprise Server in
  addition to GitHub.com.

### Key Entities

- **Trigger Event**: The GitHub `issues.labeled` webhook payload
  containing issue details and label information.
- **Trigger Label**: The configured label (default: `speckit`) that starts
  the SDD process when added to an issue.
- **Spec Directory**: The generated `specs/NNN-feature-name/` directory
  containing the specification artifacts.
- **Feedback Comment**: Issue comments posted by the Action to communicate
  status and results.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95% of issues labeled with the trigger label result in a
  specification being generated within 5 minutes.
- **SC-002**: 100% of triggered workflows post an acknowledgment comment
  to the issue within 30 seconds.
- **SC-003**: 100% of generated specifications include a valid reference
  to the source issue.
- **SC-004**: 90% of users can configure the Action with their preferred
  trigger label without consulting documentation beyond the README.
- **SC-005**: Zero duplicate specifications are created when the same
  issue triggers the workflow multiple times.

## Configuration Options

The GitHub Action should support the following configuration options via
repository variables:

| Variable | Required | Default | Description |
| -------- | -------- | ------- | ----------- |
| `SPECKIT_TRIGGER_LABEL` | No | `speckit` | Label that triggers SDD |
| `SPECKIT_CREATE_PR` | No | `true` | Create PR with spec |
| `SPECKIT_CREATE_BRANCH` | No | `true` | Create feature branch |
| `SPECKIT_COMMENT_ON_ISSUE` | No | `true` | Post status comments |
| `SPECKIT_AI_PROVIDER` | No | `claude` | AI provider (claude, openai) |

## Out of Scope

- Automatic implementation after specification is approved (covered by
  `/speckit.implement`)
- Integration with external project management tools (Jira, Azure DevOps)
- Custom AI prompts or templates (use existing SpecKit templates)
- Slack/Discord notifications (can be added via separate workflow)
