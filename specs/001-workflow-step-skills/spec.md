# Feature Specification: Workflow Steps as Skills

**Feature Branch**: `001-workflow-step-skills`  
**Created**: 2026-02-26  
**Status**: Draft  
**Input**: User description: "enhance current tooling from prompts to skills so a workflow step can be invoked as a skill using /agdt.doyourstep style"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Invoke a workflow step as a skill command (Priority: P1)

A maintainer can run a workflow step directly as a skill-style slash command so the same behavior is available through the skill interface without rewriting the step.

**Why this priority**: This is the core value of the request: enabling step-to-skill invocation through `/agdt.<step>` style commands.

**Independent Test**: Can be fully tested by invoking one existing workflow step using a slash-style skill command and confirming the expected step outcome is produced.

**Acceptance Scenarios**:

1. **Given** a workflow step is available for execution, **When** the maintainer invokes `/agdt.doyourstep`, **Then** the corresponding step executes and returns its expected result.
2. **Given** the workflow step requires input parameters, **When** the maintainer invokes the skill-style command with valid inputs, **Then** the step receives those inputs and executes successfully.

---

### User Story 2 - Discover available step-backed skills (Priority: P2)

A maintainer can identify which workflow steps are exposed as skills so they can invoke the right command without relying on undocumented naming conventions.

**Why this priority**: Discoverability prevents misuse and reduces trial-and-error when adopting the new invocation style.

**Independent Test**: Can be fully tested by listing or viewing available skill-style commands and verifying known mapped workflow steps are present.

**Acceptance Scenarios**:

1. **Given** multiple workflow steps are configured for skill-style invocation, **When** a maintainer checks available skills, **Then** each exposed step appears with its command name.

---

### User Story 3 - Receive clear feedback for invalid invocations (Priority: P3)

A maintainer receives actionable feedback when attempting to invoke a step-backed skill that is unknown, unavailable, or invalid.

**Why this priority**: Clear failure feedback is necessary for reliable daily use and faster troubleshooting.

**Independent Test**: Can be fully tested by invoking an invalid or unavailable `/agdt.<step>` command and verifying that the response explains the problem and next action.

**Acceptance Scenarios**:

1. **Given** a maintainer invokes `/agdt.unknownstep`, **When** no mapped workflow step exists, **Then** the system returns a clear error that the skill is not available.
2. **Given** a mapped step is temporarily unavailable, **When** the maintainer invokes the command, **Then** the system explains the failure reason and suggests a retry or alternative action.

---

### Edge Cases

- What happens when two workflow steps would resolve to the same `/agdt.<name>` command?
- How does the system handle invocation attempts for step-backed skills that are disabled by policy or context?
- What happens when required step inputs are missing or malformed in a skill-style command?
- How does the system behave when a step-backed skill exceeds expected execution time?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow invocation of an eligible workflow step using `/agdt.<step-name>` skill-style command syntax.
- **FR-002**: The system MUST map each exposed skill-style command to one and only one workflow step.
- **FR-003**: The system MUST preserve the workflow step behavior when invoked as a skill, including expected inputs, outputs, and completion status.
- **FR-004**: The system MUST validate required invocation inputs before attempting execution and return clear guidance when inputs are invalid.
- **FR-005**: The system MUST provide users with visibility into which workflow steps are currently available as skill-style commands.
- **FR-006**: The system MUST return a clear, user-readable error when a requested `/agdt.<step-name>` command is not mapped.
- **FR-007**: The system MUST handle execution failures of mapped step-backed skills by returning actionable error feedback without exposing sensitive internal details.
- **FR-008**: The system MUST record each step-backed skill invocation outcome (success/failure) for maintainers to review operational usage.

### Non-Functional Requirements

- **NFR-001**: Skill-style invocation responses MUST be understandable by non-authors of the workflow and use consistent wording patterns for success and failure.
- **NFR-002**: For valid invocations under normal operating conditions, users MUST receive an initial execution acknowledgment within 5 seconds.
- **NFR-003**: The feature MUST support adoption without requiring maintainers to relearn workflow semantics beyond command naming.
- **NFR-004**: Failure messaging MUST avoid disclosing internal-only system details while still enabling maintainers to correct input or retry safely.

### Key Entities *(include if feature involves data)*

- **Skill Command Mapping**: Defines the association between a `/agdt.<step-name>` command and a workflow step, including command name, step identifier, availability state, and input expectations.
- **Skill Invocation Request**: Represents a user-issued skill command attempt, including requested command, provided inputs, requester context, and timestamp.
- **Skill Invocation Result**: Represents the outcome of an invocation, including final status, user-facing message, and completion time.

### Assumptions

- Existing workflow steps already have defined execution behavior that can be reused through skill-style invocation.
- Only authorized maintainers can invoke workflow-related skill commands in current operating contexts.
- Naming follows `/agdt.<step-name>` convention, where `<step-name>` is derived from an existing workflow step identifier.

### Dependencies

- An existing workflow step registry or equivalent source of truth is available for determining which steps can be exposed as skills.
- Existing command execution and result-reporting flows are available to surface invocation outcomes to maintainers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 90% of targeted workflow steps identified for this enhancement can be invoked successfully through `/agdt.<step-name>` commands in acceptance testing.
- **SC-002**: 95% of valid skill-style invocations provide users an initial acknowledgment within 5 seconds during normal operations.
- **SC-003**: At least 90% of maintainers in pilot usage can successfully invoke an intended workflow step via skill-style commands on their first attempt.
- **SC-004**: Support requests related to "how to run this workflow step" decrease by at least 30% within one release cycle after rollout.
