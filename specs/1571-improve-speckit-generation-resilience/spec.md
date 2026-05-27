# Feature Specification: Improve SpecKit Generation Resilience

**Feature Branch**: `speckit/1571/phase-1-specify`
**Created**: 2026-05-26
**Status**: Draft
**Input**: User description: "Improve SpecKit generation resilience to reduce frequent structural validation failures"
**Source Issue**: #1571 (<https://github.com/ayaiayorg/agentic-devtools/issues/1571>)

## Clarifications

### Session 2026-05-27

- Q: Where does the mandatory skeleton injection (FR-001) apply — only to the Phase 1 (specify) LLM prompt, or also to retry prompts in the clarify phase? → A: The skeleton injection applies
  exclusively to the Phase 1 (specify) prompt template. The clarify phase already has its own retry logic in `clarify-retry.sh` with structured feedback. FR-001 targets the initial generation prompt
  to ensure the LLM fills in a pre-structured document rather than generating headings from scratch.
- Q: The spec says "3 retries" for the fallback (FR-003/US3), but the existing `SPECIFY_MAX_RETRIES=3` in `spec-validation.sh` represents a cap of 3 total validation-consuming attempts. Which
  semantics does this feature follow? → A: The existing `SPECIFY_MAX_RETRIES=3` semantics are preserved — this means up to 3 total validation-consuming attempts. The fallback activates only after
  all 3 attempts have been exhausted. This is consistent with the existing variable name and behavior in
  `spec-validation.sh`.
- Q: FR-009 requires re-validation after phases that modify the spec. Given the pipeline is specify → clarify → checklist → plan → tasks → analyze, which specific phases trigger re-validation of the
  spec structural integrity? → A: Re-validation runs after the specify phase (primary) and after the clarify phase (which modifies spec.md). The checklist, plan, tasks, and analyze phases produce
  separate artifacts and do not modify spec.md, so they do not trigger spec structural re-validation. This aligns with the existing `generate-spec-from-issue.sh` architecture.
- Q: For the dynamic threshold adaptation (FR-004), should the reduction apply only to `MIN_SPEC_BYTES` or also to `MIN_FUNCTIONAL_REQUIREMENTS` and `MIN_USER_STORIES`? The spec says "reduced
  proportionally while maintaining minimum counts for requirements and user stories" which seems contradictory with the acceptance scenario mentioning "still requiring all mandatory sections and
  minimum requirement counts." → A: The reduction applies ONLY to `MIN_SPEC_BYTES`. The `MIN_FUNCTIONAL_REQUIREMENTS` (5) and `MIN_USER_STORIES` (3) thresholds remain fixed regardless of issue
  complexity. This ensures structural completeness while allowing shorter prose for simple issues.
- Q: NFR-002 requires idempotent retries producing "structurally equivalent output." Does this mean byte-for-byte deterministic output, or that repeated runs on the same input always produce output
  that passes the same structural validation checks (sections present, requirement counts met) even if prose content varies? → A: Structural equivalence means that repeated runs on the same input must
  always pass the same structural validation checks — all mandatory sections present, requirement counts within the same range (±1), and bullet percentage below threshold. Byte-for-byte determinism is
  NOT required and is not achievable with LLM-based generation. The idempotency guarantee is at the structural contract level, not the content level.

## Problem Statement

The SpecKit specification generation workflow suffers from frequent structural validation failures that block pull requests and reduce developer productivity. When the LLM-based generation produces
output that does not meet the structural contract — missing mandatory sections, insufficient content length, too few requirements or user stories, or an over-reliance on bullet-point summaries — the
validation pipeline rejects the spec and the entire workflow must be retried or manually intervened upon.

These failures are not rare edge cases. They occur regularly across a range of input issues, from detailed feature requests to minimal stub issues. The root causes are multifaceted: the LLM prompt
does not sufficiently enforce the structural contract, retry logic does not adaptively enrich the prompt based on specific failure reasons, there is no deterministic fallback when all retries are
exhausted, and the validation thresholds are static regardless of issue complexity.

The downstream impact is significant. CI pipelines fail, PRs are blocked waiting for valid specs, and developers lose confidence in the automated specification workflow. A resilient generation
pipeline would ensure that structurally valid specs are produced on the first attempt in the vast majority of cases, with intelligent retries and fallbacks covering the remaining scenarios.

