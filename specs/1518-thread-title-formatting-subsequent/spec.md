# Feature Specification: Thread title formatting for subsequent review comments

**Feature Branch**: `speckit/1518/phase-2-clarify`  
**Created**: 2026-05-22  
**Status**: Draft  
**Source Issue**: #1518 (<https://github.com/ayaiayorg/agentic-devtools/issues/1518>)

## Problem Statement

Review comment rendering currently repeats `## <title>` in subsequent comments within
the same thread. This makes ongoing thread updates noisy and visually redundant.
Subsequent comments should instead use a compact commit header format:
`### Commit: [<short_hash>](<commit_url>)`.

## Clarifications

### Session 2026-05-22

- Q: Which specific render function produces the repeated `## <title>` in subsequent comments — is this `render_file_summary()` in `review_templates.py` being called for both initial (PATCH of
  top-level comment) and follow-up (reply) comments, or is there a separate reply renderer? → A: The repeated title occurs when `render_file_summary()` is called to render reply comments posted via
  `_post_reply()` or convergence repair. The same function is used for both top-level PATCH updates and reply rendering. The fix should differentiate by introducing an `is_subsequent` (or equivalent)
  parameter to `render_file_summary()` that replaces the `## File Review Summary: {fileName}` heading with the compact `### Commit:` header for replies.
- Q: What constitutes "comment position" for the purposes of FR-003 — is it determined by the Azure DevOps thread comment index (comment ID 1 = initial, comment ID > 1 = subsequent), or by a
  caller-supplied flag? → A: Position is determined by a caller-supplied boolean parameter (e.g., `is_subsequent: bool = False`) rather than by inspecting Azure DevOps comment IDs at render time. The
  caller (e.g., `_post_activity_log_entry`, convergence repair, file review reply flows) already knows whether it is producing a top-level update or a reply, so it passes the flag explicitly. This
  keeps rendering pure and testable.
- Q: Should the `short_hash` length be 7 characters (matching the existing `_format_activity_log_entry` convention) or 12 characters (matching `review.commit_hash_short` in state)? → A: Use 7
  characters to match the existing `_format_activity_log_entry` convention and standard Git short-hash convention. The 12-character variant in state is used only for directory naming; display contexts
  use 7.
- Q: Does FR-009's prohibition on altering activity log payload structure mean that `_format_activity_log_entry()` must remain completely unchanged, or can it adopt the new header format for its own
  subsequent-comment usage? → A: `_format_activity_log_entry()` MUST remain completely unchanged. The activity log already uses its own distinct `### Review Session —` header format for replies and
  does not suffer from the repeated-title problem. FR-009 exists to prevent accidental regressions in that path. Only file-summary and overall-summary reply renderers are in scope for the header
  change.
- Q: For the convergence/repair flow, when a subsequent comment is flagged as invalid (has `## <title>` instead of `### Commit:`), should repair attempt to extract `short_hash` and `commit_url` from
  review state, or from the existing comment content? → A: Repair MUST source `short_hash` and `commit_url` from `ReviewState` (specifically `review_state.commitHash` and derived commit URL), not from
  the comment content. The comment content is considered untrusted/stale. If `ReviewState` lacks the commit hash, the FR-008 fallback (`### Commit: unknown`) applies.

## Scope

**In scope:**

- Formatting rules for first vs. subsequent thread comments
- Updating render callers to pass enough context to choose the correct format
- Adding an `is_subsequent` parameter to both `render_file_summary()` and `render_overall_summary()` to control header output
- Validation/repair logic for header format in follow-up comments
- Regression safeguards to preserve existing activity log behavior (no changes to `_format_activity_log_entry()`)

**Out of scope:**

- Changes to thread creation APIs or thread lifecycle behavior
- Changes to unrelated comment body content outside title/header formatting
- Changes to `_format_activity_log_entry()` or its `### Review Session —` header format
- Changes to the 12-character `review.commit_hash_short` state key (display uses 7 characters)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Compact follow-up headers in review threads (Priority: P1)

As a PR reviewer, I want follow-up comments in a thread to use a compact commit header
instead of repeating the full title, so that thread history is easier to scan.

**Why this priority**: This is the direct behavior change requested by issue #1518.

**Covers**: FR-001, FR-002, FR-003, FR-004, FR-010

**Independent Test**: Render initial and follow-up comments for both
`render_file_summary(...)` and `render_overall_summary(...)`; verify follow-ups
contain `### Commit: [<short_hash>](<commit_url>)` and do not include `## <title>`.

**Acceptance Scenarios**:

1. **Given** a thread with an existing top-level summary comment, **When** a follow-up
   comment is generated (via `render_file_summary(…, is_subsequent=True)`), **Then** the follow-up uses a `### Commit: [<7-char-hash>](<commit_url>)` header.
2. **Given** a new thread with no prior comment, **When** the initial comment is
   generated (via `render_file_summary(…, is_subsequent=False)`), **Then** the initial comment retains the existing `## File Review Summary: {fileName}` title format.
