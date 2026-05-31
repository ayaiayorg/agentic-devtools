# Spec: Review all files every time with simplified scaffolding and prompt for unchanged files

## Metadata

- **Spec ID:** 1523-review-all-files-every
- **Status:** Draft
- **Phase:** Phase 2 - Clarify
- **Source:** Issue/feature request to review all files on every run, simplify scaffolding,
  and prompt for unchanged files when prior review context exists
- **Owner:** TBD
- **Last Updated:** 2026-05-23

## Summary

The review workflow must evaluate all files on every execution instead of skipping files solely
because they were reviewed previously. The scaffolding presented to the review model should be
simplified, and the system should use prior review state to inherit status where appropriate. When
a file is unchanged but has prior review history, the workflow should conditionally prompt the
reviewer in a way that preserves context without forcing redundant output. Output should clearly
distinguish newly reviewed, inherited, and unchanged-file decisions.

## Clarifications

### Session 2026-05-23

- Q: What exact output labels should be used to distinguish inherited versus freshly reviewed
  results? → A: Use the following three labels consistently across CLI output, logs, and
  review-state.json: `reviewed` (file was actively reviewed on this run, including changed/new
  files), `inherited` (file was unchanged, valid prior state existed, status carried forward), and
  `reviewed-no-prior` (file was unchanged with no valid prior state, required fresh review). These
  are persisted in a new `processingPath` field on `FileEntry`.
- Q: What constitutes a "valid" prior state if stored data is partial but still parseable? → A:
  Prior state is valid for inheritance if and only if: (1) the `FileEntry` exists in the prior
  `review-state.json`, (2) the `status` field is terminal (`approved` or `needs-work`), and
  (3) `ReviewState.commitHash` is present and used as the prior-side commit for unchanged
  comparison against `lastMergeSourceCommit.commitId`. Non-terminal statuses (`in-progress`,
  `unreviewed`) never qualify for inheritance and require full re-review. Partial entries missing
  `threadId`, `commentId`, or `folder` are treated as invalid and the file falls back to normal
  review.
- Q: What comparison basis defines "unchanged" for all supported review modes? → A: A file is
  "unchanged" when it has no content changes between the prior reviewed commit
  (`ReviewState.commitHash`) and the current head commit (`lastMergeSourceCommit.commitId`)
  according to the workflow's existing comparison signals (Azure DevOps iteration changes plus git
  diff cross-check, or an equivalent deterministic mechanism). If no prior `commitHash` exists
  (first run), all files are treated as changed.
- Q: Should the `SkippedFile` dataclass and `already_reviewed` skip reason be removed entirely or
  retained for backward compatibility during migration? → A: Remove the `already_reviewed` skip
  reason from `SkippedFile` usage in the prompt generation path. The `SkippedFile` dataclass
  itself is retained (it still serves the `not_on_branch` reason), but no file shall be added to
  `skippedFiles` with reason `already_reviewed` after this change. The `skippedFiles` field in
  `ReviewState` remains for backward-compatible deserialization of older state files.
- Q: For multi-model reviews, should inheritance apply per-model or globally per-file? → A:
  Inheritance applies globally per-file. If a file is unchanged and has valid prior terminal
  status, all configured models still evaluate it on the current run using the unchanged-file
  prompt/context. The workflow carries forward the prior status and existing `modelVerdicts` only
  when every current model assessment matches the prior persisted verdict, so no new review
  submission is needed. If any prior model verdict was non-terminal (`in-progress` or
  `unreviewed`), or any current model assessment differs, the file does not qualify for
  inheritance and fresh output is recorded for all models.

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
2. **Given** an unchanged file without valid prior review state (missing `FileEntry`, unrecognized
   `status`, or partial/invalid entry fields)
   **When** the workflow processes the file
   **Then** the file is treated as requiring a normal review decision
   **And** no inheritance is applied from missing or invalid state
3. **Given** an unchanged file inheriting a terminal prior status (`approved` or `needs-work`)
   **When** the workflow persists the current run state
   **Then** the file is marked with `processingPath: "inherited"` indicating terminal-by-inheritance
   **And** downstream logic can distinguish inherited terminal status from a newly produced terminal status
4. **Given** a multi-model review where the file has prior terminal status with all model verdicts also terminal
   **When** the workflow evaluates inheritance
   **Then** all configured models evaluate the unchanged file using prior context
   **And** the file inherits globally only when every current model assessment matches the prior
   terminal verdict
   **And** the `modelVerdicts` list is carried forward unchanged only in that case
5. **Given** a multi-model review where any prior model verdict is non-terminal or any current
   model assessment differs from the prior persisted verdict
   **When** the workflow evaluates inheritance
   **Then** the file does not qualify for inheritance
   **And** fresh review output is recorded for all models

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

1. **Given** a completed workflow run containing changed files, unchanged inherited files, and
   unchanged files with no valid prior state
   **When** results are displayed or emitted
   **Then** each file's output includes its `processingPath` label (`reviewed`, `inherited`, or `reviewed-no-prior`) and final status
