# Feature Specification: Update Constitution to v1.2.0

**Feature Branch**: `speckit/1580/phase-1-specify`  
**Created**: 2026-05-26  
**Status**: Draft  
**Input**: User description: "Update constitution to v1.2.0 — align with new architecture, coverage, and pre-1.0 policy"  
**Source Issue**: #1580 (<https://github.com/ayaiayorg/agentic-devtools/issues/1580>)

## Problem Statement

The project constitution (`.specify/memory/constitution.md`) at v1.1.0 is out of alignment with the current codebase reality and project direction. Specifically:

1. **Principle I** promotes auto-approval as a central design principle, when it is actually a temporary workaround — the real principle is scoped tool availability per workflow step.
2. **Principle II** claims a single JSON file with "no distributed configuration," but the project now uses dual-layer state (CLI JSON segments + LangGraph checkpointing) and requires parallel-safe
   isolated state segments.
3. **Principle IV** states "Minimum 95% code coverage" while ADR-011 and `pyproject.toml` already enforce 100%.
4. **Principle VI** requires major version bumps for breaking CLI changes, but the project is pre-1.0 and expects breaking changes.
5. The constitution lacks principles for LangGraph orchestration, dual-engine compatibility, and pre-1.0 flexibility that are now established patterns.
6. The Development Workflow and Governance sections contain backward-compatibility requirements that conflict with pre-1.0 iteration speed.

The constitution is the authoritative design document — downstream templates, specs, and code reviews all reference it. Misalignment causes confusion and inconsistent decisions.

## User Scenarios & Testing

### User Story 1 - Constitution Accurately Reflects Architecture (Priority: P1)

As a contributor reading the constitution, I need Principle II (State Architecture) to accurately describe the dual-layer state system (CLI parallel-safe JSON segments + LangGraph checkpointing) so
that I design new features using the correct patterns.

**Why this priority**: The state architecture principle is referenced by every spec and implementation. Incorrect guidance leads to architecturally unsound designs.

**Independent Test**: Can be fully tested by reading the updated constitution and verifying it describes the dual-layer state model, references specs #1428/#1430/#1525, and removes "No distributed
configuration."

**Mapped Functional Requirements**: FR-003

**Acceptance Scenarios**:

1. **Given** the constitution at v1.2.0, **When** a contributor reads Principle II, **Then** they find guidance on both CLI state (parallel-safe JSON segments) and LangGraph checkpointing for
   orchestration workflows.
2. **Given** the constitution at v1.2.0, **When** a contributor searches for "No distributed configuration," **Then** the phrase does not appear.
3. **Given** the constitution at v1.2.0, **When** a contributor reads Principle II, **Then** it references the requirement for parallel-safe isolated state segments for concurrent subagent execution.

---

### User Story 2 - Coverage Requirement Aligned to 100% (Priority: P1)

As a contributor or reviewer, I need all coverage references in the constitution to state 100% so that there is no ambiguity between the constitution and the actual CI enforcement
(`--cov-fail-under=100`).

**Why this priority**: Contradictory coverage targets cause confusion during code review and test writing. ADR-011 is already authoritative at 100%.

**Independent Test**: Can be fully tested by searching the constitution for any occurrence of "95%" and verifying none exist, while "100%" appears in all coverage contexts.

**Mapped Functional Requirements**: FR-004, FR-011

**Acceptance Scenarios**:

1. **Given** the updated constitution, **When** I search for "95%", **Then** zero matches are found.
2. **Given** the updated constitution, **When** I read Principle IV and the Quality Gates section, **Then** coverage is stated as 100%.

---

### User Story 3 - Pre-1.0 Flexibility Policy Established (Priority: P1)

As a contributor, I need the constitution to explicitly state that breaking changes are allowed pre-1.0, so that I do not waste effort on migration plans, deprecation periods, or
backward-compatibility shims for iterative improvements.

**Why this priority**: The current constitution blocks rapid iteration by requiring major version bumps and migration plans for any breaking change. This contradicts the project's pre-1.0 reality.

**Independent Test**: Can be fully tested by reading the new Principle XI and verifying it explicitly permits breaking changes pre-1.0 without migration plans.

**Mapped Functional Requirements**: FR-008, FR-009, FR-010

**Acceptance Scenarios**:

