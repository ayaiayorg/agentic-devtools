# Feature Specification: SpecKit Clarification Step — Content-Preserving Augmentation

**Feature Branch**: `speckit/1195/phase-1-specify`  
**Created**: 2026-04-15  
**Status**: Draft  
**Input**: User description: "SpecKit clarification step overwrites spec.md content instead of augmenting"  
**Source Issue**: #1195 (<https://github.com/ayaiayorg/agentic-devtools/issues/1195>)

## Problem Statement

The SpecKit CI/CD pipeline runs the workflow: specify → clarify → checklist → plan → tasks → analyze → markdownlint validation.
In phase 2 (clarify + checklist), the automated pipeline sends the full `spec.md` content to an LLM and writes the LLM response
back to disk using a destructive overwrite (`> spec.md`). When the LLM returns a truncated or summary-only response instead of
the full augmented specification, the original content — user stories, functional requirements, NFRs, edge cases — is
irrecoverably lost.

This was observed in PR #1178, where `spec.md` was reduced from a complete specification to a 14-line clarification summary table.
The SpecKit analysis step flagged this as CRITICAL (F01): 11 of 21 requirement definitions were lost. The same pattern affected
`checklists/requirements.md`, which was replaced with a description of what the checklist should contain rather than the actual
checklist.

The interactive agent mode (used in VS Code) already implements an incremental augmentation pattern with per-question atomic saves.
The CI/CD pipeline mode lacks equivalent safeguards.

---

## Clarifications

### Session 2026-04-21

- Q: Should the automated tests for the no-content-loss invariant be Python unit tests (mocking the LLM), shell integration tests in `generate-spec-from-issue.sh`, or both?
  → A: Both Python unit tests and shell integration tests are required. Updated NFR-005 inline to remove the `[NEEDS CLARIFICATION]` marker.

- Q: What file-size threshold should trigger a warning about potential context-window truncation?
  → A: 50 KB warning to stderr (non-blocking). Added as FR-012.

- Q: What should happen when the backup write fails (e.g., disk full)?
  → A: Abort immediately with OS-level error detail, leaving `spec.md` unchanged. Updated FR-002 inline; applicable to User Story 2 and Edge Cases.

- Q: What mechanism should be used for atomically replacing `spec.md` after validation?
  → A: `mv` (POSIX rename) from `spec.md.tmp`. Updated FR-006 inline; applicable to User Story 3 and Key Entities.

- Q: Which section headings are always-mandatory in every valid `spec.md`?
  → A: `## Problem Statement`, `## User Scenarios & Testing`, `## Requirements`, `## Success Criteria`.
  Updated FR-006 inline, Structural Validation Report entity, and added new Always-Mandatory Sections entity.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Clarification Preserves Complete Specification (Priority: P1)

As a developer triggering the SpecKit pipeline via a `speckitspec`-labeled GitHub issue,
I want the clarification phase to augment my specification with clarification answers while preserving every existing section
(user stories, FRs, NFRs, edge cases, entities, success criteria),
so that no content is lost between pipeline phases.

**Why this priority**: This is the core defect. Without content preservation, the entire SpecKit pipeline produces unusable output.
Every downstream phase (plan, tasks, analyze) depends on a complete spec.md. Data loss here cascades into total pipeline failure.

**Requirement Count Definition**: For all retention comparisons in this spec, a "requirement" or "requirement entry" means only a
distinct bullet or numbered list item in the `## Requirements` section whose identifier begins with `FR-` or `NFR-` (for example,
`FR-001` or `NFR-003`). Do **not** count user stories, acceptance scenarios, checklist items, section headings, edge cases,
entities, or success criteria unless they are also restated as `FR-###` or `NFR-###` items in `## Requirements`.

**Independent Test**: Run the full specify → clarify pipeline on a test issue. Compare the section headings and the number of
`FR-###`/`NFR-###` requirement entries in the `## Requirements` section of `spec.md` before and after clarification. The
post-clarify spec must contain every original section and at least 95% as many requirement entries as the pre-clarify version,
with any reduction attributable only to deduplication or merging rather than content loss.

