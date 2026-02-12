# Implementation Plan: Separate AGDT and Specify Documentation

**Branch**: `001-separate-docs` | **Date**: 2026-02-03 | **Spec**: [specs/001-separate-docs/spec.md](specs/001-separate-docs/spec.md)
**Input**: Feature specification from `/specs/001-separate-docs/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See
`.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Separate AGDT end‑user documentation from Specify developer documentation by
restructuring existing content into two clear sections with dedicated entry
points. Use README.md for end‑user guidance and SPEC_DRIVEN_DEVELOPMENT.md for
developer‑only Specify guidance, with explicit audience labeling on any
cross‑references.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical
  details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Markdown (repository documentation)  
**Primary Dependencies**: None  
**Storage**: N/A  
**Testing**: Developer review (heuristic, no automated tests)  
**Target Platform**: GitHub repository documentation  
**Project Type**: Documentation-only change  
**Performance Goals**: N/A (documentation navigation)  
**Constraints**: README.md must not include Specify references; cross-links
require audience labels
**Scale/Scope**: Repository documentation only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- I. Auto-Approval Friendly Design: Pass (no CLI changes).
- II. Single Source of Truth: Pass (no state changes).
- III. Background Task Architecture: Pass (no command changes).
- IV. Test-Driven Development & Coverage: Pass (documentation-only change; no

  executable code).
  executable code).

- V. Code Quality & Maintainability: Pass (docs updates will be clear and

  scoped).
  scoped).

- VI. User Experience Consistency: Pass (explicit audience labels, consistent

  structure).
  structure).

- VII. Performance & Responsiveness: Pass (no runtime impact).
- VIII. Python Package Best Practices: Pass (no package changes).

### Post-Design Re-check (Phase 1)

- I. Auto-Approval Friendly Design: Still Pass.
- II. Single Source of Truth: Still Pass.
- III. Background Task Architecture: Still Pass.
- IV. Test-Driven Development & Coverage: Still Pass (documentation-only).
- V. Code Quality & Maintainability: Still Pass.
- VI. User Experience Consistency: Still Pass.
- VII. Performance & Responsiveness: Still Pass.
- VIII. Python Package Best Practices: Still Pass.

## Project Structure

### Documentation (this feature)

```text
specs/001-separate-docs/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
README.md
SPEC_DRIVEN_DEVELOPMENT.md
specs/
├── README.md
└── 001-separate-docs/
```

**Structure Decision**: Documentation-only update scoped to repository root docs
and specs/README.md. No source code changes.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
