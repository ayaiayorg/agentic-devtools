# Feature Specification: Structural Validation and Retry for Phase 1 (Specify)

**Feature Branch**: `speckit/1505/phase-2-clarify`
**Created**: 2026-05-21
**Status**: Draft
**Input**: User description: "Introduce structural validation and retry mechanism to Phase 1 (specify) to block underspecified specs"
**Source Issue**: #1505 (<https://github.com/ayaiayorg/agentic-devtools/issues/1505>)

## Clarifications

### Session 2026-05-21

- Q: Where should the new `validate_spec_quality` function be defined — inline in `generate-spec-from-issue.sh` or in a separate library file (e.g., `lib/spec-validation.sh`)? → A: In a new library
  file `lib/spec-validation.sh` that is sourced by both `generate-spec-from-issue.sh` (Phase 1) and `lib/clarify-retry.sh` (Phase 2). This follows the existing pattern where `lib/clarify-retry.sh` and
  `lib/retry.sh` are separate sourceable libraries with sourcing guards.

- Q: What exit code should Phase 1 use when all retry attempts are exhausted — exit code 1 (matching the existing `{ echo "Error: Specify phase failed after retries" >&2; exit 1; }` pattern) or a
  distinct code? → A: Exit code 1, consistent with the existing Phase 1 error handling in
  `generate-spec-from-issue.sh`'s retry-exhausted error handler. The return-code-2-for-operational-failure convention applies within the retry loop (to distinguish
  retriable operational failures from validation failures), but the final pipeline exit remains code 1.

- Q: Should the retry re-prompt include the full original specify prompt plus structured feedback appended, or only the structured feedback with the previous (failed) output? → A: The retry re-prompt
  should include the full original specify prompt, the failed output (so the LLM sees what it produced), and the structured feedback appended at the end — matching the proven pattern from
  `_build_structured_clarify_feedback` in `lib/clarify-retry.sh` where both context and categorized failures are provided.

- Q: How should the user story heading pattern check handle variations like `### User Story: <title>` or `### Scenario N` that don't match `### User Story N` exactly? → A: The validator should match
  headings containing `### User Story` as a prefix (case-insensitive), accepting patterns like `### User Story 1`, `### User Story: Title`, and `### User Story N — Description`. The matcher
  should be implemented as truly case-insensitive (for example, `grep -iE '^### user story'`). Other heading styles (e.g., `### Scenario N`) are not counted as user stories.

- Q: Should the `MIN_SPEC_BYTES=2048` threshold measure the raw LLM output or the final post-processed content (after `strip_llm_preamble` and `ensure_heading_start`)? → A: The threshold measures the
  post-processed content, consistent with FR-012 which states "Validation MUST run AFTER `strip_llm_preamble` and `ensure_heading_start` processing." This matches what would actually be written to
  disk, avoiding false passes from verbose LLM preambles inflating byte count.

## Problem Statement

Phase 1 (specify) of the SpecKit pipeline currently writes LLM-generated `spec.md` output directly to disk without any structural quality validation. This allows underspecified, summary-only, or
bullet-point-only specs to pass through and enter mainline. Downstream phases (clarify, plan, tasks, implement) then operate on insufficient input, producing low-quality artifacts or failing entirely.

The clarify phase (Phase 2) already has a robust multi-layer validation and retry mechanism (`clarify-retry.sh`, `validate_structural_integrity`, structured feedback re-prompting). Phase 1 lacks an
equivalent gate, meaning the very first and most critical artifact — `spec.md` — has no quality floor enforcement at the point of generation.

Evidence: PR #1504 produced a shallow, bullet-summary spec that passed Phase 1 unchallenged. Well-formed specs (e.g., `specs/1195-*`, `specs/1198-*`) demonstrate that the LLM is capable of producing
full specs when given proper guardrails and retry opportunities.

## Scope

**In scope:**

- Structural validation of Phase 1 `spec.md` output before writing to disk
- Minimum content thresholds (size, section count, requirement count, user story count)
- Detection and rejection of summary-only/bullet-point outputs
- Measurability checks on Success Criteria entries
- Automatic retry with structured feedback when validation fails
- Bounded retry limit to prevent infinite loops
- Extraction of shared validation helpers into `lib/spec-validation.sh`, usable by both Phase 1 and Phase 2