**Acceptance Scenarios**:

1. **Given** a complete `spec.md` produced by the specify phase with N total requirements across its existing sections,
**When** the clarification phase completes in CI/CD mode, **Then** `spec.md` retains at least 95% of those requirements,
with any reduction caused only by deduplication or merging, plus any new content introduced by clarification answers.

2. **Given** a complete `spec.md` with sections including `## User Scenarios & Testing`, `## Requirements`,
`## Success Criteria`, and `## Edge Cases`, **When** the clarification phase completes,
**Then** every original section heading is still present in the output file.

3. **Given** a `spec.md` containing `[NEEDS CLARIFICATION]` markers, **When** the clarification step resolves those markers,
**Then** each resolved marker is replaced with the clarification answer in-place within the appropriate section,
and a corresponding entry is appended to the `## Clarifications` section.

---

### User Story 2 — Pre-Write Backup Prevents Irrecoverable Loss (Priority: P1)

As a developer relying on the automated SpecKit pipeline, I want the clarification step to create a backup of `spec.md`
before writing any changes, so that the original content can be recovered if the LLM produces a defective response.

**Why this priority**: Even with improved prompting, LLM output is non-deterministic. A backup is the safety net that prevents
the catastrophic data loss observed in #1178. This is a P1 because it's the only mechanism that guarantees recoverability
regardless of LLM behavior.

**Independent Test**: Run the clarification phase and verify that, before any modifications are written, a backup file exists
alongside `spec.md` using the deterministic naming scheme `spec.md.bak`, or `spec.md.bak.N` when collisions are present.

**Acceptance Scenarios**:

1. **Given** an existing `spec.md` in the feature directory, **When** the clarification phase begins execution,
**Then** a backup copy is created at `spec.md.bak`, or at the next available numbered path `spec.md.bak.N` if that filename
already exists, before any write operation occurs.

2. **Given** a backup was created and the clarification phase produced a defective output,
**When** a developer inspects the feature directory, **Then** the backup file contains the complete original
`spec.md` content and can be used to restore the specification.

---

### User Story 3 — Pre-Commit Structural Validation (Priority: P1)

As a pipeline operator, I want the clarification step to write the LLM response to a temporary candidate file, validate
that candidate for structural completeness, and only then atomically replace `spec.md`, so that defective LLM responses
are rejected before the canonical specification on disk is changed.

**Why this priority**: Validation closes the feedback loop. Without an explicit temp-write → validate → atomic-replace
contract, truncated output can still overwrite `spec.md` and only be discovered in phase 5 (analyze) — too late to
prevent a broken PR. This contract preserves the original file on validation failure while still keeping the backup
available for manual recovery.

**Independent Test**: Inject a deliberately truncated LLM response into the clarification step and verify that the
candidate output fails validation, `spec.md` is not replaced, and the pipeline reports the validation failure.

**Acceptance Scenarios**:

1. **Given** the original `spec.md` contains sections `## User Scenarios & Testing`, `## Requirements`,
and `## Success Criteria`, **When** the LLM output written to the temporary candidate file is missing any of these
mandatory sections, **Then** validation fails, the original `spec.md` remains unchanged, the backup remains available,
and the pipeline reports a clear error message identifying which sections were lost.

2. **Given** the original `spec.md` contains 15 requirement entries (FR + NFR), **When** the LLM output retains fewer
than `ceil(0.95 * N)` of the original requirement count (where `N` is the original count; for `N = 15`, that means fewer
than 15 entries retained, so 14 of 15 entries retained fails validation), **Then** the validation flags the output as
truncated, does not replace `spec.md`, leaves the original file unchanged, keeps the backup available, and reports the
count discrepancy.