1. **Given** the updated constitution, **When** I read Principle XI (Pre-1.0 Flexibility), **Then** it states that breaking changes are allowed and expected until v1.0.0.
2. **Given** the updated constitution, **When** I read the Development Workflow section, **Then** the backward-compatibility requirement is replaced with the pre-1.0 policy.
3. **Given** the updated constitution, **When** I read the Governance → Amendments section, **Then** "Migration plan for affected code" is not listed as mandatory.

---

### User Story 4 - Scoped Tool Availability Principle Replaces Auto-Approval (Priority: P1)

As a workflow designer, I need Principle I to describe scoped tool/command availability per workflow step so that I define explicit capability declarations for each step rather than relying on the
auto-approval workaround.

**Why this priority**: This principle shapes how every workflow step is designed. The shift from "auto-approval friendly" to "explicitly scoped tools" is a fundamental design philosophy change.

**Independent Test**: Can be fully tested by reading Principle I and verifying it describes scoped tool availability, explicitly states auto-approval is a temporary workaround, and defines that each
workflow step has a precisely defined set of available tools/commands.

**Mapped Functional Requirements**: FR-002

**Acceptance Scenarios**:

1. **Given** the updated constitution, **When** I read Principle I, **Then** the title is "Scoped Tool Availability" (or equivalent) and describes explicit capability declarations per step.
2. **Given** the updated constitution, **When** I search for "Auto-Approval Friendly Design" as a principle title, **Then** it does not appear.
3. **Given** the updated constitution, **When** I read Principle I, **Then** it acknowledges auto-approval as a recognized temporary workaround, not a design principle.

---

### User Story 5 - LangGraph Orchestration Principle Added (Priority: P2)

As a workflow implementer, I need a new Principle IX documenting that multi-step workflows use LangGraph with checkpoint state recovery and human-in-the-loop interrupts, so that I follow the
established orchestration pattern.

