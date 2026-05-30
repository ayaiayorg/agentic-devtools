# Feature Specification: dispatch_repair: Suppressed Copilot review comments not included in repair dispatch comment

**Feature Branch**: `speckit/1653/phase-2-clarify`  
**Created**: 2026-05-30  
**Status**: Draft  
**Input**: User description: "dispatch_repair: Suppressed Copilot review comments not included in repair dispatch comment"  
**Source Issue**: #1653 (<https://github.com/ayaiayorg/agentic-devtools/issues/1653>)

## Clarifications

### Session 2026-05-30

- Q: What is the reliable data source for suppressed comments — should the implementation
  parse the review body HTML `<details>` block, use the GraphQL `minimizedComment` API,
  or both? → A: Parse
  the review body HTML `<details>` block as the primary source, since GitHub's "suppressed due to low confidence" comments are embedded there and not reliably exposed as
  individual items via REST or GraphQL minimized-comment APIs. If the `<details>` block is absent or malformed, fall back gracefully (log a warning and skip suppressed recovery).
- Q: What file-path extraction strategy should be used for suppressed comments embedded in the review body,
  given that the HTML format uses bold file-path headers or inline code references? → A: Parse
  each suppressed entry for bold-formatted file paths (e.g., **path/to/file.ts**) or code-formatted paths
  (`path/to/file.ts`). When no parseable file path is found, use an explicit `(unknown file)` marker
  rather than dropping the entry.
- Q: Should the implementation fetch the review body via a separate API call (e.g.,
  `GET /repos/{owner}/{repo}/pulls/{pr_number}/reviews/{review_id}`) or is the review body already available in the
  existing data flow? → A: Add a targeted `GET /repos/{owner}/{repo}/pulls/{pr_number}/reviews/{review_id}` call to retrieve
  the review body when `review_id > 0`. This is a single additional API call per dispatch and
  fits within the 120-second NFR budget.
- Q: How should deduplication (FR-004) handle partial body matches where the REST inline
  comment body is a subset of the suppressed entry's body text (or vice versa)?
  → A: Deduplication uses exact
  match only (after normalization per FR-004). Partial/substring matches are not considered duplicates — both entries are preserved. This keeps the logic deterministic and avoids false-positive
  deduplication.
- Q: Should the suppressed-comment parsing logic be implemented as a standalone utility
  function (for independent testability) or inline within `list_review_comments`?
  → A: Implement as a standalone
  utility function (e.g., `_parse_suppressed_from_review_body`) within `github_provider.py` for independent unit testability and separation of concerns. The function returns a
  `list[ReviewCommentInfo]` with `is_suppressed=True`.

## Problem Statement

`dispatch_repair` currently builds repair prompts only from API-visible review comments, so Copilot feedback
that is suppressed due to low confidence is omitted from the generated `@copilot` comment. The implementation
needs to recover those suppressed findings from the review body HTML (which embeds them in a `<details>` block) and pass them through the
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
suppressed comments from the review body HTML `<details>` block, which is the
reliable source for GitHub's low-confidence suppressed feedback:

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
that contains both REST-visible inline comments and suppressed feedback in the review body HTML,
running repair dispatch comment generation, and verifying the output includes
both types of comments with the suppressed label.

**Acceptance Scenarios**:

1. **Given** a Copilot review with regular inline comments and a "suppressed due to low confidence" details block in the review body,
   **When** repair dispatch builds the `@copilot` comment, **Then** both regular and suppressed comments are included.
2. **Given** a suppressed comment with a file path and body text parsed from the review body, **When** it is rendered in the repair dispatch comment, **Then** the entry identifies the affected file
   and labels the feedback as suppressed.

### User Story 2 - Handle Suppressed-Only Feedback (Priority: P1)

As a maintainer reviewing a PR where Copilot only emitted suppressed feedback, I
need repair dispatch to still include that feedback so no review finding is
silently lost.

**Why this priority**: A suppressed-only review is the highest-risk failure mode because dispatch would otherwise provide no review context at all despite Copilot having findings.

