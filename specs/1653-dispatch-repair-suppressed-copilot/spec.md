# Feature Specification: dispatch_repair: Suppressed Copilot review comments not included in repair dispatch comment

> ⚠️ **FALLBACK SKELETON** — This specification was generated via deterministic fallback after all LLM retry attempts were exhausted. It requires manual enrichment. Review each section and replace
> placeholder content with detailed, issue-specific information.

**Source Issue**: #1653 (<https://github.com/ayaiayorg/agentic-devtools/issues/1653>)

## Problem Statement

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

1. Open a PR where Copilot posts a review with ≥1 suppressed comment (marked *"suppressed due to low confidence"*) alongside regular inline comments
2. Observe that the pipeline dispatches a repair c

The implementation of this feature will improve the overall system reliability and reduce the operational burden on development teams. Without this change, the existing workarounds will continue to
consume developer time and introduce potential for human error.

## User Scenarios & Testing

### User Story 1 - Primary Workflow (Priority: P1)

As a developer working with the system, I expect the dispatch_repair: suppressed copilot review comments not included in repair dispatch comment feature to work correctly on standard inputs without
requiring manual intervention.

**Acceptance Scenarios**:

1. **Given** a standard input meeting all preconditions, **When** the system processes it, **Then** the output meets all quality checks and completes within the expected time bounds.

2. **Given** an input that previously caused failures, **When** processed with the improved logic, **Then** the success rate exceeds 90% over repeated runs.

### User Story 2 - Error Recovery (Priority: P1)

As a developer whose operation encounters a transient failure, I expect the system to recover gracefully and complete the operation without manual intervention.

**Acceptance Scenarios**:

1. **Given** a first attempt that fails due to a transient issue, **When** the retry mechanism activates, **Then** the second attempt succeeds with enriched context.

2. **Given** a specific validation failure reason, **When** retry feedback is generated, **Then** the feedback addresses the exact failure with actionable guidance.

### User Story 3 - Graceful Degradation (Priority: P2)

As a developer whose operation has exhausted all retry attempts, I expect the system to provide a usable fallback output rather than failing completely.

**Acceptance Scenarios**:

1. **Given** all retry attempts have been exhausted, **When** the fallback mechanism activates, **Then** a structurally valid output is produced that allows the workflow to proceed.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST implement absent capability as described in the feature requirements, ensuring correct behavior under normal operating conditions and providing appropriate error handling
  for edge cases.

- **FR-002**: The system MUST implement action capability as described in the feature requirements, ensuring correct behavior under normal operating conditions and providing appropriate error handling
  for edge cases.

- **FR-003**: The system MUST implement actions capability as described in the feature requirements, ensuring correct behavior under normal operating conditions and providing appropriate error
  handling for edge cases.

- **FR-004**: The system MUST implement address capability as described in the feature requirements, ensuring correct behavior under normal operating conditions and providing appropriate error
  handling for edge cases.

- **FR-005**: The system MUST implement affected capability as described in the feature requirements, ensuring correct behavior under normal operating conditions and providing appropriate error
  handling for edge cases.

### Non-Functional Requirements

- **NFR-001**: The implementation must complete all operations within 120 seconds under normal conditions.

- **NFR-002**: The implementation must maintain backward compatibility with existing interfaces and contracts.

## Success Criteria

- **SC-001**: The feature achieves at least 90% success rate on standard inputs measured over a representative sample of 20+ test cases.

- **SC-002**: Zero critical failures occur during the first 2 weeks of deployment, measured by monitoring error rates in CI logs.

- **SC-003**: Average processing time remains under 30 seconds for standard inputs, with worst-case time under 120 seconds including retries.

---
*Generated via fallback skeleton — manual enrichment required*

---
*Generated by Copilot SDK (claude-opus-4.6)*
