# Feature Specification: Workflow Step Chat Prompts

**Feature Branch**: `001-add-workflow-step-agents`  
**Created**: 2026-02-06  
**Status**: Draft  
**Input**: User description: "for our agdt_devtools, i wanna add for each
workflow step a agent within the agents and a prompt within prompts in the style
of speckit, so our development team can start each workflow step out of the
copilot chat window in vscode"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start a workflow step from chat (Priority: P1)

As a developer, I want to start any workflow step from the Copilot chat window
so I can begin work without leaving the chat context.

**Why this priority**: This is the core value of the feature and enables the new
workflow entry point.

**Independent Test**: Can be fully tested by selecting a workflow step in chat
and receiving the step-specific prompt and required inputs.

**Acceptance Scenarios**:

1. **Given** a known workflow step exists, **When** the developer selects that
   step in Copilot chat, **Then** the step-specific prompt appears with required
   inputs and next actions.
2. **Given** multiple workflow steps exist, **When** the developer selects any
   step, **Then** the correct prompt is shown for that step and not a different
   one.

---

### User Story 2 - Consistent step guidance (Priority: P2)

As a developer, I want each step prompt to follow a consistent Speckit style so
I can quickly understand what to do next.

**Why this priority**: Consistent guidance reduces onboarding time and avoids
confusion across steps.

**Independent Test**: Can be tested by reviewing prompts for at least two steps
and verifying consistent structure and tone.

**Acceptance Scenarios**:

1. **Given** two different workflow steps, **When** their prompts are opened,
   **Then** both prompts share the same structure, tone, and clarity standards.

---

### User Story 3 - Maintain step coverage (Priority: P3)

As a workflow maintainer, I want every workflow step to have a corresponding
chat agent and prompt so the team can start any step without gaps.

**Why this priority**: Full coverage prevents dead ends and ensures reliability
of the new entry point.

**Independent Test**: Can be tested by listing all workflow steps and verifying
each has a matching chat entry.

**Acceptance Scenarios**:

1. **Given** the current workflow step catalog, **When** a coverage check is
   run, **Then** no step is missing a chat agent or prompt.

---

### Edge Cases

- What happens when a workflow step is renamed and its chat agent or prompt is

  not updated?
  not updated?

- How does the system handle a request for a step that is not available in the

  current workspace?
  current workspace?

- What happens if a prompt definition is present but lacks required inputs or

  guidance?
  guidance?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a chat entry point for every existing

  workflow step.
  workflow step.

- **FR-002**: The system MUST provide a step-specific prompt for every workflow

  step that can be launched from Copilot chat.
  step that can be launched from Copilot chat.

- **FR-003**: The system MUST use a consistent Speckit-style structure across

  all step prompts.
  all step prompts.

- **FR-004**: Each step prompt MUST include purpose, prerequisites or inputs,

  the actions to take, expected outcomes, and next steps.
  the actions to take, expected outcomes, and next steps.

- **FR-005**: The system MUST present required inputs and expected outcomes in

  each step prompt.
  each step prompt.

- **FR-006**: The system MUST prevent or clearly report missing step coverage

  when a workflow step has no chat agent or prompt.
  when a workflow step has no chat agent or prompt.

- **FR-007**: Users MUST be able to select a workflow step without needing to

  know internal identifiers or file locations.
  know internal identifiers or file locations.

### Non-Functional Requirements

- **NFR-001**: The chat entry point for a step MUST be discoverable by a

  developer within 30 seconds.
  developer within 30 seconds.

- **NFR-002**: Step prompts MUST be readable and actionable within 2 minutes by

  a developer new to the workflow.
  a developer new to the workflow.

- **NFR-003**: The system MUST provide clear, actionable error messages when a

  step cannot be started from chat.
  step cannot be started from chat.

### Key Entities *(include if feature involves data)*

- **Workflow**: A named sequence of steps that guide a development task.
- **Workflow Step**: A single step within a workflow that can be started

  independently.
  independently.

- **Chat Agent**: The chat entry point used to initiate a workflow step.
- **Step Prompt**: The prompt content that guides the user through a workflow

  step.
  step.

- **Prompt Catalog**: The set of all step prompts and their mappings to

  workflow steps.
  workflow steps.

## Assumptions

- All existing workflows have a defined, finite list of steps that is the

  source of truth for step coverage.
  source of truth for step coverage.

- The primary user experience is within VS Code Copilot chat, not other clients.
- Speckit-style prompts refer to consistent structure and tone rather than

  implementation specifics.
  implementation specifics.

## Dependencies

- VS Code Copilot supports custom chat agents and step-specific prompts for the

  workspace.
  workspace.

- Workflow step definitions remain stable enough to keep prompt mappings

  current.
  current.

## Out of Scope

- Creating new workflows or modifying workflow logic beyond adding chat entry

  points and prompts.
  points and prompts.

- Changing how workflow steps are executed outside of the Copilot chat entry

  point.
  point.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of existing workflow steps have a matching chat agent and

  step prompt.
  step prompt.

- **SC-002**: A developer can start any workflow step from Copilot chat in

  under 2 minutes without external documentation.
  under 2 minutes without external documentation.

- **SC-003**: 90% of developers report that step prompts are clear and

  consistent across workflows.
  consistent across workflows.

- **SC-004**: Zero production incidents are caused by missing or mismatched
  step prompts during the first month after release.
