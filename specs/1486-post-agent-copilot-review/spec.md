# Feature Specification: Post-Agent Copilot Review Evaluator

**Feature Branch**: `speckit/1486/phase-1-specify`
**Created**: 2026-05-19
**Status**: Draft
**Source Issue**: #1486 (<https://github.com/ayaiayorg/agentic-devtools/issues/1486>)

## Problem Statement

When a Copilot review runs on a PR and the agent responds via a Copilot comment (e.g., says
fixes already done), but **no machine-parseable final result** (no sentinel) and **no
reply/resolve on review threads**, the review loop is left hanging for human intervention —
even if the code is fine. The system needs a Post-Agent Copilot Review Evaluator that can
programmatically analyze PR state after the Copilot comment, classify the scenario, and take
the appropriate action to unblock the PR.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - PR State Classification (Priority: P1)

As a repository maintainer, I want the system to programmatically classify the PR state after
a Copilot agent comment, so that the correct remediation action can be determined without
human intervention.

**Why this priority**: Classification is the foundation — all other actions depend on correctly
identifying the current PR state. Without this, no automated remediation is possible.

**Independent Test**: Can be tested by providing various PR state snapshots (with/without
sentinels, with/without unresolved threads, with/without code changes) and verifying the
correct classification is returned.

**Applies to**: FR-001, FR-002, FR-003, FR-004, FR-005

**Acceptance Scenarios**:

1. **Given** a PR where the Copilot agent posted a comment saying "already fixed" but no
   sentinel is present, **When** the evaluator runs, **Then** the state is classified as
   `agent_claims_fixed_no_sentinel`.
2. **Given** a PR where the Copilot agent posted a comment and all review threads are already
   resolved, **When** the evaluator runs, **Then** the state is classified as
   `threads_resolved_no_sentinel`.
3. **Given** a PR where the sentinel is present and all threads are resolved, **When** the
   evaluator runs, **Then** the state is classified as `complete` and no further action is
   needed.
4. **Given** a PR where the agent comment indicates changes were made but threads remain
   unresolved, **When** the evaluator runs, **Then** the state is classified as
   `changes_made_threads_unresolved`.
5. **Given** a PR where the agent session ended without any comment, **When** the evaluator
   runs, **Then** the state is classified as `agent_silent`.

---

### User Story 2 - Verify-and-Resolve Threads (Priority: P1)

As a repository maintainer, I want the system to verify that Copilot review feedback has been
addressed in the code and then resolve the corresponding threads, so that the PR can proceed
without manual thread resolution.

**Why this priority**: Thread resolution is the most common missing step that blocks PRs. If
classification says "code is fixed", the system must be able to verify and resolve threads
to complete the loop.

**Independent Test**: Can be tested by setting up a PR with unresolved Copilot review threads
where the code diff shows the issues were addressed, and verifying threads are resolved.

**Applies to**: FR-006, FR-008, FR-009

**Acceptance Scenarios**:

1. **Given** a classified state of `agent_claims_fixed_no_sentinel` with unresolved threads,
   **When** the verify-and-resolve action runs, **Then** each thread's feedback is compared
   against the current code and threads whose feedback is addressed are resolved.
2. **Given** a thread whose feedback is NOT addressed in the code, **When** the
   verify-and-resolve action runs, **Then** that thread remains unresolved and a comment is
   posted noting the unresolved item.
3. **Given** all threads have been verified and resolved, **When** the action completes,
   **Then** a re-review request is posted to trigger the next Copilot review cycle.

---

### User Story 3 - Synthesize Result Summary (Priority: P1)

As a repository maintainer, I want the system to synthesize a machine-parseable result summary
(with the sentinel marker) when the agent failed to produce one, so that the AI PR loop can
proceed to its next phase.

**Why this priority**: The sentinel is the machine-parseable signal that downstream automation
depends on. Without it, the loop cannot finalize.

**Independent Test**: Can be tested by verifying that after the evaluator processes a PR with
no sentinel, a properly formatted result comment with the sentinel is posted.