**Why this priority**: LangGraph is the chosen orchestration framework (specs #1428, #1430) but has no constitutional backing yet. Adding it prevents ad-hoc alternatives.

**Independent Test**: Can be fully tested by reading the new Principle IX and verifying it codifies LangGraph checkpointing, state recovery, and human-in-the-loop interrupts.

**Mapped Functional Requirements**: FR-006

**Acceptance Scenarios**:

1. **Given** the updated constitution, **When** I read Principle IX, **Then** it describes LangGraph as the orchestration framework for multi-step workflows.
2. **Given** the updated constitution, **When** I read Principle IX, **Then** it mentions checkpoint state recovery and human-in-the-loop interrupts as required capabilities.

---

### User Story 6 - Dual-Engine Compatibility Principle Added (Priority: P2)

As a contributor adding a new orchestration engine, I need Principle X to specify that new engines must coexist with existing paths via explicit opt-in routing and that failures in one engine must not
affect the other.

**Why this priority**: Prevents regressions during the transition period where both CLI-driven and LangGraph workflows exist.

**Independent Test**: Can be fully tested by reading Principle X and verifying it describes opt-in routing (`--engine` flag) and fault isolation between engines.

**Mapped Functional Requirements**: FR-007

**Acceptance Scenarios**:

1. **Given** the updated constitution, **When** I read Principle X, **Then** it requires explicit opt-in routing for engine selection.
2. **Given** the updated constitution, **When** I read Principle X, **Then** it states that failures in one engine must not affect the other.

---

### User Story 7 - Sync Impact Report Updated (Priority: P2)

As a template maintainer, I need the Sync Impact Report header in the constitution to reflect the v1.1.0 → v1.2.0 change with a summary of modified, added, and removed principles, so that downstream
templates can be reviewed for alignment.

**Why this priority**: The Sync Impact Report is the mechanism that triggers downstream template updates. Without it, templates drift.

**Independent Test**: Can be fully tested by reading the HTML comment block at the top of the constitution and verifying it lists the v1.2.0 changes.

**Mapped Functional Requirements**: FR-001, FR-012

**Acceptance Scenarios**:

1. **Given** the updated constitution, **When** I read the Sync Impact Report comment, **Then** it shows version change 1.1.0 → 1.2.0.
2. **Given** the updated constitution, **When** I read the Sync Impact Report, **Then** it lists all modified principles (I, II, IV, VI), added principles (IX, X, XI), and removed content.
3. **Given** the updated constitution, **When** I read the Sync Impact Report, **Then** it lists templates requiring review for alignment.

---

### User Story 8 - UX Consistency Principle Updated (Priority: P3)

As a CLI designer, I need Principle VI to remove the "major version bump" requirement for breaking CLI changes and instead reference the pre-1.0 flexibility policy.

**Why this priority**: Lower priority because it's a small textual change within a principle that is otherwise correct. The pre-1.0 principle (Story 3) already establishes the policy.

**Independent Test**: Can be fully tested by reading Principle VI and verifying it does not mention major version bumps for breaking changes.

**Mapped Functional Requirements**: FR-005

**Acceptance Scenarios**:

1. **Given** the updated constitution, **When** I read Principle VI, **Then** the bullet about "Breaking changes to CLI UX require a major version bump and migration notes" is absent.

---

### Edge Cases

- What happens if downstream templates reference specific principle numbers that are renumbered? The Sync Impact Report must flag renumbered principles explicitly.
- How does the constitution handle the case where LangGraph is later replaced by another orchestration framework? Principle IX should be framework-agnostic enough to allow amendment without
  restructuring.
- What if a contributor reads both the constitution and stale docs (e.g., `docs/10-quality-requirements.md`) that still say 95%? The constitution's Sync Impact Report should note these as requiring
  follow-up updates.

## Requirements

### Functional Requirements

- **FR-001**: The constitution MUST be updated to version 1.2.0 with the version footer reflecting the new version and ratification date.
- **FR-002**: Principle I MUST be renamed and rewritten to describe scoped tool/command availability per workflow step, acknowledging auto-approval as a temporary workaround.
- **FR-003**: Principle II MUST be rewritten to describe dual-layer state architecture (CLI parallel-safe JSON segments + LangGraph checkpointing), removing "No distributed configuration."
- **FR-004**: Principle IV MUST state 100% code coverage (not 95%), aligned with ADR-011 and `pyproject.toml`.
- **FR-005**: Principle VI MUST remove the requirement for major version bumps on breaking CLI changes.
- **FR-006**: A new Principle IX MUST be added describing LangGraph orchestration with checkpoint state recovery and human-in-the-loop interrupts.
- **FR-007**: A new Principle X MUST be added describing dual-engine compatibility with opt-in routing and fault isolation.
- **FR-008**: A new Principle XI MUST be added codifying the pre-1.0 flexibility policy (breaking changes allowed, no migration plans required, active removal of dead code).
- **FR-009**: The Development Workflow → Code Changes section MUST replace the backward-compatibility requirement with the pre-1.0 policy.
- **FR-010**: The Governance → Amendments section MUST remove "Migration plan for affected code" as a mandatory requirement.
- **FR-011**: The Quality Gates → Pre-Commit section MUST update coverage from "≥ 95%" to "100%."
- **FR-012**: The Sync Impact Report HTML comment MUST be updated to reflect the v1.1.0 → v1.2.0 changes, listing all modifications, additions, removals, and templates requiring review.

### Non-Functional Requirements

- **NFR-001**: The constitution MUST remain a single markdown file at `.specify/memory/constitution.md`.
- **NFR-002**: The constitution MUST be self-contained — no external file dependencies for understanding the principles.
- **NFR-003**: All principle descriptions MUST include a **Rationale** block explaining the "why."
- **NFR-004**: The document MUST maintain consistent formatting (heading levels, bullet styles, bold labels) matching the existing structure.

### Key Entities

- **Constitution**: The authoritative design document at `.specify/memory/constitution.md` that governs all project decisions.
- **Sync Impact Report**: HTML comment block at the top of the constitution that tracks version changes and downstream template impacts.
- **Principle**: A numbered, titled section within the constitution that establishes a non-negotiable design rule with rationale.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The constitution file contains `**Version**: 1.2.0` in its footer.
- **SC-002**: Zero occurrences of "95%" exist in the constitution.
- **SC-003**: The string "No distributed configuration" does not appear in the constitution.
- **SC-004**: The string "Breaking changes to CLI UX require a major version bump" does not appear in the constitution.
- **SC-005**: The string "Migration plan for affected code" does not appear as a mandatory amendment requirement.
- **SC-006**: Principles IX, X, and XI exist with titles related to LangGraph Orchestration, Dual-Engine Compatibility, and Pre-1.0 Flexibility respectively.
- **SC-007**: The Sync Impact Report comment block lists version change `1.1.0 -> 1.2.0` and enumerates all modified/added/removed content.
- **SC-008**: All existing principles (III, V, VII, VIII) remain unchanged in substance (only Principle number shifts if any are acceptable provided the Sync Impact Report documents them).

---
*Generated by Copilot SDK (claude-opus-4.6)*
