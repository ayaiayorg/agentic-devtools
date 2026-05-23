# Spec: Review all files every time with simplified scaffolding and prompt for unchanged files

## Metadata

- **Spec ID:** 1523-review-all-files-every
- **Status:** Draft
- **Phase:** Phase 1 - Spec
- **Source:** Issue/feature request to review all files on every run, simplify scaffolding,
  and prompt for unchanged files when prior review context exists
- **Owner:** TBD
- **Last Updated:** TBD

## Summary

The review workflow must evaluate all files on every execution instead of skipping files solely
because they were reviewed previously. The scaffolding presented to the review model should be
simplified, and the system should use prior review state to inherit status where appropriate. When
a file is unchanged but has prior review history, the workflow should conditionally prompt the
reviewer in a way that preserves context without forcing redundant output. Output should clearly
distinguish newly reviewed, inherited, and unchanged-file decisions.

## Problem Statement

The current behavior relies on skip-oriented logic and more complex scaffolding than needed. This
creates gaps in repeatability, makes it harder to reason about the output of a fresh run, and
obscures whether unchanged files were actively considered or merely omitted. A revised flow is
needed so that every run considers every relevant file, while still leveraging prior state to avoid
unnecessary churn and to present clearer status to users.

## Goals

- Ensure every in-scope file is considered on every review run.
- Remove skip-based behavior that excludes files from review due to prior processing alone.
- Simplify review scaffolding passed into the system.
- Inherit prior status for unchanged files when valid prior state exists.
- Prompt conditionally for unchanged files so users and models receive appropriate context.
- Improve output clarity so consumers can distinguish active review outcomes from inherited ones.

## Non-Goals

- Redefining the meaning of review statuses beyond what is required for inheritance and reporting.
- Changing repository file discovery rules beyond ensuring all in-scope files are reviewed every run.
- Introducing new external dependencies or a new persistence mechanism.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Review all in-scope files every run

**Priority:** P1

As a user running the review workflow, I want every in-scope file to be considered each time, so
that the result reflects the full current repository state instead of a subset filtered by prior
runs.

**Related FRs:** FR-001, FR-002, FR-003

**Acceptance Scenarios**:

1. **Given** a repository with in-scope files that were reviewed on a previous run
   **When** the review workflow executes again
   **Then** each in-scope file is included in the current run's review processing
   **And** no file is excluded solely because it has prior review history
2. **Given** a repository containing both changed and unchanged in-scope files
   **When** the workflow executes
   **Then** both changed and unchanged files are considered
   **And** the workflow records an outcome for each file

### User Story 2 - Reuse prior status for unchanged files

**Priority:** P1

As a user, I want unchanged files with valid prior review state to inherit their prior status, so
that repeat runs remain efficient and consistent without losing previous decisions.

**Related FRs:** FR-004, FR-005, FR-006, FR-011

**Acceptance Scenarios**:

1. **Given** an unchanged file with a previously stored review status
   **When** the workflow processes the file on a later run
   **Then** the file inherits the previous status unless new review input requires a different
   outcome
2. **Given** an unchanged file without valid prior review state
   **When** the workflow processes the file
   **Then** the file is treated as requiring a normal review decision
   **And** no inheritance is applied from missing or invalid state
3. **Given** an unchanged file inheriting a terminal prior status
   **When** the workflow persists the current run state
   **Then** the file is marked with a dedicated inheritance flag indicating terminal-by-inheritance
   **And** downstream logic can distinguish inherited terminal status from a newly produced terminal status

### User Story 3 - Use simpler scaffolding

**Priority:** P2

As a maintainer, I want the review scaffolding to be simplified, so that the review logic is easier
to understand and maintain while preserving current review functionality.

**Related FRs:** FR-007, FR-008

**Acceptance Scenarios**:

1. **Given** the workflow is preparing instructions or context for a review step
   **When** scaffolding is generated
   **Then** the generated scaffolding contains only the information necessary for correct review
   behavior
   **And** redundant or obsolete skip-oriented scaffolding is removed
2. **Given** simplified scaffolding is used
   **When** the review workflow runs across the same set of files
   **Then** the workflow still produces complete per-file outcomes
3. **Given** a commit under review
   **When** simplified scaffolding is rendered
   **Then** it includes the minimal commit header format `### Commit: [<hash>](<url>)`
   **And** unchanged files with prior review context include `no changes since last review`

### User Story 4 - Prompt appropriately for unchanged files

**Priority:** P2

As a user or downstream reviewer, I want unchanged files to be conditionally prompted based on
whether prior state exists, so that the workflow preserves relevant context without generating
unnecessary repeated review content.

**Related FRs:** FR-008, FR-009

**Acceptance Scenarios**:

1. **Given** an unchanged file with valid prior review state
   **When** the workflow prepares the review prompt or context
   **Then** the prompt reflects that the file is unchanged
   **And** includes or references the prior status needed for inheritance or confirmation
2. **Given** an unchanged file with no prior review state
   **When** the workflow prepares the review prompt or context
   **Then** the workflow does not assume a prior decision
   **And** the file is presented for normal review handling
3. **Given** an unchanged file with prior state and unchanged assessment
   **When** the workflow evaluates whether to submit new review output
   **Then** no new review submission is emitted for that file
   **And** a new submission is emitted only when the current assessment differs from the prior one