2. **Given** a user compares outputs from multiple runs
   **When** they inspect unchanged files
   **Then** they can determine whether the status came from inheritance, active review, or fresh
   evaluation due to missing prior state

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001:** The system shall include every in-scope file in each review run.
- **FR-002:** The system shall not skip a file solely because that file was reviewed in a previous
  run. Specifically, the `already_reviewed` skip reason shall no longer be used to exclude files from prompt generation.
- **FR-003:** The system shall detect whether a file is changed or unchanged relative to the
  comparison basis used by the workflow. A file is "unchanged" when it has no content changes between the prior reviewed commit (`ReviewState.commitHash`) and the current head commit
  (`lastMergeSourceCommit.commitId`) according to the workflow's deterministic change-detection signals (Azure DevOps iteration changes plus git diff cross-check, or an equivalent mechanism). If no
  prior `commitHash` exists, all files are treated as changed.
- **FR-004:** The system shall load prior review state for a file when such state is available.
- **FR-005:** The system shall inherit the prior review status for an unchanged file when valid
  prior state exists and no new review input overrides that status. Valid prior state requires:
  (1) `FileEntry` exists in prior `review-state.json`, (2) `status` is terminal (`approved` or
  `needs-work`), (3) `ReviewState.commitHash` is present and used as the prior-side commit for
  unchanged comparison against `lastMergeSourceCommit.commitId`, and (4) `threadId`,
  `commentId`, and `folder` are all present in the `FileEntry` (partial entries missing any of
  these fields are invalid and the file falls back to normal review, per EC-004). For
  multi-model reviews, all model verdicts must be terminal for global inheritance to apply.
- **FR-006:** The system shall treat unchanged files without valid prior state as requiring normal
  review handling rather than inherited status.
- **FR-007:** The system shall simplify review scaffolding by removing obsolete skip-oriented
  instructions, retaining only context needed for correct review behavior, and emitting unchanged-
  file scaffold content in this exact order: `### Commit: [<hash>](<url>)`, then a blank line, then
  `no changes since last review`.
- **FR-008:** The system shall conditionally tailor prompts for unchanged files based on prior
  state; when valid prior state exists, the prompt shall include `no changes since last review`,
  and this unchanged-file scaffold content shall be generated during scaffolding before the AI agent
  session begins.
- **FR-009:** The system shall only submit new review output for unchanged files with prior state
  when the current assessment differs from the previously persisted assessment.
- **FR-010:** The system shall produce output that identifies, for each file, its final status and
  its `processingPath` label: one of `reviewed` (actively reviewed this run, including changed/new files), `inherited` (unchanged file with valid prior state, status carried forward), or
  `reviewed-no-prior` (unchanged file with no valid prior state, required fresh review).
- **FR-011:** The system shall persist `processingPath` on `FileEntry` for every in-scope file,
  using one of: `reviewed`, `inherited`, `reviewed-no-prior`. For unchanged files that reuse prior
  terminal status, `processingPath` shall be `inherited` so downstream steps can distinguish
  terminal-by-inheritance from newly terminal outcomes.
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
  artifacts. The canonical labels are: `reviewed`, `inherited`, `reviewed-no-prior`.
- **NFR-003 (Backward Compatibility):** Existing review status semantics and persisted state formats
  shall remain compatible. The `SkippedFile` dataclass is retained for the `not_on_branch` reason
  and for backward-compatible deserialization of older state files. The new `processingPath` field
  on `FileEntry` treats an absent value as null-equivalent during deserialization, ensuring older
  state files load without error.
- **NFR-004 (Test Coverage):** Automated tests shall cover changed files, unchanged files with prior
  state, unchanged files without prior state, deleted files, multi-model inheritance behavior, and multi-run behavior for status
  inheritance and output labeling.

## Edge Cases

- **EC-001: Missing prior state**
  If an unchanged file has no prior review state (no `FileEntry` in `review-state.json`), the workflow must not infer a status and must process the
  file as a normal review candidate with `processingPath: "reviewed-no-prior"`.

- **EC-002: First review run**
  On the first run, all in-scope files must be processed without inheritance because no prior review
  state exists yet. All files receive `processingPath: "reviewed"`.

- **EC-003: Deleted files**
  Files present in prior review state but no longer present in the current in-scope set must not be
  reviewed or reported as inherited current results. They remain in the prior state file for audit but are excluded from the current run's output.

- **EC-004: Invalid or partial prior state**
  Corrupt, incomplete, or unrecognized prior state for a file must be ignored for inheritance
  purposes, and the file must fall back to normal review handling. Specifically, entries missing `threadId`, `commentId`, or `folder`, or with an unrecognized `status` value, are treated as invalid.

- **EC-005: Multi-model interactions**
  When multiple models or stages participate in review generation, unchanged-file inheritance and
  output labels must remain deterministic and not depend on incidental differences in prompt wording
  between models. Inheritance applies globally per-file: either all models retain the inherited
  result because every current assessment matches the prior terminal verdict, or fresh output is
  recorded for all models.

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
  status and a `processingPath` indicator (one of: `reviewed`, `inherited`, or
  `reviewed-no-prior`).
- **SC-005:** Test coverage includes at least one automated scenario for each listed edge case and
  for each user story's primary acceptance path.

## Open Questions

*All prior open questions have been resolved in the Clarifications section above.*

---

*Generated by Copilot SDK (claude-opus-4.6)*