3. **Given** the LLM output passes structural validation (all mandatory sections present, requirement count within threshold),
**When** the write completes, **Then** the backup file is retained (not deleted) for audit purposes
and the pipeline proceeds to the next phase.

---

### User Story 4 — Clarification Audit Trail (Priority: P2)

As a developer reviewing a SpecKit-generated PR, I want to see a clear record of what clarifications were applied and where,
so that I can verify the clarification step added value without removing content.

**Why this priority**: Traceability builds trust in the automated pipeline. While not strictly required to fix the data loss bug,
it makes clarification outcomes reviewable in PR diffs and aligns with the existing interactive agent's
`## Clarifications` section pattern.

**Independent Test**: Run the clarification phase and verify that the output `spec.md` contains a `## Clarifications` section
with dated entries mapping questions to answers and the sections they modified.

**Acceptance Scenarios**:

1. **Given** a `spec.md` without a `## Clarifications` section, **When** the clarification phase runs and resolves
two ambiguities, **Then** a `## Clarifications` section is appended with a session subheading containing two Q&A
bullet entries, each referencing the spec section that was updated.

2. **Given** a `spec.md` that already has a `## Clarifications` section from a previous run,
**When** the clarification phase runs again, **Then** a new session subheading is appended under the existing
`## Clarifications` section without duplicating or removing prior entries.

---

### User Story 5 — Checklist Preservation (Priority: P2)

As a developer using the SpecKit pipeline, I want the clarification phase to preserve the `checklists/requirements.md`
file's content with the same safeguards applied to `spec.md`,
so that the requirements checklist is not overwritten with a description of itself.

**Why this priority**: The checklist is a sibling artifact that suffered the same class of defect in #1178.
Fixing spec.md alone leaves the pipeline partially broken if the checklist is still vulnerable to content loss.

**Checklist Item Count Definition**: For all retention comparisons involving `checklists/requirements.md` in this spec,
a "checklist item" means a Markdown task list item — a line matching the pattern `- [ ] ...` (unchecked) or
`- [x] ...` (checked). Do **not** count plain bullet points (`- ...` without a checkbox), numbered list items,
section headings, or blank lines. This definition ensures deterministic counting in both validation logic and tests.

**Independent Test**: Run the clarification phase with an existing `checklists/requirements.md` containing concrete
checklist items (Markdown task list items). Verify the output file retains all original items.

**Acceptance Scenarios**:

1. **Given** a `checklists/requirements.md` containing N checklist items (as defined by the Checklist Item Count
Definition above), **When** the clarification phase completes, **Then** the output file contains at least N
checklist items.

2. **Given** a `checklists/requirements.md` file exists, **When** the clarification phase begins,
**Then** a backup is created before any modifications, following the same backup pattern as `spec.md`.

---

### User Story 6 — Parity Between Interactive and CI Modes (Priority: P3)

As a SpecKit maintainer, I want the CI/CD clarification mode to follow the same augmentation contract as the interactive
agent mode, so that both paths produce structurally equivalent results and share validation logic.

**Why this priority**: Long-term maintainability. The interactive agent already implements incremental augmentation correctly.
Aligning the CI path reduces the surface area for divergent bugs.
This is P3 because it's an architectural improvement rather than an immediate fix.

**Independent Test**: Run both the interactive agent and the CI pipeline on the same input spec and compare the structural
properties of the output (section count, requirement count, presence of `## Clarifications` section).

**Acceptance Scenarios**:

1. **Given** the same `spec.md` input, **When** the clarification step runs in interactive mode and in CI mode
with the same clarification answers, **Then** both outputs contain identical section headings and comparable
requirement counts (within a tolerance of ±1 for minor phrasing differences).

---

### Edge Cases

