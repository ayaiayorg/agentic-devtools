# Feature Specification: SpecKit pipeline cross-reference plan code references against actual codebase

**Feature Branch**: `speckit/1204/phase-1-specify`
**Created**: `2026-04-27`
**Status**: `Draft`
**Input**: `Add a SpecKit pipeline detection pass that cross-references plan code references against the actual codebase.`
**Source Issue**: #1204

## Summary

Add a new analysis pass to the `speckit.analyze` pipeline that cross-references code symbols mentioned in a generated implementation plan
against the actual repository contents. The goal is to detect when a plan references files, classes, functions, methods, commands, or modules
that do not exist, are misspelled, or appear to point to the wrong location, so the plan can be corrected before downstream implementation or
review begins.

This detection pass integrates as **Pass G** in the existing A–F framework of `speckit.analyze`.

## Problem Statement

Plans can contain inaccurate code references, especially when they are generated from incomplete context, stale assumptions, or fuzzy
recollection of symbol names. Those bad references reduce trust in the plan, slow implementation, and create avoidable clarification loops
in later phases. The pipeline needs a deterministic way to identify suspect references and report them with enough context for a human or
later automation step to decide whether the reference is valid, should be corrected to an existing symbol, or intentionally refers to a new
symbol that does not exist yet.

## Goals

- Detect references in the plan that do not map cleanly to the current codebase.
- Distinguish high-confidence invalid references from ambiguous cases.
- Suggest likely intended matches when confidence is sufficient.
- Avoid flagging intentionally new symbols when the plan clearly indicates creation intent.
- Surface findings in the existing `speckit.analyze` report structure so later phases can rely on them.

## Non-Goals

- Automatically editing source code as part of Pass G.
- Guaranteeing perfect symbol resolution across every language or framework.
- Replacing later human review for architecture-level intent.
- Blocking plans solely because a reference is ambiguous but plausibly valid.

## Assumptions and Context

- The repository being analyzed is available locally at analysis time.
- Earlier analysis passes already provide the plan text or structured plan sections for Pass G to inspect.
- The implementation should prefer existing standard-library or already-used project mechanisms first.
- Fuzzy matching may be used to improve suggestion quality, but deterministic output is required for the same repository state and plan input.

## User Scenarios & Testing *(mandatory)*

### US1 — Detect nonexistent code references in a plan

**Priority:** P1

As a developer reviewing a generated plan, I want references to nonexistent files or symbols flagged, so I can correct the plan before implementation starts.

**Acceptance scenarios**

- **Given** a plan that references a file or symbol that does not exist anywhere in the repository, **when** Pass G runs, **then** the
  report includes a finding with the unresolved reference text and enough context to locate it in the plan.
- **Given** a plan with multiple invalid references, **when** Pass G runs, **then** each invalid reference is reported separately rather than collapsed into a single generic warning.
- **Given** a plan with only valid references, **when** Pass G runs, **then** no invalid-reference findings are emitted.

### US2 — Suggest likely intended matches

**Priority:** P1

As a developer, I want the analyzer to propose likely existing symbols when a referenced symbol seems misspelled or slightly wrong, so I can fix the plan quickly.

**Acceptance scenarios**

- **Given** a plan reference that differs slightly from an existing symbol name, **when** the similarity threshold is met, **then** the finding includes one or more ranked candidate matches.
- **Given** a plan reference with no close candidates, **when** Pass G runs, **then** the finding states that no reliable suggestion was found instead of inventing a weak match.
- **Given** multiple similarly strong candidates, **when** Pass G runs, **then** the finding is marked ambiguous rather than presenting one guess as definitive.

### US3 — Respect explicit "new symbol" intent

**Priority:** P1

As a developer authoring a plan, I want references that are clearly described as new code to avoid being flagged as invalid, so the analyzer does not produce noisy false positives.

**Acceptance scenarios**