**Independent Test**: Can be tested with a review fixture that has no
REST-visible inline comments and only suppressed feedback in the review body, then verifying repair
dispatch still emits an `@copilot` comment containing each suppressed entry and
its file context.

**Acceptance Scenarios**:

1. **Given** a Copilot review whose actionable feedback appears only in the suppressed-comments block of the review body,
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
  but the supplemental suppressed-comment source (review body) is unavailable or malformed?
  Repair dispatch MUST preserve regular comments and fail softly (log a warning, continue dispatch)
  without blocking dispatch.
- How does the system handle suppressed comments that do not include a parseable
  file path? The repair comment MUST still include the feedback with an
  explicit `(unknown file)` marker rather than dropping it silently.
- What happens when the same feedback appears in both the REST comments and the
  supplemental suppressed-comment source? The system MUST deduplicate
  according to FR-004 (exact match after normalization) while preserving the non-suppressed rendering when
  available.
- What happens when the review body `<details>` block exists but is empty (contains no entries)?
  The system MUST treat this as zero suppressed comments and proceed normally with only REST-sourced comments.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST include suppressed Copilot review comments (parsed from the review body HTML `<details>` block) in repair dispatch context in addition to regular inline review comments.

- **FR-002**: The system MUST extract the affected file path and comment body from each suppressed entry in the review body HTML.
  When no parseable file path is found, the system MUST use an `(unknown file)` marker.

- **FR-003**: The system MUST clearly label suppressed comments as suppressed (via `is_suppressed=True` on `ReviewCommentInfo`) when rendering them in the repair dispatch comment.

- **FR-004**: The system MUST avoid duplicating the same review feedback when a
  comment is available from more than one source. Two entries are duplicates only
  when their file paths match after trimming whitespace and removing one leading
  `/`, and their comment bodies match after normalizing CRLF to LF and trimming
  surrounding whitespace; when one duplicate is non-suppressed, that entry MUST
  be preserved for rendering.

- **FR-005**: The system MUST preserve existing repair dispatch behavior for reviews that contain no suppressed comments (regular inline feedback remains unchanged, no synthetic suppressed entries).

- **FR-006**: The system MUST fetch the review body via `GET /repos/{owner}/{repo}/pulls/{pr_number}/reviews/{review_id}` when `review_id > 0` to obtain the suppressed-comments `<details>` block.

- **FR-007**: The system MUST implement suppressed-comment parsing as a standalone, independently-testable utility function (e.g., `_parse_suppressed_from_review_body`) that returns
  `list[ReviewCommentInfo]` with `is_suppressed=True` for each extracted entry.

- **FR-008**: The system MUST fail softly when the review-body fetch or
  suppressed-comment parsing fails (missing/malformed `<details>`): log a warning
  and continue dispatch using only REST-sourced comments.

### Non-Functional Requirements

- **NFR-001**: System MUST complete all operations (including the additional review-body fetch) within 120 seconds under normal conditions.

- **NFR-002**: System MUST maintain backward compatibility with existing interfaces and contracts — no changes to `ReviewCommentInfo` dataclass fields, `_build_repair_comment` signature,
  or `dispatch_repair` method signature.

## Success Criteria

### Measurable Outcomes

- **SC-001**: For a representative Copilot review containing both regular and suppressed comments, the generated repair dispatch comment includes every regular comment and every suppressed comment
  parsed from the review body.

- **SC-002**: For a Copilot review containing only suppressed comments (empty REST comments list, non-empty review body `<details>` block), repair dispatch still produces an `@copilot` comment
  containing those suppressed comments.

- **SC-003**: For reviews without suppressed comments (no `<details>` block in review body), the repair dispatch comment remains unchanged from the current regular-inline-comment behavior.

- **SC-004**: The standalone `_parse_suppressed_from_review_body` function has 100% branch coverage with unit tests covering:
  - valid entries with file paths
  - entries without file paths (`(unknown file)` marker)
  - empty `<details>` block
  - malformed HTML
  - absence of the `<details>` block entirely

---
*Generated by Copilot SDK (claude-opus-4.6)*
