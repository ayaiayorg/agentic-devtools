# Feature Specification: Shared review threads across identities for Review Activity Log, Overall PR Review Summary, and File Review Summary

**Feature Branch**: `speckit/1517/phase-1-specify`
**Created**: 2026-05-22
**Status**: Draft
**Source Issue**: #1517 (<https://github.com/ayaiayorg/agentic-devtools/issues/1517>)

## Problem Statement *(mandatory)*

Current review-thread scaffolding can create duplicate Review Activity Log,
Overall PR Review Summary, and File Review Summary threads when a different
identity continues an existing review. This fragments status history across
multiple threads for the same purpose and makes review state harder to track.
The desired behavior is deterministic cross-identity reuse of existing
canonical threads by posting scaffolded replies in matching threads and creating
new threads only when no reusable match exists.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reuse Review Activity Log Thread Across Identities (Priority: P1)

As a reviewer, I want the review activity log thread to be reused even when comment authors differ, so each PR keeps a single canonical activity-log thread.

**Why this priority**: Activity-log duplication causes noisy PR timelines and makes review history harder to follow.

**Independent Test**: Can be tested by seeding a PR with an existing activity-log thread from one identity, then posting with another identity and verifying the same thread ID is reused.

**Covers**: FR-001, FR-006

**Acceptance Scenarios**:

1. **Given** a PR already has one activity-log thread, **When** a different identity posts the next activity update,
   **Then** the existing activity-log thread is reused by adding a scaffolded reply instead of creating a new thread.
2. **Given** no activity-log thread exists, **When** the first activity update is posted, **Then** exactly one activity-log thread is created.

---

### User Story 2 - Reuse Overall PR Review Summary Thread Across Identities (Priority: P1)

As a PR reviewer, I want the overall summary thread to be reused across identities, so the PR has one durable status summary location.

**Why this priority**: The overall summary is a top-level review artifact and must remain stable for humans and automation.

**Independent Test**: Can be tested by running review updates from multiple identities and verifying all overall-summary updates target a single thread.

**Covers**: FR-002, FR-005, FR-006

**Acceptance Scenarios**:

1. **Given** an overall summary thread already exists, **When** another identity updates summary status,
   **Then** the existing overall-summary thread is reused by adding a scaffolded reply,
   without creating a new top-level thread.
2. **Given** multiple unrelated PR threads exist, **When** summary lookup runs, **Then** only the thread classified as overall summary is selected.

---

### User Story 3 - Reuse File Review Summary Threads Across Identities (Priority: P1)

As a reviewer, I want file-specific review summary threads to be reused across identities, so each file retains a single authoritative summary thread.

**Why this priority**: File-level duplication breaks traceability and can desynchronize status and suggestion state.

**Independent Test**: Can be tested by creating file review summaries from identity A, then continuing review with identity B and verifying updates map to existing file threads.

**Covers**: FR-003, FR-005, FR-006

**Acceptance Scenarios**:

1. **Given** a file summary thread already exists for `/src/module.py`, **When** another identity reviews the same file, **Then** it reuses that same file summary thread by adding a scaffolded reply.
2. **Given** a file has no existing summary thread, **When** first reviewed, **Then** one new file summary thread is created and persisted.

---

### User Story 4 - Deterministic Thread Classification and Matching (Priority: P2)

As the review workflow engine, I want deterministic classification and matching for activity/overall/file thread types, so thread reuse is reliable and idempotent.

**Why this priority**: Correct reuse depends on accurately identifying existing thread intent.

**Independent Test**: Can be tested with mixed thread sets (different authors, statuses, and content) and asserting stable classification and match results.

**Covers**: FR-004

**Acceptance Scenarios**:

1. **Given** mixed PR threads (discussion, activity-log, overall summary, and file summary), **When** classification runs, **Then** each target type is identified consistently.
2. **Given** both resolved and active candidate threads, **When** matching runs, **Then** matching respects defined reuse rules and does not pick unrelated threads.

---

### User Story 5 - Backward-Compatible Behavior in Mixed and Legacy Scenarios (Priority: P2)

As a maintainer, I want thread reuse to work with legacy review-state data and mixed old/new thread patterns, so existing PR workflows continue without migration breaks.

**Why this priority**: Backward compatibility is required to avoid interrupting in-flight reviews.

**Independent Test**: Can be tested by loading legacy state and legacy thread structures, then running updates and confirming successful reuse without duplicate creation.

**Covers**: FR-007, FR-008

**Acceptance Scenarios**:

1. **Given** legacy review-state entries with previously created summary threads, **When** reuse logic runs, **Then** the workflow continues using those threads.
2. **Given** partially migrated PRs with some reusable and some missing thread types, **When** update operations run, **Then** existing threads are reused and only missing ones are created.

---

### Edge Cases

- What happens when duplicate candidate threads exist for the same type?
  The system chooses a deterministic winner and avoids creating additional duplicates
  using this order: prefer active threads over resolved threads, then lowest thread ID
  (earliest created) as tie-breaker.
- How does the system handle deleted or renamed files after an existing file summary thread was created?
  The system avoids incorrect cross-file reuse and only reuses when normalized file path equality
  matches the file-summary marker payload.
- What happens when the only matching thread is resolved?
  Reuse follows defined policy and remains idempotent without creating unnecessary new threads;
  if no active match exists, the earliest resolved match (lowest thread ID) is reused.
- What happens in dry-run mode? Classification and planned reuse are reported without creating or mutating threads.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect and reuse an existing Review Activity Log thread even when the current actor identity differs from the original author.
- **FR-002**: System MUST detect and reuse an existing Overall PR Review Summary thread across identities.
- **FR-003**: System MUST detect and reuse existing File Review Summary threads across identities using deterministic file/thread matching.
- **FR-004**: System MUST classify candidate threads into activity-log, overall-summary, file-summary, or unrelated categories using stable matching rules.
  - When multiple candidates exist for a target type, selection MUST be deterministic: prefer active over resolved, then choose the lowest thread ID.
  - For file-summary reuse, matching MUST use normalized file path equality between the target file and the parsed marker `file` value.
- **FR-005**: System MUST persist reused thread identifiers in review state so subsequent updates continue targeting the same threads.
- **FR-006**: System MUST avoid creating duplicate activity-log, overall-summary, or file-summary threads when a reusable thread already exists.
- **FR-007**: System MUST support mixed scenarios where some thread types are reused and missing thread types are created exactly once.
- **FR-008**: System MUST preserve backward compatibility with legacy review-state/thread layouts used by existing in-progress reviews.

### Non-Functional Requirements

- **NFR-001**: Thread lookup and classification MUST not introduce a noticeable regression in review update latency for normal PR thread volumes.
- **NFR-002**: Reuse behavior MUST be transparent in logs/output so operators can understand why a thread was reused or created.
- **NFR-003**: Repeated executions with unchanged PR thread data MUST be idempotent (no additional thread creation).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In re-review workflows across different identities, 100% of updates to activity-log, overall-summary, and existing file-summary types reuse the correct existing thread.
- **SC-002**: In mixed legacy/new scenarios, tests assert zero duplicate activity-log, overall-summary, and file-summary threads by validating created-thread counts and reused thread IDs.
- **SC-003**: Automated tests cover cross-identity reuse, classification, mixed scenarios, and backward-compatibility behavior for all three summary thread types.
- **SC-004**: Measured API usage for review-thread updates does not increase versus baseline for equivalent review operations.