**Out of scope:**

- Semantic/quality assessment of spec content (e.g., "are the requirements good?")
- Changes to the LLM prompt content for Phase 1 (beyond retry feedback injection)
- Changes to Phase 2 (clarify) validation logic (existing logic is preserved, shared helpers are extracted)
- Changes to downstream phases (plan, tasks, implement)

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Spec Validation Blocks Underspecified Output (Priority: P1)

As a developer triggering Phase 1 (specify) via the SpecKit pipeline, I want the system to automatically validate the generated `spec.md` against structural quality rules before writing it to disk, so
that no underspecified or summary-only spec ever makes it out of Phase 1.

**Why this priority**: This is the core behavior — the quality gate itself. Without this, all other stories are moot. It directly addresses the root cause: underspecified specs entering mainline.

**Independent Test**: Can be fully tested by feeding the validation function a known-bad spec (e.g., a bullet-point summary with only 2 requirements and no user stories) and verifying it returns
failure with actionable feedback.

**Acceptance Scenarios**:

1. **Given** Phase 1 generates a `spec.md` with fewer than 5 functional requirements, **When** the output is validated, **Then** validation fails with feedback specifying the minimum FR count
   required.

2. **Given** Phase 1 generates a `spec.md` missing the `## Success Criteria` section, **When** the output is validated, **Then** validation fails listing the missing mandatory section.

3. **Given** Phase 1 generates a `spec.md` that is under 2048 bytes in size (after `strip_llm_preamble` and `ensure_heading_start` post-processing), **When** the output is validated,
   **Then** validation fails with feedback indicating the spec is below the minimum content threshold.

4. **Given** Phase 1 generates a `spec.md` with only 1 user story, **When** the output is validated, **Then** validation fails requiring at least 3 user stories with acceptance scenarios.

5. **Given** Phase 1 generates a `spec.md` with all mandatory sections, 5+ FRs, 3+ user stories, measurable success criteria, and >2KB content, **When** the output is validated, **Then** validation
   passes and the spec is written to disk.

6. **Given** Phase 1 generates a `spec.md` where success criteria contain no numbers, percentages, or measurable targets, **When** the output is validated, **Then** validation fails with feedback
   requiring measurable outcomes.

---

### User Story 2 — Automatic Retry with Structured Feedback (Priority: P1)

As a developer running the SpecKit pipeline, I want the system to automatically re-prompt the LLM with structured feedback when Phase 1 validation fails, so that the LLM gets a chance to produce a
conforming spec without manual intervention.

**Why this priority**: Validation without retry makes the pipeline brittle — it would simply fail on first attempt. The retry mechanism is what makes the validation gate practical and self-healing,
matching the proven pattern from Phase 2 clarify.

**Independent Test**: Can be tested by mocking `call_llm` to return an underspecified output on the first call and a valid spec on the second call, then verifying the retry logic fires exactly once
with the correct structured feedback.

**Acceptance Scenarios**:

1. **Given** Phase 1 validation fails on the initial LLM output, **When** the retry mechanism fires, **Then** the LLM receives a re-prompt containing the full original specify prompt, the failed
   output, and categorized feedback (MISSING_SECTIONS,
   INSUFFICIENT_REQUIREMENTS, INSUFFICIENT_USER_STORIES, BELOW_SIZE_THRESHOLD, NON_MEASURABLE_CRITERIA) describing exactly what failed.

2. **Given** the retry re-prompt produces a valid spec on the second attempt, **When** validation passes, **Then** the valid spec is written to disk and no further retries occur.

3. **Given** the retry limit (3 attempts) is exhausted without producing a valid spec, **When** all retries fail, **Then** the pipeline exits with exit code 1 and an actionable error
   message listing all validation failures from the final attempt printed to stderr.

4. **Given** a retry attempt encounters an operational failure (e.g., LLM API timeout), **When** the error is detected, **Then** it does NOT count against the retry limit
   (return code 2 within the retry loop signals operational failure, consistent with Phase 2 behavior).