3. **Given** an existing overall-summary thread, **When** a follow-up comment is
   generated (via `render_overall_summary(…, is_subsequent=True)`), **Then** the
   follow-up uses a `### Commit: [<7-char-hash>](<commit_url>)` header.
4. **Given** a new overall-summary thread, **When** the initial comment is generated
   (via `render_overall_summary(…, is_subsequent=False)`), **Then** the initial
   comment retains the existing `## Overall PR Review Summary` title format.

---

### User Story 2 — Correct format validation during convergence/repair (Priority: P2)

As a maintainer, I want convergence logic to validate headers based on comment position,
so that repair flows enforce consistent formatting.

**Why this priority**: Without position-aware validation, repair logic can reintroduce
the old repeated-title format.

**Covers**: FR-005, FR-006, FR-007, FR-008

**Independent Test**: Run validation on both top-level and reply-style comments and
verify position-specific pass/fail outcomes.

**Acceptance Scenarios**:

1. **Given** a top-level comment, **When** format validation runs, **Then** `## <title>`
   remains valid.
2. **Given** a subsequent comment with `## <title>`, **When** format validation runs,
   **Then** it is flagged as invalid and repair rewrites it to `### Commit: [<short_hash>](<commit_url>)` sourcing values from `ReviewState`.

---

### User Story 3 — No regressions in activity logging (Priority: P3)

As an operator, I want activity logging behavior to stay unchanged, so that formatting
changes do not break observability.

**Why this priority**: The change should be constrained to comment formatting only.
`_format_activity_log_entry()` and its `### Review Session —` format are explicitly
excluded from any modifications.

**Covers**: FR-009

**Independent Test**: Compare activity log fields before and after applying the
formatting update for equivalent operations.

**Acceptance Scenarios**:

1. **Given** a comment update that changes only header formatting, **When** activity is
   logged, **Then** log schema and key fields remain unchanged.

---

### Edge Cases

- **Missing commit URL or hash in follow-up comments**: Use deterministic fallback per FR-008 — `### Commit: <short_hash>` (hash only, no link) when URL is missing; `### Commit: unknown` when hash is
  missing.
- **Single-comment threads where no follow-up header should be used**: Caller passes `is_subsequent=False`; header remains `## <title>`.
- **Repair operation on a partially formatted follow-up header**: Repair always re-renders from ReviewState rather than patching existing content, ensuring deterministic output.
- **Replies posted to legacy threads containing old `## <title>` style comments**: The convergence system detects the stale format and repairs to `### Commit:` using ReviewState as the source of
  truth.
- **`short_hash` display length**: Always 7 characters in rendered output (first 7 of `commitHash` from ReviewState).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST keep existing top-level thread comment title formatting
  unchanged (`## File Review Summary: {fileName}` for file summaries; `## Overall PR Review Summary` for overall summaries).
- **FR-002**: The system MUST render subsequent thread comments with
  `### Commit: [<short_hash>](<commit_url>)` as the header when both values are
  available. `short_hash` is the first 7 characters of the commit hash from ReviewState.
- **FR-003**: The system MUST choose title/header format based on a caller-supplied
  `is_subsequent` boolean parameter (not by inspecting Azure DevOps comment IDs at render time). The parameter defaults to `False`.
- **FR-004**: The system MUST preserve non-header body content when switching to commit
  headers.
- **FR-005**: Validation logic MUST treat `## <title>` as valid for initial comments only
  (where `is_subsequent=False`).
- **FR-006**: Validation logic MUST treat `### Commit:` as required for subsequent
  comments (where `is_subsequent=True`).
- **FR-007**: Repair logic MUST rewrite invalid subsequent headers to the `### Commit:`
  format (link form when both hash and URL are available; fallback form per FR-008
  otherwise). Repair sources commit metadata exclusively from `ReviewState`.
- **FR-008**: Repair logic MUST degrade gracefully when commit metadata is missing
  by using deterministic fallback headers that still start with `### Commit:`: use
  `### Commit: <short_hash>` when URL is missing but hash exists, and use
  `### Commit: unknown` when hash is missing (with or without URL).
- **FR-009**: Rendering and repair changes MUST NOT alter activity log payload structure.
  Specifically, `_format_activity_log_entry()` and the `### Review Session —` header
  format MUST remain unchanged.
- **FR-010**: Automated tests MUST cover initial-comment, subsequent-comment, and
  validation/repair paths.

### Non-Functional Requirements

- **NFR-001**: Header formatting rules MUST remain deterministic for identical inputs
  (same `is_subsequent`, `commit_hash`, and `commit_url` values always produce the same output).
- **NFR-002**: Formatting updates MUST NOT introduce additional API calls. The
  `is_subsequent` flag is passed by the caller; no Azure DevOps API inspection is
  required to determine comment position.
- **NFR-003**: The implementation MUST remain backward-compatible with existing stored
  thread content and repair workflows. Legacy `## <title>` comments in existing threads
  are only repaired when the convergence system runs; they are not retroactively modified
  by the rendering change alone.

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

---
*Generated by Copilot SDK (claude-opus-4.6)*