**Applies to**: FR-007

**Acceptance Scenarios**:

1. **Given** a classified state where the agent completed successfully but no sentinel is
   present, **When** the synthesize action runs, **Then** a PR comment is posted containing
   the sentinel marker and a summary of what the agent did.
2. **Given** the synthesized result, **When** downstream automation reads the PR comments,
   **Then** it can detect the sentinel and proceed normally.

---

### User Story 4 - CLI Entry Point (Priority: P1)

As a CI/CD workflow, I want a single CLI command (`agdt-evaluate-post-agent-state`) that
invokes the evaluator, so that the workflow YAML remains minimal and all logic resides in
testable Python code.

**Why this priority**: The CLI entry point is the integration point between the workflow
trigger and the Python logic. Keeping it as a single command ensures zero decision logic in
YAML.

**Independent Test**: Can be tested by invoking the CLI command with mocked PR state and
verifying it produces the correct classification and action output.

**Applies to**: FR-010, FR-011, FR-013

**Acceptance Scenarios**:

1. **Given** the workflow triggers on a Copilot comment, **When**
   `agdt-evaluate-post-agent-state` is invoked with a PR number, **Then** it analyzes the
   PR state, classifies it, and executes the appropriate action.
2. **Given** the CLI is invoked, **When** it completes, **Then** it outputs a structured JSON
   result containing the classification, action taken, and success/failure status.
3. **Given** a `--dry-run` flag, **When** the CLI is invoked, **Then** it classifies the
   state and reports what action would be taken without executing it.

---

### User Story 5 - Retry Trigger (Priority: P2)

As a repository maintainer, I want the system to re-trigger a Copilot review after resolving
threads and posting the sentinel, so that the PR gets a fresh review pass confirming
everything is clean.

**Why this priority**: A re-review ensures the automated resolution actually satisfied the
original feedback. It's important but depends on the core classification and resolution
stories being functional first.

**Independent Test**: Can be tested by verifying that after thread resolution, a re-review
request is posted and the Copilot review is triggered.

**Applies to**: FR-009

**Acceptance Scenarios**:

1. **Given** the verify-and-resolve action completed successfully, **When** the retry trigger
   runs, **Then** a Copilot re-review is requested on the PR.
2. **Given** the re-review has been requested, **When** the system polls for the new review,
   **Then** it detects the new review and the loop can proceed.

---

### User Story 6 - Agentic Fallback (Priority: P3)

As a repository maintainer, I want the system to trigger a full Copilot agent session with
structured context when programmatic resolution is not possible, so that complex edge cases
are still handled without human intervention.

**Why this priority**: This is the safety net for cases that cannot be resolved
programmatically. It's lowest priority because it requires the classification system to first
identify that programmatic resolution failed.

**Independent Test**: Can be tested by providing a PR state that the programmatic classifier
cannot resolve and verifying a Copilot agent session is triggered with the correct context.

**Applies to**: FR-012

**Acceptance Scenarios**:

1. **Given** a classified state where programmatic resolution is not possible (e.g.,
   `agent_silent` or ambiguous feedback), **When** the agentic fallback runs, **Then** a
   Copilot agent session is triggered with structured context including the PR diff,
   unresolved threads, and agent history.
2. **Given** the fallback has been triggered, **When** the Copilot agent session completes,
   **Then** the evaluator can be re-invoked to verify the agent's work.

---

### Edge Cases

- What happens when the Copilot agent's comment is ambiguous (neither "fixed" nor "can't fix")?
- How does the system handle a PR where the agent made partial fixes (some threads addressed,
  others not)?
- What if the sentinel is present but malformed or incomplete?
- What if thread resolution fails due to GitHub API rate limiting?
- What if the Copilot review was dismissed or superseded by a new review?
- How does the system handle concurrent evaluator invocations on the same PR?
- What if the PR branch has been force-pushed between the agent session and the evaluator run?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `classify_post_agent_state()` pure function that takes a
  `PostAgentSnapshot` (input dataclass capturing PR threads, sentinel presence, head changes)
  and returns a `PostAgentClassification` enum.
