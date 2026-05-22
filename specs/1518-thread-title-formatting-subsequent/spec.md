# Feature Specification: Thread title formatting for subsequent review comments

**Feature Branch**: `speckit/1518/phase-1-specify`  
**Created**: 2026-05-22  
**Status**: Draft  
**Source Issue**: #1518 (<https://github.com/ayaiayorg/agentic-devtools/issues/1518>)

## Problem Statement

Review comment rendering currently repeats `## <title>` in subsequent comments within
the same thread. This makes ongoing thread updates noisy and visually redundant.
Subsequent comments should instead use a compact commit header format:
`### Commit: [<short_hash>](<commit_url>)`.

## Scope

**In scope:**

- Formatting rules for first vs. subsequent thread comments
- Updating render callers to pass enough context to choose the correct format
- Validation/repair logic for header format in follow-up comments
- Regression safeguards to preserve existing activity log behavior

**Out of scope:**

- Changes to thread creation APIs or thread lifecycle behavior
- Changes to unrelated comment body content outside title/header formatting

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Compact follow-up headers in review threads (Priority: P1)

As a PR reviewer, I want follow-up comments in a thread to use a compact commit header
instead of repeating the full title, so that thread history is easier to scan.

**Why this priority**: This is the direct behavior change requested by issue #1518.

**Independent Test**: Render a thread with an initial comment and one follow-up; verify
the follow-up contains `### Commit: [<short_hash>](<commit_url>)` and does not include `## <title>`.

**Acceptance Scenarios**:

1. **Given** a thread with an existing top-level summary comment, **When** a follow-up
   comment is generated, **Then** the follow-up uses a `### Commit:` header.
2. **Given** a new thread with no prior comment, **When** the initial comment is
   generated, **Then** the initial comment retains the existing top-level title format.

---

### User Story 2 — Correct format validation during convergence/repair (Priority: P2)

As a maintainer, I want convergence logic to validate headers based on comment position,
so that repair flows enforce consistent formatting.

**Why this priority**: Without position-aware validation, repair logic can reintroduce
the old repeated-title format.

**Independent Test**: Run validation on both top-level and reply-style comments and
verify position-specific pass/fail outcomes.

**Acceptance Scenarios**:

1. **Given** a top-level comment, **When** format validation runs, **Then** `## <title>`
   remains valid.
2. **Given** a subsequent comment with `## <title>`, **When** format validation runs,
   **Then** it is flagged as invalid and repair rewrites it to `### Commit:`.

---

### User Story 3 — No regressions in activity logging (Priority: P3)

As an operator, I want activity logging behavior to stay unchanged, so that formatting
changes do not break observability.

**Why this priority**: The change should be constrained to comment formatting only.

**Independent Test**: Compare activity log fields before and after applying the
formatting update for equivalent operations.

**Acceptance Scenarios**:

1. **Given** a comment update that changes only header formatting, **When** activity is
   logged, **Then** log schema and key fields remain unchanged.

---

### Edge Cases

- Missing commit URL or hash in follow-up comments
- Single-comment threads where no follow-up header should be used
- Repair operation on a partially formatted follow-up header
- Replies posted to legacy threads containing old `## <title>` style comments

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST keep existing top-level thread comment title formatting
  unchanged.
- **FR-002**: The system MUST render subsequent thread comments with
  `### Commit: [<short_hash>](<commit_url>)` as the header when both values are
  available.
- **FR-003**: The system MUST choose title/header format based on comment position in the
  thread (initial vs. subsequent).
- **FR-004**: The system MUST preserve non-header body content when switching to commit
  headers.
- **FR-005**: Validation logic MUST treat `## <title>` as valid for initial comments only.
- **FR-006**: Validation logic MUST treat `### Commit:` as required for subsequent
  comments.
- **FR-007**: Repair logic MUST rewrite invalid subsequent headers to the `### Commit:`
  format (link form when both hash and URL are available; fallback form per FR-008
  otherwise).
- **FR-008**: Repair logic MUST degrade gracefully when commit metadata is missing
  by using deterministic fallback headers that still start with `### Commit:`: use
  `### Commit: <short_hash>` when URL is missing but hash exists, and use
  `### Commit: unknown` when hash is missing (with or without URL).
- **FR-009**: Rendering and repair changes MUST NOT alter activity log payload structure.
- **FR-010**: Automated tests MUST cover initial-comment, subsequent-comment, and
  validation/repair paths.

### Non-Functional Requirements

- **NFR-001**: Header formatting rules MUST remain deterministic for identical inputs.
- **NFR-002**: Formatting updates MUST NOT introduce additional API calls.
- **NFR-003**: The implementation MUST remain backward-compatible with existing stored
  thread content and repair workflows.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of newly generated subsequent thread comments use `### Commit:`
  headers in tests and manual verification.
- **SC-002**: 0 regressions are observed in activity log schema/fields for affected
  operations.
- **SC-003**: Validation/repair tests confirm position-aware rules for both initial and
  subsequent comments.
- **SC-004**: The updated spec provides complete Phase 1 sections required to support
  downstream clarify/plan/tasks workflows.