- **Given** a plan step that explicitly says a new file, function, class, or command will be created, **when** that symbol is not present
  in the repository, **then** Pass G does not emit an invalid-reference finding for that symbol.
- **Given** a plan that references a missing symbol without any creation intent markers, **when** Pass G runs, **then** the symbol is still eligible to be flagged.
- **Given** a plan that mixes new-symbol intent and existing-symbol references in the same step, **when** Pass G runs, **then** only the unresolved existing-symbol references are flagged.

### US4 — Handle ambiguous or partial references safely

**Priority:** P2

As a reviewer, I want ambiguous references handled conservatively, so the report helps me investigate without overstating certainty.

**Acceptance scenarios**

- **Given** a plan that references only a short method or class name shared by multiple files, **when** Pass G cannot disambiguate with
  confidence, **then** the finding is marked ambiguous and includes the candidate locations.
- **Given** a plan reference that names a module but not the symbol within it, **when** the module exists, **then** Pass G reports the reference as partially matched rather than invalid.
- **Given** a reference format the extractor cannot classify, **when** Pass G runs, **then** it records the reference as unclassified or skipped rather than failing the analysis.

### US5 — Integrate findings into the existing analysis report

**Priority:** P2

As a consumer of `speckit.analyze`, I want Pass G findings surfaced in the same report format as other passes, so downstream workflows can use them without custom parsing.

**Acceptance scenarios**

- **Given** Pass G finds issues, **when** the pipeline completes, **then** the final report includes a dedicated Pass G section with structured findings.
- **Given** Pass G finds no issues, **when** the pipeline completes, **then** the report still records that Pass G executed successfully.
- **Given** downstream tooling reads the report, **when** Pass G output is present, **then** it can distinguish invalid, ambiguous, skipped, and suggestion-backed findings by type or status.

### US6 — Support future optional remediation workflows

**Priority:** P3

As a maintainer, I want findings to include enough structured metadata to support future auto-remediation or guided correction flows, so this pass can be extended without redesign.

**Acceptance scenarios**

- **Given** a finding for an unresolved symbol, **when** it is serialized, **then** it includes the referenced text, match status, and candidate matches if available.
- **Given** a future workflow wants to rewrite the plan, **when** it reads Pass G output, **then** it can identify which plan location and which suggestion should be applied.
- **Given** future remediation is not implemented yet, **when** Pass G runs now, **then** it still produces stable structured output without performing any edits.

## Edge Cases

1. **Empty or reference-free plans**
   If the plan contains no code references, Pass G should complete successfully and report that no actionable references were found.

2. **Ambiguous short names**
   If a symbol name like `run`, `Config`, or `main` exists in multiple places, Pass G should avoid claiming a single definitive match unless disambiguation evidence is strong.

3. **Generated or protected files**
   References that point to generated files, protected files, or files explicitly excluded by repository conventions should not produce misleading suggestions from files that should not be edited.

4. **Repository contains new code not reflected in index/cache**
   If symbol discovery relies on cached or precomputed data, the pass must either refresh deterministically or clearly report when discovery data is stale.

5. **Intentional new symbols**
   If the plan clearly says "create", "add", "introduce", or equivalent language for a symbol, the absence of that symbol in the
   codebase should not be treated as an error by default.

6. **Partially qualified references**
   If the plan names a file correctly but not the exact symbol within it, or names a symbol without the file path, Pass G should preserve
   that nuance instead of reducing everything to binary valid/invalid results.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001:** The system MUST extract candidate code references from the plan text, including file
  paths and symbol-like identifiers where feasible.
- **FR-002:** The system MUST analyze the current repository contents to build a searchable
  inventory of existing files and symbols relevant to supported languages and project conventions.
- **FR-003:** The system MUST compare extracted references against the repository inventory and
  classify each reference as matched, invalid, ambiguous, partial, skipped, or
  intentional-new-symbol when enough evidence exists.
- **FR-004:** The system MUST record the originating plan text or plan location for each
  extracted reference so findings can be traced back to the source statement.