---

### User Story 3 — Summary-Only and Bullet-Point Detection (Priority: P2)

As a pipeline maintainer, I want the validation to detect and reject specs that consist primarily of bullet points or one-line stubs without substantive paragraph content, so that shallow LLM outputs
are caught early.

**Why this priority**: This addresses a specific failure mode observed in PR #1504 where the LLM produced a structurally-valid-looking spec that was actually just a reformatted version of the issue
body. It builds on the core validation (US1) with a more nuanced heuristic.

**Independent Test**: Can be tested by crafting a spec that has all mandatory section headings but where each section contains only 1-2 bullet points and no prose paragraphs, then verifying the
validator rejects it.

**Acceptance Scenarios**:

1. **Given** a spec where more than 80% of non-heading lines are bullet points (lines starting with `-` or `*`), **When** validated, **Then** validation fails with feedback "BULLET_SUMMARY_DETECTED:
   spec appears to be a summary-only output; expand into full prose sections with acceptance scenarios."

2. **Given** a spec where at least 3 sections contain substantive paragraph content (≥2 consecutive non-bullet, non-heading lines), **When** validated, **Then** the bullet-point check passes.

3. **Given** a spec where the User Scenarios section contains user story headings but no Given/When/Then acceptance scenarios, **When** validated, **Then** validation fails with feedback requiring
   acceptance scenarios.

---

### User Story 4 — Shared Validation Helpers (Priority: P2)

As a SpecKit maintainer, I want the section-counting and structural validation logic to be extracted into a shared library file (`lib/spec-validation.sh`) usable by both Phase 1 and Phase 2, so that
validation rules are defined once and enforced consistently across phases.

**Why this priority**: Reduces duplication and ensures both phases enforce the same structural contract. The existing `validate_structural_integrity` function is designed for Phase 2 (comparing
candidate to original). Phase 1 needs a related but distinct validation (checking absolute thresholds on a fresh spec with no "original" to compare against).

**Independent Test**: Can be tested by invoking the shared helpers from both the Phase 1 validation function and the existing Phase 2 flow, verifying both produce consistent results for the same
input.

**Acceptance Scenarios**:

1. **Given** a new shared helper `validate_spec_quality` is created in `lib/spec-validation.sh`, **When** called with a spec file path, **Then** it checks all Phase 1 quality rules (mandatory
   sections, minimum counts, size threshold, measurability, bullet-summary detection) and returns structured failure reasons on stdout with return code 1 on failure and 0 on success.

2. **Given** the existing `validate_structural_integrity` function in Phase 2, **When** Phase 1 shared helpers are extracted, **Then** Phase 2 continues to work identically (no behavioral change to
   clarify retry logic).

3. **Given** the shared helpers are defined in `lib/spec-validation.sh`, **When** both `run_specify_phase` (via `generate-spec-from-issue.sh`) and `run_clarify_phase` (via `lib/clarify-retry.sh`)
   source it, **Then** no code duplication exists for section extraction and counting logic.

---

### User Story 5 — Configurable Thresholds (Priority: P3)

As a SpecKit maintainer, I want validation thresholds (minimum FR count, minimum user story count, minimum byte size, retry limit) to be defined as named constants at the top of `lib/spec-validation.sh`,
so that they can be tuned without modifying validation logic.

**Why this priority**: Threshold values may need adjustment as the LLM improves or as spec expectations evolve. Centralizing them makes tuning straightforward and auditable.

**Independent Test**: Can be tested by overriding threshold constants in a test script and verifying the validator uses the overridden values.

**Acceptance Scenarios**:

1. **Given** threshold constants are defined (e.g., `MIN_FUNCTIONAL_REQUIREMENTS=5`, `MIN_USER_STORIES=3`, `MIN_SPEC_BYTES=2048`, `SPECIFY_MAX_RETRIES=3`), **When** a spec has exactly 5 FRs, **Then**
   it passes the FR check.

2. **Given** a test overrides `MIN_FUNCTIONAL_REQUIREMENTS=10`, **When** a spec with 7 FRs is validated, **Then** validation fails citing the 10-FR minimum.

---