- What happens when `spec.md` does not exist at the start of the clarification phase?
The step should fail with a clear error rather than creating a clarification-only file from scratch.
- What happens when `spec.md` is empty (0 bytes)?
The step should fail with an error indicating that the specify phase did not produce output.
- What happens when the LLM returns an empty string or a network error occurs mid-generation?
The pipeline should report the failure and leave the original `spec.md` unchanged if replacement has not begun.
If a destructive write partially occurred after replacement began, the backup must be restored.
- What happens when the LLM returns content that is syntactically valid Markdown but semantically a summary/description
of the spec rather than the spec itself?
The section-count and requirement-count validation should catch this pattern.
- What happens when `spec.md` is very large (>50KB) and exceeds the LLM's effective context window?
*(Out of scope for this fix. Context-window handling and chunking strategies will be addressed in a follow-up issue.
For now, the existing behavior — passing the full content to the LLM — is unchanged.)*
- What happens when the backup file already exists from a previous failed run?
The new backup should use the next available numbered suffix (`spec.md.bak.1`, `spec.md.bak.2`, etc.)
to avoid overwriting the previous backup.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CI/CD clarification step MUST read the existing `spec.md` content
before generating any output.

- **FR-002**: The CI/CD clarification step MUST create a backup of `spec.md`
before writing any modifications to the file. If the backup write fails (e.g., disk full),
the clarification step MUST abort immediately with an OS-level error detail and leave `spec.md` unchanged.

- **FR-003**: The CI/CD clarification step MUST preserve all existing sections of `spec.md` when writing
clarification results. No section present in the input may be absent from the output.

- **FR-004**: The CI/CD clarification step MUST preserve the substantive content of each section —
requirement entries, user stories, acceptance scenarios, edge cases — not merely the section headings.

- **FR-005**: The CI/CD clarification step MUST append a `## Clarifications` section (or add entries to an existing one)
documenting each clarification question, the accepted answer, and which spec section was updated.

- **FR-006**: The CI/CD clarification step MUST write clarification results to a staged output
(a temporary file `spec.md.tmp`) and perform structural validation
against that staged output before replacing `spec.md` via atomic rename (`mv` / POSIX rename),
comparing presence of the always-mandatory sections by normalized heading text (`## Problem Statement`,
`## User Scenarios & Testing`, `## Requirements`, `## Success Criteria`), where validation MUST
strip any trailing `*(mandatory)*` annotation from both expected and actual headings before matching,
presence of all section headings found in the input, and requirement entry counts against
the original. Requirement-entry retention MUST be computed as `(number of requirement entries present
in the staged output ÷ number of requirement entries present in the original input) × 100`. The staged
output MUST retain at least 95% of the original requirement entries for validation to pass. Any result
below 95% MUST be treated as a hard validation failure, preventing replacement of `spec.md` and
triggering the failure handling defined in **FR-007**. When the original input contains zero
requirement entries, the retention check MUST be skipped (treated as a pass), because no entries can
be lost; this aligns with **SC-001**'s precondition of "≥5 requirement entries."
This retention rule MUST align with **SC-001** and **User Story 1**.

- **FR-007**: When structural validation of the staged output fails, including when requirement-entry
retention is below 95%, the system MUST leave the existing `spec.md` unchanged and report which
validation checks failed. If a failure occurs after replacement of `spec.md` has begun or completed,
the system MUST restore `spec.md` from the backup and report the restoration action and the
triggering failure.

- **FR-008**: The CI/CD clarification step MUST apply the same backup, preservation, and validation safeguards
to `checklists/requirements.md` as to `spec.md`. Checklist-item retention MUST be computed by counting Markdown
task list items (`- [ ] ...` or `- [x] ...`) in both the original and the staged output, consistent with the
Checklist Item Count Definition in User Story 5. The staged output MUST retain 100% of the original checklist
items for validation to pass. When the original file contains zero checklist items, the retention check MUST be
skipped (treated as a pass).

- **FR-009**: The system MUST fail with a clear, actionable error message if `spec.md` does not exist or is empty
when the clarification phase starts.

- **FR-010**: The system MUST retain backup files after successful writes for audit and recovery purposes.
Backups MUST NOT be automatically deleted on success.

