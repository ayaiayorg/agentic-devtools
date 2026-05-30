# Feature Specification: dispatch_repair: Suppressed Copilot review comments not included in repair dispatch comment

**Feature Branch**: `speckit/1653/phase-1-specify`  
**Created**: 2026-05-30  
**Status**: Draft  
**Input**: User description: "dispatch_repair: Suppressed Copilot review comments not included in repair dispatch comment"  
**Source Issue**: #1653 (<https://github.com/ayaiayorg/agentic-devtools/issues/1653>)

## Problem Statement

`dispatch_repair` currently builds repair prompts only from API-visible review comments, so Copilot feedback
that is suppressed due to low confidence is omitted from the generated `@copilot` comment. The implementation
needs to recover those suppressed findings from a reliable GitHub review data source and pass them through the
existing repair-comment rendering path.

## Bug Description

When Copilot marks review comments as "suppressed due to low confidence," those comments are not included in the @copilot repair dispatch comment, even though the non-suppressed inline comments are
included correctly.

## Root Cause

The `dispatch_repair` action (and the orchestrator's `_dispatch_repair` function) fetches inline review comments by calling:

```text
GET /repos/{owner}/{repo}/pulls/{pr_number}/reviews/{review_id}/comments
```

However, the current REST review-comments endpoint does not provide all
suppressed feedback needed by repair dispatch. The implementation should recover
suppressed comments from a reliable GitHub review data source (for example,
GraphQL minimized comments or the review body when no structured API data is
available):

```html
<details>
<summary>Comments suppressed due to low confidence (N)</summary>
...
</details>
```

Because `list_review_comments` only processes the REST API response, these suppressed comments are silently dropped and never reach `_build_repair_comment`, even though that function already has logic
to handle `is_suppressed=True` comments (formatting them with a `(suppressed comment)` label).

## Impact

The repair dispatch @copilot comment is missing context about suppressed feedback. The Copilot coding agent receives an incomplete picture of the review and may not address issues that the reviewer
flagged with lower confidence.

## Steps to Reproduce

1. Open a PR where Copilot posts a review with ≥1 suppressed comment (marked *"suppressed due to low confidence"*) alongside regular inline comments.
2. Observe that the pipeline dispatches a repair comment (`@copilot ...`).
3. Verify that the repair comment lists only the non-suppressed inline comments and omits the suppressed feedback.

When suppressed review comments are omitted, maintainers must manually inspect the Copilot review details and relay
that feedback to the repair agent. Automating inclusion of suppressed feedback reduces missed review context without
changing the existing inline-comment dispatch flow.

## User Scenarios & Testing

### User Story 1 - Include Suppressed Review Feedback (Priority: P1)

As a maintainer relying on repair dispatch, I need suppressed Copilot review comments to be included in the generated
`@copilot` repair comment so the repair agent receives the full review context without manual intervention.

**Why this priority**: This is the core bug fix requested by the source issue.
Without it, actionable Copilot feedback can be omitted from repair dispatch and
the agent may leave review findings unaddressed.

**Independent Test**: Can be tested by constructing a Copilot review fixture
that contains both REST-visible inline comments and suppressed feedback,
running repair dispatch comment generation, and verifying the output includes
both types of comments with the suppressed label.

**Acceptance Scenarios**:

1. **Given** a Copilot review with regular inline comments and a "suppressed due to low confidence" details block,
   **When** repair dispatch builds the `@copilot` comment, **Then** both regular and suppressed comments are included.
2. **Given** a suppressed comment with a file path and body text, **When** it is rendered in the repair dispatch comment, **Then** the entry identifies the affected file and labels the feedback as suppressed.

### User Story 2 - Handle Suppressed-Only Feedback (Priority: P1)

As a maintainer reviewing a PR where Copilot only emitted suppressed feedback, I
need repair dispatch to still include that feedback so no review finding is
silently lost.

**Why this priority**: A suppressed-only review is the highest-risk failure mode because dispatch would otherwise provide no review context at all despite Copilot having findings.

**Independent Test**: Can be tested with a review fixture that has no
REST-visible inline comments and only suppressed feedback, then verifying repair
dispatch still emits an `@copilot` comment containing each suppressed entry and
its file context.

**Acceptance Scenarios**:

1. **Given** a Copilot review whose actionable feedback appears only in the suppressed-comments block,
   **When** repair dispatch runs, **Then** the generated `@copilot` comment includes each suppressed comment with
   its file context.

### User Story 3 - Preserve Existing Dispatch Behavior (Priority: P2)

As a maintainer of the CI repair loop, I need the suppressed-comment handling to
be additive so reviews without suppressed comments continue to dispatch the same
regular inline feedback as before.

**Why this priority**: Preserving existing behavior prevents the bug fix from regressing the current inline-comment dispatch path that already works for non-suppressed feedback.

**Independent Test**: Can be tested by running the existing regular-inline-comment
repair dispatch fixture with no suppressed feedback and verifying the generated
comment is unchanged except for expected deterministic metadata, with no
synthetic suppressed entries.

**Acceptance Scenarios**:

1. **Given** a Copilot review with no suppressed-comments details block, **When** repair dispatch builds the
   `@copilot` comment, **Then** the generated comment contains the same regular inline feedback as before and no
   synthetic suppressed entries.

### Edge Cases

- What happens when the REST review comments endpoint returns regular comments
  but the supplemental suppressed-comment source is unavailable or malformed?
  Repair dispatch should preserve regular comments and fail softly without
  blocking dispatch.
- How does the system handle suppressed comments that do not include a parseable
  file path? The repair comment should still include the feedback with an
  explicit unknown-file marker rather than dropping it silently.
- What happens when the same feedback appears in both the REST comments and the
  supplemental suppressed-comment source? The implementation should deduplicate
  according to FR-004 while preserving the non-suppressed rendering when
  available.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST include suppressed Copilot review comments in repair dispatch context in addition to regular inline review comments.

- **FR-002**: The system MUST extract enough information from each suppressed comment to render its affected file and comment body in the `@copilot` repair comment.

- **FR-003**: The system MUST clearly label suppressed comments as suppressed when rendering them in the repair dispatch comment.

- **FR-004**: The system MUST avoid duplicating the same review feedback when a
  comment is available from more than one source. Two entries are duplicates only
  when their file paths match after trimming whitespace and removing one leading
  `/`, and their comment bodies match after normalizing CRLF to LF and trimming
  surrounding whitespace; when one duplicate is non-suppressed, that entry MUST
  be preserved for rendering.

- **FR-005**: The system MUST preserve existing repair dispatch behavior for reviews that contain no suppressed comments.

### Non-Functional Requirements

- **NFR-001**: The implementation must complete all operations within 120 seconds under normal conditions.

- **NFR-002**: The implementation must maintain backward compatibility with existing interfaces and contracts.

## Success Criteria

### Measurable Outcomes

- **SC-001**: For a representative Copilot review containing both regular and suppressed comments, the generated repair dispatch comment includes every regular comment and every suppressed comment.

- **SC-002**: For a Copilot review containing only suppressed comments, repair dispatch still produces an `@copilot` comment containing those suppressed comments.

- **SC-003**: For reviews without suppressed comments, the repair dispatch comment remains unchanged from the current regular-inline-comment behavior.

*Generated by Copilot SDK (claude-opus-4.6)*