### Edge Cases

- **What happens when the LLM produces a valid spec on the first attempt?** Validation passes immediately, no retry occurs, and the spec is written to disk with zero additional latency beyond the
  validation check itself.

- **What happens when the LLM produces an empty or whitespace-only response?** The existing empty-content check in Phase 1's post-generation sanity check block in `generate-spec-from-issue.sh` fires
  before validation, failing the phase immediately with the existing error message.

- **What happens when the spec has the right structure but sections contain placeholder text (e.g., "[TODO]")?** Placeholder detection is out of scope for this feature; the structural validator checks
  counts and measurability, not semantic completeness.

- **How does the system handle a spec that passes structural validation but has fewer than the minimum acceptance scenarios per user story?** The validator checks for the presence of Given/When/Then
  patterns within the User Scenarios section. If fewer than 3 user stories (headings matched with a case-insensitive `### user story` prefix check) have at least one acceptance scenario each,
  validation fails.

- **What happens if `strip_llm_preamble` removes content that causes the spec to drop below thresholds?** Validation runs AFTER `strip_llm_preamble` and `ensure_heading_start`, so the validated content
  is exactly what would be written to disk.

- **What happens if the validation library file `lib/spec-validation.sh` is missing when sourced?** The sourcing script (`generate-spec-from-issue.sh`) uses:

  ```bash
  source "$SCRIPT_DIR/lib/spec-validation.sh"
  ```

  This fails with `set -euo pipefail`, causing an immediate exit with a clear file-not-found error. This is acceptable — the library is a hard dependency.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST validate Phase 1 `spec.md` output against structural quality rules BEFORE writing the file to disk.

- **FR-002**: The system MUST check for all mandatory sections: `## Problem Statement`, `## User Scenarios & Testing`, `## Requirements`, `## Success Criteria`.

- **FR-003**: The system MUST require a minimum of 5 functional requirements (lines matching `**FR-###**` pattern) in the generated spec.

- **FR-004**: The system MUST require a minimum of 3 user stories with acceptance scenarios (sections matching headings with prefix `### User Story` (case-insensitive), each containing at least one
  `**Given**`/`**When**`/`**Then**`
  sequence).

- **FR-005**: The system MUST require success criteria entries to be measurable — at least 50% of `**SC-###**` entries MUST contain a number, percentage, or quantitative target.

- **FR-006**: The system MUST reject specs below a minimum content threshold of 2048 bytes (measured on the post-processed content after `strip_llm_preamble` and `ensure_heading_start`).

- **FR-007**: The system MUST detect and reject summary-only/bullet-point specs where more than 80% of content lines (excluding headings and blank lines) are bullet points.

- **FR-008**: The system MUST automatically retry with structured feedback when validation fails, up to a maximum of 3 retry attempts.

- **FR-009**: The structured feedback provided to the LLM on retry MUST include the full original specify prompt, the failed output, and categorized failure information (e.g., MISSING_SECTIONS,
  INSUFFICIENT_REQUIREMENTS, INSUFFICIENT_USER_STORIES, BELOW_SIZE_THRESHOLD,
  NON_MEASURABLE_CRITERIA, BULLET_SUMMARY_DETECTED) with specific counts and thresholds.

- **FR-010**: Operational failures (LLM API errors, timeouts) MUST NOT count against the retry limit. Within the retry loop, return code 2 signals an operational failure (consistent with the Phase 2
  clarify retry contract).

- **FR-011**: When all retries are exhausted, the system MUST exit with exit code 1 and print all validation failures from the final attempt to stderr.

- **FR-012**: Validation MUST run AFTER `strip_llm_preamble` and `ensure_heading_start` processing, so the validated content matches what would be written to disk.

- **FR-013**: Shared helper functions (section extraction, requirement counting, user story counting, bullet-point ratio calculation) MUST be extracted into `lib/spec-validation.sh`, a library file
  sourceable by both Phase 1 and Phase 2 code paths, following the existing sourcing-guard pattern used by `lib/clarify-retry.sh`.

- **FR-014**: The existing Phase 2 (clarify) behavior MUST remain unchanged — shared helper extraction MUST NOT alter any existing test outcomes.