- **FR-011**: The system MUST replace `[NEEDS CLARIFICATION]` markers in-place within the appropriate spec section
when a clarification resolves the ambiguity,
rather than only recording the answer in the `## Clarifications` section.

- **FR-012**: When `spec.md` is greater than or equal to 50 KB (50,000 bytes), the clarification step MUST emit a warning to stderr
(non-blocking) alerting the user to potential context-window truncation risk. Processing MUST continue
normally after the warning.

### Non-Functional Requirements

- **NFR-001**: The backup and validation overhead MUST add no more than 5 seconds to the clarification phase
execution time (excluding LLM call latency).

- **NFR-002**: Validation error messages MUST identify the specific sections or counts that failed validation,
enabling a developer to diagnose the issue without inspecting file diffs manually.

- **NFR-003**: The backup file naming convention MUST be deterministic and documented,
so that recovery scripts and developers can locate backups programmatically.

- **NFR-004**: The clarification step MUST produce consistent structural results regardless of whether it runs
in interactive (agent) mode or automated (CI/CD) mode, as defined by a shared validation contract.

- **NFR-005**: All changes to the clarification pipeline MUST be covered by automated tests that verify
the no-content-loss invariant. Both Python unit tests (within the pytest suite) and shell-script-level
integration tests (in the pipeline) are required.

### Key Entities

- **Spec Document (`spec.md`)**: The feature specification file produced by the specify phase.
Contains structured sections (User Scenarios, Requirements, Success Criteria, Edge Cases, etc.)
with requirement entries, user stories, and acceptance scenarios.
The canonical artifact that all downstream phases depend on.

- **Requirements Checklist (`checklists/requirements.md`)**: A companion artifact containing concrete,
checkable requirement items derived from the spec.
Used for quality validation during planning and implementation.

- **Backup File (`spec.md.bak`)**: A point-in-time copy of a spec artifact created immediately before the
clarification step writes modifications.
Serves as the recovery source when validation fails.

- **Clarification Session**: A logical grouping of Q&A pairs produced during a single clarification run.
Recorded in the `## Clarifications` section with a date-stamped subheading.
Each entry links a question to its answer and the spec section that was modified.

- **Structural Validation Report**: The result of comparing the post-clarification output against the
pre-clarification baseline. Contains section presence checks (including the always-mandatory sections:
`## Problem Statement`, `## User Scenarios & Testing`, `## Requirements`, `## Success Criteria`),
requirement counts, and pass/fail status for each check.

- **Always-Mandatory Sections**: The set of section headings that must be present in every valid `spec.md`
after clarification: `## Problem Statement`, `## User Scenarios & Testing`, `## Requirements`,
`## Success Criteria`. Absence of any of these triggers a hard validation failure.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After the clarification phase runs on any `spec.md` containing ≥5 requirement entries,
the output file retains 100% of the original section headings and ≥95% of the original requirement entry count
(allowing for merging of duplicate entries during clarification).

- **SC-002**: Zero instances of irrecoverable content loss in the SpecKit pipeline across all runs after this fix
is deployed. The CRITICAL F01 class of defect observed in #1178 must not recur.

- **SC-003**: Every clarification phase execution produces a backup file that can be used to fully restore
the pre-clarification `spec.md` content.

- **SC-004**: Structural validation catches 100% of cases where the LLM output has fewer mandatory sections
than the input, preventing truncated specs from being committed.

- **SC-005**: The `## Clarifications` section is present in the output `spec.md` after every clarification run,
providing a reviewable audit trail in the PR diff.

- **SC-006**: The `checklists/requirements.md` file is protected by the same backup-validate-restore cycle
as `spec.md`, with zero content loss incidents after deployment.

---

## Open Questions

All open questions have been resolved during Phase 2 clarification. See `## Clarifications` above.

---

*Generated by Copilot SDK (claude-opus-4.6)*