## User Scenarios & Testing

### User Story 1 - Reliable First-Attempt Spec Generation (Priority: P1)

As a developer triggering SpecKit generation on a well-described GitHub issue, I expect the system to produce a structurally valid specification on the first attempt without manual intervention. The
generated spec should contain all mandatory sections populated with meaningful content derived from the issue description, meeting minimum length and requirement count thresholds.

**Why this priority**: This is the primary happy path. If first-attempt generation succeeds reliably, all downstream retry and fallback mechanisms become rarely needed. Fixing this addresses the
majority of current failures and directly unblocks PRs.

**Mapped Functional Requirements**: FR-001, FR-007, FR-008

**Independent Test**: Trigger spec generation on 20 representative issues of varying detail levels. Verify that at least 18 of 20 produce a structurally valid spec on the first attempt without any
retry or fallback activation.

**Acceptance Scenarios**:

1. **Given** a GitHub issue with a detailed feature description containing purpose, implementation suggestions, and validation criteria, **When** the SpecKit generation workflow is triggered, **Then**
   the output passes all structural validation checks on the first attempt including minimum length, all mandatory sections present, at least 5 requirements, at least 3 user stories, and bullet
   percentage below 80%.

2. **Given** a GitHub issue with moderate detail (title, 2-3 paragraph description, no implementation suggestions), **When** the SpecKit generation workflow is triggered, **Then** the output still
   passes structural validation on the first attempt because the LLM prompt includes a mandatory skeleton that ensures all required sections are populated with synthesized content.

3. **Given** a GitHub issue where the LLM output begins with conversational preamble text before the markdown heading, **When** the sanitizer processes the output, **Then** the preamble is stripped
   cleanly without triggering a false-positive "no proper heading detected" warning, and the resulting spec retains all its content intact.

---

### User Story 2 - Adaptive Retry with Enriched Feedback (Priority: P1)

As a developer whose spec generation failed on the first attempt due to a specific structural deficiency, I expect the retry mechanism to adaptively address the exact failure reasons by enriching the
LLM prompt with targeted guidance, examples, and explicit instructions about what was missing.

**Why this priority**: Even with an improved first-attempt success rate, some generations will still fail. The retry mechanism is the second line of defense and must be intelligent rather than simply
repeating the same prompt. This directly reduces the number of cases that reach the fallback.

**Mapped Functional Requirements**: FR-002, FR-009, FR-010

**Independent Test**: Deliberately craft an issue that produces a spec missing the Requirements section. Verify that the retry prompt includes explicit instructions about the missing section and that
the second attempt produces a valid spec.

**Acceptance Scenarios**:

1. **Given** a first-attempt spec that failed validation because it was missing the "## Requirements" section and had fewer than 5 functional requirements, **When** the retry mechanism activates,
   **Then** the enriched prompt explicitly states which sections were missing, includes a concrete example of a valid Requirements section, and instructs the LLM to ensure at least 5 FR-### entries
   are present.

2. **Given** a first-attempt spec that failed because bullet percentage exceeded 80%, **When** the retry mechanism activates, **Then** the enriched prompt includes specific instructions to use prose
   paragraphs for descriptions, explains the bullet percentage rule, and provides an example of acceptable prose-to-bullet ratio.

3. **Given** a first-attempt spec that failed because it was below the minimum byte threshold (default: 2048 bytes), **When** the retry mechanism activates, **Then** the enriched prompt instructs the
   LLM to expand each
   section with detailed descriptions, elaborated acceptance scenarios, and comprehensive requirement definitions rather than terse summaries.

---

### User Story 3 - Deterministic Fallback on Total Retry Exhaustion (Priority: P2)

As a developer whose spec generation has exhausted all retry attempts without producing a valid spec, I expect the system to write a deterministic minimal skeleton spec that passes structural
validation. This skeleton should contain all mandatory sections with placeholder content derived from the issue title and description, allowing the workflow to proceed while flagging the spec for
manual enrichment.

**Why this priority**: This is the safety net that prevents complete workflow blockage. While it should rarely activate if the first two stories are implemented well, its presence ensures that no PR
is permanently blocked by transient LLM output quality issues.

**Mapped Functional Requirements**: FR-003, FR-011