- **FR-002**: System MUST detect the presence/absence of the sentinel marker in PR comments.
- **FR-003**: System MUST check unresolved review threads and their resolution status.
- **FR-004**: System MUST detect whether code changes were made after the review was posted.
- **FR-005**: System MUST detect reply status on review threads (replied vs unreplied).
- **FR-006**: System MUST provide action handlers for each classified state, following the
  provider abstraction pattern (`CIPlatformProvider`).
- **FR-007**: System MUST synthesize a sentinel-containing result comment when the agent
  fails to produce one.
- **FR-008**: System MUST verify that review feedback is addressed in code before resolving
  threads.
- **FR-009**: System MUST request a Copilot re-review after resolving threads.
- **FR-010**: System MUST provide a CLI entry point (`agdt-evaluate-post-agent-state`) that
  orchestrates classification and action execution.
- **FR-011**: System MUST support `--dry-run` mode for safe previewing of actions.
- **FR-012**: System MUST trigger an agentic fallback session when programmatic resolution is
  not possible.
- **FR-013**: System MUST output structured JSON results from the CLI command.

### Non-Functional Requirements

- **NFR-001**: Classification function MUST execute in under 5 seconds (excluding API calls).
- **NFR-002**: All scenario handlers MUST be fully unit-testable with mocked
  `CIPlatformProvider` interfaces (decision logic is pure; side effects are injected).
- **NFR-003**: New edge cases MUST be addable as new Python handler functions + test cases,
  not configuration changes.
- **NFR-004**: Zero decision logic in workflow YAML — all branching MUST reside in the Python
  codebase.
- **NFR-005**: CLI output MUST follow existing `agdt-*` command patterns (structured JSON,
  state key updates).
- **NFR-006**: System MUST handle GitHub API rate limiting gracefully with exponential
  backoff and retry.

### Key Entities

- **PostAgentSnapshot**: Input dataclass capturing the PR state at evaluation time (threads,
  sentinel presence, head changes, agent comments, review status).
- **PostAgentClassification**: Enum classifying the snapshot into a scenario (e.g.,
  `agent_claims_fixed_no_sentinel`, `threads_resolved_no_sentinel`, `complete`,
  `changes_made_threads_unresolved`, `agent_silent`).
- **PostAgentAction**: Enum of possible remediation actions (e.g., `verify_and_resolve`,
  `synthesize_sentinel`, `trigger_re_review`, `agentic_fallback`, `no_action`).
- **CIPlatformProvider**: Existing provider abstraction used for platform-agnostic API calls
  (thread resolution, comment posting, review requests).
- **EvaluationResult**: Dataclass containing the classification, action taken, success
  status, and any error details.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 90% of "stuck PR" scenarios (agent commented but loop not finalized) are
  automatically resolved without human intervention within 5 minutes of detection.
- **SC-002**: `classify_post_agent_state()` achieves 100% unit test coverage across all
  defined state variants.
- **SC-003**: Zero decision logic exists in the workflow YAML — confirmed by workflow file
  containing only trigger + CLI invocation.
- **SC-004**: New edge case scenarios can be added with only a new handler function and
  corresponding test (no changes to existing code or configuration required).
- **SC-005**: The evaluator CLI command completes execution (classification + action) within
  30 seconds for a typical PR with fewer than 20 review threads.

## Clarification Items

- **CLARIFY-001**: Should thread verification use semantic code analysis (AST-level
  comparison of feedback vs current code) or heuristic matching (keyword/line-range based)?
  Semantic is more accurate but complex; heuristic is simpler but may miss cases.
- **CLARIFY-002**: What is the exact shape of the workflow YAML trigger — should it reuse the
  existing `issue_comment` trigger in `ai-pr-loop` or add a separate workflow file?

---
*Generated from issue #1486 — Phase 1 specification*