### User Story 5 - Produce clear output for users

**Priority:** P3

As a user reading review results, I want output to clearly identify whether a file was newly
reviewed, inherited from prior state, or otherwise processed as unchanged, so that I can trust and
audit the workflow result.

**Related FRs:** FR-010

**Acceptance Scenarios**:

1. **Given** a completed workflow run containing changed files, unchanged inherited files, and files
   with no prior state
   **When** results are displayed or emitted
   **Then** each file's output clearly indicates its processing path and final status
2. **Given** a user compares outputs from multiple runs
   **When** they inspect unchanged files
   **Then** they can determine whether the status came from inheritance, active review, or fresh
   evaluation due to missing prior state

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001:** The system shall include every in-scope file in each review run.
- **FR-002:** The system shall not skip a file solely because that file was reviewed in a previous
  run.
- **FR-003:** The system shall detect whether a file is changed or unchanged relative to the
  comparison basis used by the workflow.
- **FR-004:** The system shall load prior review state for a file when such state is available.
- **FR-005:** The system shall inherit the prior review status for an unchanged file when valid
  prior state exists and no new review input overrides that status.
- **FR-006:** The system shall treat unchanged files without valid prior state as requiring normal
  review handling rather than inherited status.
- **FR-007:** The system shall simplify review scaffolding by removing obsolete skip-oriented
  instructions, retaining only context needed for correct review behavior, and emitting the minimal
  scaffold commit header `### Commit: [<hash>](<url>)`.
- **FR-008:** The system shall conditionally tailor prompts for unchanged files based on prior
  state; when valid prior state exists, the prompt shall include `no changes since last review`.
- **FR-009:** The system shall only submit new review output for unchanged files with prior state
  when the current assessment differs from the previously persisted assessment.
- **FR-010:** The system shall produce output that identifies, for each file, its final status and
  whether that status was newly determined, inherited, or produced after unchanged-file handling.
- **FR-011:** The system shall persist a dedicated inheritance marker for unchanged files that
  reuse prior terminal status, so downstream steps can distinguish terminal-by-inheritance from
  newly terminal outcomes.
- **FR-012:** The system shall handle deleted or missing files in prior state safely, without
  causing the run to fail or producing misleading inherited output for files no longer in scope.

### Non-Functional Requirements

- **NFR-001 (Performance):** Reviewing all in-scope files on every run shall not increase
  end-to-end runtime by more than 20% compared with the baseline established by running
  `agdt-review-pull-request` against the deterministic CI event fixtures in
  `tests/fixtures/ci_events/` (using `pull_request_opened.json` and
  `pull_request_synchronize.json`) on a standard CI runner (Ubuntu-latest, no model/network
  calls, mocked LLM responses), measured as wall-clock time from workflow entry to final status
  write.
- **NFR-002 (UX Consistency):** Output labels and processing terminology for changed, unchanged,
  inherited, and freshly reviewed files shall be consistent across CLI, logs, and generated review
  artifacts.
- **NFR-003 (Backward Compatibility):** Existing review status semantics and persisted state formats
  shall remain compatible unless an explicit migration path is documented.
- **NFR-004 (Test Coverage):** Automated tests shall cover changed files, unchanged files with prior
  state, unchanged files without prior state, deleted files, and multi-run behavior for status
  inheritance and output labeling.

## Edge Cases

- **EC-001: Missing prior state**
  If a file has no prior review state, the workflow must not infer a status and must process the
  file as a normal review candidate.

- **EC-002: First review run**
  On the first run, all in-scope files must be processed without inheritance because no prior review
  state exists yet.

- **EC-003: Deleted files**
  Files present in prior review state but no longer present in the current in-scope set must not be
  reviewed or reported as inherited current results.

- **EC-004: Invalid or partial prior state**
  Corrupt, incomplete, or unrecognized prior state for a file must be ignored for inheritance
  purposes, and the file must fall back to normal review handling.

- **EC-005: Multi-model interactions**
  When multiple models or stages participate in review generation, unchanged-file inheritance and
  output labels must remain deterministic and not depend on incidental differences in prompt wording
  between models.

- **EC-006: File transitions from unchanged to changed**
  A file that previously inherited status but is changed on the current run must receive normal
  review handling rather than automatic inheritance.

## Success Criteria *(mandatory)*

- **SC-001:** In a regression test fixture with prior review history, 100% of current in-scope
  files are represented in the workflow results for every run.
- **SC-002:** In a fixture containing unchanged files with valid prior state, at least 95% of those
  files inherit the expected prior status in automated tests, with any exceptions explained by
  explicit override logic.
- **SC-003:** In a fixture containing unchanged files without prior state, 100% of those files are
  processed without inherited status.
- **SC-004:** Output validation tests confirm that 100% of reported files include both a final
  status and a processing-path indicator (for example: reviewed, inherited, or
  unchanged-without-prior-state).
- **SC-005:** Test coverage includes at least one automated scenario for each listed edge case and
  for each user story's primary acceptance path.

## Open Questions

- What exact output labels should be used to distinguish inherited versus freshly reviewed results?
- What constitutes a "valid" prior state if stored data is partial but still parseable?
- What comparison basis defines "unchanged" for all supported review modes?

---

*Generated by Copilot SDK (claude-opus-4.6)*