**Independent Test**: Force all retry attempts to fail (e.g., by using a mock LLM that returns empty output). Verify that the fallback skeleton is written, passes structural validation, and contains
markers indicating it needs manual review.

**Acceptance Scenarios**:

1. **Given** that the spec generation has failed all 3 configured validation attempts (as capped by `SPECIFY_MAX_RETRIES`), **When** the final attempt produces invalid output, **Then** the system
   writes a deterministic
   skeleton spec that includes all mandatory sections (Problem Statement, User Scenarios & Testing, Requirements, Success Criteria) populated with content derived from the issue title and body text.

2. **Given** that the deterministic fallback skeleton has been written, **When** structural validation runs against it, **Then** it passes all checks including minimum length (via expanded template
   prose), minimum requirements count (via placeholder FR entries derived from issue keywords), and bullet percentage (via prose paragraph structure).

3. **Given** that the fallback skeleton was used, **When** the developer reviews the generated spec, **Then** the spec contains a clearly visible banner at the top indicating it was generated via
   fallback and requires manual enrichment, along with specific guidance on which sections need the most attention based on the original validation failures.

---

### User Story 4 - Dynamic Threshold Adaptation for Minimal Issues (Priority: P2)

As a developer triggering spec generation on a minimal stub issue (e.g., a one-line bug report or a brief enhancement request), I expect the validation thresholds to adapt to the input complexity
rather than applying the same minimum byte count that would be appropriate for a detailed feature request.

**Why this priority**: Static thresholds cause impossible-to-satisfy validation for simple issues. Adapting thresholds reduces false failures without compromising quality for complex issues.

**Mapped Functional Requirements**: FR-004

**Independent Test**: Trigger spec generation on a one-sentence issue. Verify that the minimum byte threshold is reduced proportionally and that a well-structured but shorter spec passes validation.

**Acceptance Scenarios**:

1. **Given** an issue with fewer than 200 characters of description, **When** the validation thresholds are computed, **Then** the `MIN_SPEC_BYTES` threshold is reduced by up to 40% from the
   default (from 2048 to a minimum of 1229 bytes), while `MIN_FUNCTIONAL_REQUIREMENTS` (5) and `MIN_USER_STORIES` (3) remain unchanged.

2. **Given** an issue with a comprehensive multi-paragraph description exceeding 2000 characters, **When** the validation thresholds are computed, **Then** the standard `MIN_SPEC_BYTES` threshold
   (2048 bytes)
   applies without reduction.

---

### User Story 5 - Granular Actionable Error Feedback (Priority: P3)

As a developer reviewing a spec generation failure, I expect the error messages to provide specific, actionable guidance about what to fix rather than generic failure descriptions. Each validation
failure reason should include a suggested remediation step.

**Why this priority**: While not directly preventing failures, better error messages reduce time-to-resolution when manual intervention is needed and help developers understand what the system
expects.

**Mapped Functional Requirements**: FR-005

**Independent Test**: Trigger validation on a deliberately malformed spec. Verify that each failure message includes both the specific problem and a concrete suggestion for fixing it.

**Acceptance Scenarios**:

1. **Given** a spec that fails validation due to missing the "## Success Criteria" section, **When** the error report is generated, **Then** the message includes not only "missing Success Criteria"
   but also "Add a '## Success Criteria' section with at least one SC-### entry containing a measurable outcome metric."

2. **Given** a spec that fails validation due to excessive bullet percentage (e.g., 95%), **When** the error report is generated, **Then** the message includes the actual percentage, the maximum
   allowed percentage (80%), and a suggestion such as "Convert bullet lists in Problem Statement and Requirements sections to prose paragraphs with explanatory context."

---

### User Story 6 - Sanitizer Precision Improvement (Priority: P3)

As a developer whose spec generation produces valid content but triggers false-positive sanitizer warnings, I expect the preamble stripping and heading detection logic to be precise enough to avoid
incorrectly modifying valid specs or emitting spurious warnings.

**Why this priority**: False-positive sanitizer triggers cause unnecessary noise in logs and can occasionally corrupt valid output. Improving precision reduces confusion and prevents subtle content
loss.

**Mapped Functional Requirements**: FR-006