### Non-Functional Requirements

- **NFR-001**: The structural validation check MUST complete in under 1 second for a typical spec (5–25KB), adding negligible latency to the Phase 1 pipeline step.
  Measurement:

  ```bash
  SCRIPT_DIR=".github/scripts/speckit-trigger"
  source "$SCRIPT_DIR/lib/spec-validation.sh" && time validate_spec_quality /path/to/spec.md
  ```

  returns in <1s on a standard GitHub Actions runner.

- **NFR-002**: All validation failure messages MUST be human-readable and actionable, clearly stating what failed, what the threshold is, and what the actual value was (e.g.,
  "INSUFFICIENT_REQUIREMENTS: found 3 FR entries, minimum required is 5").

- **NFR-003**: The retry mechanism MUST produce deterministic outcomes — given the same LLM output, the validation result MUST be identical across runs (no randomness, timestamp-dependent logic, or
  floating-point comparisons in validation).

- **NFR-004**: Threshold constants MUST be defined as named variables at the top of `lib/spec-validation.sh`, not as inline magic numbers.

- **NFR-005**: All new shell functions MUST include a function header comment documenting parameters, return codes, and stdout/stderr behavior, consistent with existing conventions in
  `generate-spec-from-issue.sh`.

- **NFR-006**: New validation logic MUST be covered by shell tests in a dedicated test file (`test_spec_validation.sh`), with at least 10 test cases that explicitly cover all documented validation
  branches and failure modes.

### Key Entities

- **Spec Quality Validator**: A shell function (`validate_spec_quality`) defined in `lib/spec-validation.sh` that performs absolute-threshold validation on a freshly generated `spec.md`. Unlike
  `validate_structural_integrity` (which compares candidate to original), this validator checks minimum quality standards for a new spec with no prior version. Returns 0 on success, 1 on validation
  failure (with structured feedback on stdout).

- **Structured Retry Feedback**: A categorized, machine-readable feedback string generated when validation fails. Includes category labels, actual vs. expected counts, and remediation instructions.
  Fed directly into the LLM re-prompt alongside the full original prompt and failed output.

- **Retry Budget**: A bounded counter (default: 3) tracking validation-failure retries. Operational failures (return code 2 from `call_llm`) do not decrement the budget. Exhaustion triggers pipeline
  exit with code 1.

- **Quality Thresholds**: Named constants defined at the top of `lib/spec-validation.sh` controlling validation sensitivity: `MIN_FUNCTIONAL_REQUIREMENTS` (5), `MIN_USER_STORIES` (3), `MIN_SPEC_BYTES`
  (2048), `MIN_MEASURABLE_CRITERIA_PCT` (50),
  `MAX_BULLET_LINE_PCT` (80), `SPECIFY_MAX_RETRIES` (3).

- **Validation Library** (`lib/spec-validation.sh`): A sourceable shell library file following the existing pattern of `lib/clarify-retry.sh` — includes a sourcing guard
  (`_SPEC_VALIDATION_LIB_LOADED`), defines all validation functions and threshold constants, and has no top-level side effects.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of specs generated by Phase 1 after this change contain all 4 mandatory sections, at least 5 FRs, and at least 3 user stories with acceptance scenarios.

- **SC-002**: 0% of specs below 2048 bytes or consisting primarily of bullet-point summaries pass Phase 1 validation.

- **SC-003**: The retry mechanism successfully recovers (produces a valid spec) in at least 80% of cases where the first LLM attempt fails validation, based on pipeline run data over the first 20
  feature specs generated after deployment.

- **SC-004**: Phase 1 pipeline step latency increases by no more than 2 seconds in the non-retry case (validation overhead only) and no more than 90 seconds in the worst case (3 retries with full LLM
  calls).

- **SC-005**: All existing `test_clarify_retry.sh` and `test_content_preservation.sh` tests continue to pass without modification after shared helper extraction.

- **SC-006**: The dedicated shell test file (`test_spec_validation.sh`) contains at least 10 test cases that explicitly cover all documented validation branches and failure modes.

---

*Generated by Copilot SDK (claude-opus-4.6)*