- **FR-005:** The system MUST flag a reference as invalid when no exact or sufficiently
  confident match exists and no explicit new-symbol intent is detected.
- **FR-006:** The system MUST detect explicit new-symbol intent markers in plan text and
  suppress invalid-reference findings for those intended creations.
  [NEEDS CLARIFICATION: Which phrases or patterns should count as sufficiently explicit markers
  that a missing symbol is intentionally new rather than an invalid reference?]
- **FR-007:** The system MUST support exact matching for file paths, module names, command
  names, class names, function names, and method names where those can be discovered reliably.
- **FR-008:** The system MUST support fuzzy matching for unresolved references and rank
  candidate matches by similarity score.
- **FR-009:** The system MUST mark fuzzy results as suggestions, not exact matches, unless the
  confidence threshold and disambiguation rules are satisfied.
- **FR-010:** The system MUST preserve multiple candidate matches for ambiguous references
  rather than discarding lower-ranked but still plausible candidates.
- **FR-011:** The system MUST exclude or specially classify references that resolve only to
  generated, protected, or otherwise non-editable files according to repository conventions.
- **FR-012:** The system MUST integrate as Pass G in `speckit.analyze` without breaking the
  existing A–F passes or their report structure.
- **FR-013:** The system MUST emit Pass G findings in a structured format that downstream
  phases can consume programmatically.
- **FR-014:** The system MUST include human-readable report text explaining why a reference was
  flagged and, when available, what candidate corrections were found.
- **FR-015:** The system MUST complete successfully even when extraction yields zero references
  or when some references cannot be classified.
- **FR-016:** The system MUST avoid modifying the plan or repository as part of Pass G in the
  initial implementation.

### Non-Functional Requirements

- **NFR-001 (Determinism):** Given the same repository state, configuration, and plan input,
  Pass G MUST produce the same classifications and candidate ordering on repeated runs.
- **NFR-002 (Performance):** Pass G SHOULD add only modest overhead to `speckit.analyze` and
  SHOULD remain practical for normal repository analysis workflows.
- **NFR-003 (Dependency discipline):** The initial implementation SHOULD prefer
  standard-library solutions unless a third-party fuzzy-matching library is clearly justified.
  [NEEDS CLARIFICATION: Is `rapidfuzz` acceptable if `difflib` does not provide adequate
  suggestion quality, or must the implementation remain standard-library-only?]
- **NFR-004 (Report compatibility):** Pass G output MUST fit the existing report integration
  pattern so current consumers do not require a breaking schema change.
- **NFR-005 (Graceful degradation):** When symbol extraction or fuzzy matching is incomplete
  for a language or file type, the pass MUST still return useful findings instead of failing
  the full analysis.

## Success Criteria

1. When run against the real PR #1177 validation baseline, Pass G identifies the known bad plan references that motivated this feature.
2. For the same validation baseline, Pass G does not flag clearly valid references from the plan as invalid.
3. For misspelled or near-match references in the validation baseline, Pass G provides at least one plausible candidate suggestion where such a candidate exists in the repository.
4. For explicit "new symbol" plan statements in test coverage or validation fixtures, Pass G suppresses invalid-reference findings for those intended new symbols.
5. The final `speckit.analyze` output contains a dedicated Pass G section that is both human-readable and machine-consumable.
6. The pass can be rerun on unchanged inputs and produce stable classifications and candidate ordering, demonstrating deterministic behavior.

## Needs Clarification

All open questions have been converted to inline `[NEEDS CLARIFICATION]` markers in the
relevant requirement entries above (FR-006, NFR-003).

## Open Implementation Notes

- Start with exact matching plus conservative fuzzy suggestions.
- Prefer reporting ambiguity over overstating certainty.
- Keep the finding schema extensible enough for optional future remediation flows.

---

*Generated by Copilot SDK (claude-opus-4.6)*