**Independent Test**: Feed the sanitizer 10 valid specs that begin with proper markdown headings (some with leading whitespace, some with BOM markers). Verify that none trigger the "no proper heading
detected" fallback.

**Acceptance Scenarios**:

1. **Given** an LLM output that begins with "# Feature Specification:" preceded only by whitespace or a Unicode BOM, **When** the sanitizer processes it, **Then** no fallback heading is prepended and
   no warning is emitted.

2. **Given** an LLM output that begins with a brief acknowledgment line like "Here is the specification:" followed by a valid markdown heading on the next line, **When** the sanitizer processes it,
   **Then** only the acknowledgment line is stripped and the heading is preserved intact without triggering a "default prepended" message.

---

### Edge Cases

The following boundary conditions must be handled gracefully by the resilient generation pipeline:

1. **Empty or near-empty issue body**: When the issue has only a title and no description body, the system must still generate a structurally valid spec by synthesizing content from the title alone,
   applying reduced validation thresholds (40% reduction to `MIN_SPEC_BYTES` only), and clearly marking synthesized sections.

2. **Malformed LLM output with partial sections**: When the LLM produces output with some mandatory sections present but others missing or malformed (e.g., a "Requirements" heading with no FR-###
   entries beneath it), the retry feedback must identify both the structural absence and the content absence separately.

3. **Concurrent spec generation for the same issue**: When multiple CI runs trigger spec generation simultaneously for the same issue, the system must handle file write conflicts gracefully, either
   through file locking or last-writer-wins semantics with appropriate logging.

4. **LLM output exceeding maximum length**: When the LLM produces output that is extremely long (exceeding reasonable spec size), the system should not truncate it in a way that removes mandatory
   sections from the end of the document.

5. **Non-English or mixed-language issue content**: When the issue body contains non-English text or code snippets with special characters, the byte-count validation must handle multi-byte UTF-8
   characters correctly without penalizing internationalized content.

## Requirements

### Functional Requirements

The following functional requirements define the capabilities that the resilient SpecKit generation system must provide. Each requirement is independently verifiable and contributes to the overall
goal of reducing structural validation failures.

