# Feature Specification: dispatch_repair: Suppressed Copilot review comments not included in repair dispatch comment

> ⚠️ **FALLBACK SKELETON** — This specification was generated via deterministic fallback after all LLM retry attempts were exhausted. It requires manual enrichment. Review each section and replace
> placeholder content with detailed, issue-specific information.

**Source Issue**: #1653 (<https://github.com/ayaiayorg/agentic-devtools/issues/1653>)

## Problem Statement

`dispatch_repair` currently builds repair prompts only from API-visible review comments, so Copilot feedback that is suppressed due to low confidence is omitted from the generated `@copilot` comment. The implementation needs to recover those suppressed findings from the review body and pass them through the existing repair-comment rendering path.

## Bug Description

When Copilot marks review comments as "suppressed due to low confidence," those comments are not included in the @copilot repair dispatch comment, even though the non-suppressed inline comments are
included correctly.

## Root Cause

The `dispatch_repair` action (and the orchestrator's `_dispatch_repair` function) fetches inline review comments by calling:

```text
GET /repos/{owner}/{repo}/pulls/{pr_number}/reviews/{review_id}/comments
```

However, GitHub does **not** surface suppressed comments as API-level review comment objects. Instead, they only appear as structured HTML/markdown inside the review body:

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

When suppressed review comments are omitted, maintainers must manually inspect the Copilot review details and relay that feedback to the repair agent. Automating inclusion of suppressed feedback reduces missed review context without changing the existing inline-comment dispatch flow.

## User Scenarios & Testing

### User Story 1 - Include Suppressed Review Feedback (Priority: P1)

As a maintainer relying on repair dispatch, I need suppressed Copilot review comments to be included in the generated `@copilot` repair comment so the repair agent receives the full review context without manual intervention.

**Acceptance Scenarios**:

1. **Given** a Copilot review with regular inline comments and a "suppressed due to low confidence" details block, **When** repair dispatch builds the `@copilot` comment, **Then** both regular and suppressed comments are included.
2. **Given** a suppressed comment with a file path and body text, **When** it is rendered in the repair dispatch comment, **Then** the entry identifies the affected file and labels the feedback as suppressed.

### User Story 2 - Handle Suppressed-Only Feedback (Priority: P1)

As a maintainer reviewing a PR where Copilot only emitted suppressed feedback, I need repair dispatch to still include that feedback so no review finding is silently lost.

**Acceptance Scenarios**:

1. **Given** a Copilot review whose actionable feedback appears only in the suppressed-comments block, **When** repair dispatch runs, **Then** the generated `@copilot` comment includes each suppressed comment with its file context.

### User Story 3 - Preserve Existing Dispatch Behavior (Priority: P2)

As a maintainer of the CI repair loop, I need the suppressed-comment handling to be additive so reviews without suppressed comments continue to dispatch the same regular inline feedback as before.

**Acceptance Scenarios**:

1. **Given** a Copilot review with no suppressed-comments details block, **When** repair dispatch builds the `@copilot` comment, **Then** the generated comment contains the same regular inline feedback as before and no synthetic suppressed entries.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST include suppressed Copilot review comments in repair dispatch context in addition to regular inline review comments.

- **FR-002**: The system MUST extract enough information from each suppressed comment to render its affected file and comment body in the `@copilot` repair comment.

- **FR-003**: The system MUST clearly label suppressed comments as suppressed when rendering them in the repair dispatch comment.

- **FR-004**: The system MUST avoid duplicating the same review feedback when a comment is available from more than one source.

- **FR-005**: The system MUST preserve existing repair dispatch behavior for reviews that contain no suppressed comments.

### Non-Functional Requirements

- **NFR-001**: The implementation must complete all operations within 120 seconds under normal conditions.

- **NFR-002**: The implementation must maintain backward compatibility with existing interfaces and contracts.

## Success Criteria

- **SC-001**: For a representative Copilot review containing both regular and suppressed comments, the generated repair dispatch comment includes every regular comment and every suppressed comment.

- **SC-002**: For a Copilot review containing only suppressed comments, repair dispatch still produces an `@copilot` comment containing those suppressed comments.

- **SC-003**: For reviews without suppressed comments, the repair dispatch comment remains unchanged from the current regular-inline-comment behavior.

---
*Generated via fallback skeleton — manual enrichment required*

---
*Generated by Copilot SDK (claude-opus-4.6)*