- **FR-001**: The system MUST inject a mandatory skeleton containing all required section headings (## Problem Statement, ## User Scenarios & Testing, ## Requirements, ## Success Criteria) into the
  Phase 1 (specify) LLM prompt as a structural template that the LLM fills in rather than generates from scratch. This skeleton injection applies exclusively to the specify phase prompt; the clarify
  phase retains its existing retry logic in `clarify-retry.sh`. This ensures that even minimal LLM output retains the required document structure.

- **FR-002**: The system MUST implement adaptive retry prompt enrichment that analyzes the specific validation failures from the previous attempt and includes targeted remediation instructions in the
  retry prompt. The enrichment must address each distinct failure reason (missing sections, insufficient length, too few requirements, excessive bullets) with specific corrective guidance. This builds
  upon the existing `_build_structured_clarify_feedback` pattern in `clarify-retry.sh`.

- **FR-003**: The system MUST provide a deterministic fallback skeleton generator that activates after all retry attempts are exhausted (after `SPECIFY_MAX_RETRIES` total validation attempts, default
  3 attempts). The fallback skeleton must pass structural validation, derive
  content from the issue title and body, and include a visible banner indicating fallback activation.

- **FR-004**: The system MUST support dynamic validation threshold adaptation based on input issue complexity. For issues with description length below a configurable threshold (default: 200
  characters), the `MIN_SPEC_BYTES` threshold must be reduced by up to 40% while `MIN_FUNCTIONAL_REQUIREMENTS` (5) and `MIN_USER_STORIES` (3) remain fixed regardless of issue complexity.

- **FR-005**: The system MUST emit structured, actionable error feedback for each validation failure that includes the specific failure reason, the actual vs. expected values, and a concrete
  remediation suggestion. This feedback must be consumable both by the retry mechanism (machine-readable) and by developers reviewing logs (human-readable).

- **FR-006**: The system MUST improve the preamble sanitizer to handle common LLM output patterns (leading whitespace, BOM markers, brief acknowledgment lines) without triggering false-positive
  heading detection failures. The sanitizer must strip non-content preamble while preserving valid markdown structure.

- **FR-007**: The system MUST track and report spec generation success metrics including first-attempt success rate, average retry count, fallback activation rate, and most common failure reasons.
  These metrics must be available in CI logs for monitoring.

- **FR-008**: The system MUST validate that the bullet-to-prose ratio in generated specs does not exceed 80% of total content lines (controlled by `MAX_BULLET_LINE_PCT`). When the ratio exceeds this
  threshold during generation, the retry
  prompt must include explicit instructions to convert bullet lists into prose paragraphs with explanatory context.

- **FR-009**: The system MUST preserve heading and requirement counts through the specify and clarify phases by re-validating structural integrity after each phase that modifies `spec.md`. The
  checklist, plan, tasks, and analyze phases produce separate artifacts and do not require spec re-validation.

- **FR-010**: The system MUST support an explicit example injection mechanism in retry prompts, where on the second or subsequent retry, a reference example of a valid passing spec structure is
  included in the prompt to guide the LLM toward correct output format.

- **FR-011**: The system MUST ensure that the deterministic fallback skeleton generates at least 5 FR-### requirement entries and at least 3 user story sections, synthesized from keywords and phrases
  extracted from the issue title and description.

### Non-Functional Requirements

The following non-functional requirements define quality attributes and constraints for the resilient generation system.

- **NFR-001**: The total spec generation time including all retries must not exceed 120 seconds for any single issue. Each individual LLM call should complete within 30 seconds, and retry delays
  should use exponential backoff starting at 2 seconds (2s, 4s, 8s for retries 1, 2, 3 respectively).

- **NFR-002**: The retry mechanism must be structurally idempotent — running the same generation multiple times on the same issue input must produce structurally equivalent output (all mandatory
  sections present,
  requirement counts within ±1 of each other, bullet percentage below threshold) even if prose content varies between runs. Byte-for-byte determinism is not required.

- **NFR-003**: All error messages and log output must follow the existing logging conventions established in the speckit-trigger scripts, using consistent formatting (emoji prefixes for
  warnings/errors, structured JSON for machine-readable output).

- **NFR-004**: The fallback skeleton generator must execute in under 1 second without any network calls, using only the locally available issue data and template files.

- **NFR-005**: The dynamic threshold adaptation must be configurable via environment variables (e.g., `AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR`, defaulting to `0.6` representing 60% of original threshold
  as the floor) to allow per-repository tuning without code changes.

- **NFR-006**: The solution must maintain backward compatibility with existing `spec-validation.sh` contract — all existing validation checks must continue to work identically for specs generated by
  other means (manual authoring, external tools). The existing configurable thresholds (`MIN_SPEC_BYTES`, `MIN_FUNCTIONAL_REQUIREMENTS`, `MIN_USER_STORIES`, `MAX_BULLET_LINE_PCT`,
  `SPECIFY_MAX_RETRIES`) retain their current override semantics.

## Success Criteria

The following measurable outcomes define when this feature is considered successfully implemented. Each criterion includes specific numeric targets that can be verified through automated testing and
CI monitoring.

- **SC-001**: The first-attempt spec generation success rate (passing structural validation without any retry) must reach at least 90% across a representative sample of 50+ issues with varying
  complexity levels, measured over a 2-week period after deployment.

- **SC-002**: Zero pull requests are blocked for more than 10 minutes due to spec generation failures, measured by the time between spec generation trigger and either successful validation or fallback
  activation completing.

- **SC-003**: The sanitizer false-positive rate for heading detection must be below 5%, measured as the number of valid specs that trigger the "no proper heading detected" fallback divided by total
  specs processed.

- **SC-004**: The average number of retry attempts before successful validation must be 1.2 or fewer (meaning most specs pass on first attempt and those that retry typically succeed on the first
  retry).

- **SC-005**: The deterministic fallback activation rate must be below 3% of all spec generation attempts, indicating that the improved first-attempt generation and adaptive retries handle the vast
  majority of cases.

- **SC-006**: All generated specs (including fallback skeletons) must pass the complete structural validation suite including minimum length check, mandatory section presence, minimum 5 requirements,
  minimum 3 user stories, and bullet percentage below 80%.

- **SC-007**: Developer satisfaction with error feedback clarity must improve, measured by a 50% reduction in support requests or manual interventions related to "unclear spec generation failure"
  within 4 weeks of deployment.

---
*Generated by Copilot SDK (claude-opus-4.6)*
