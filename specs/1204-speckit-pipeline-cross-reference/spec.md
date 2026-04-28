# Feature Specification: SpecKit pipeline cross-reference plan code references against actual codebase

**Feature Branch**: `speckit/1204/phase-2-clarify`
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

## Clarifications

### Session 2026-04-27

- Q: Which phrases or patterns should count as sufficiently explicit markers that a missing symbol is intentionally new rather than an invalid reference (FR-006)? → A: The following case-insensitive
  verb phrases preceding or surrounding a symbol reference constitute new-symbol intent markers:
  "create", "add", "introduce", "implement", "define", "scaffold", "generate", "write", "build",
  "set up", "register", "wire up". These must appear in the same plan step or sentence as the symbol reference. Noun phrases such as "new file", "new class", "new function", "new module",
  "new command" adjacent to a symbol also qualify. The marker list MUST be defined as a named constant with a default value, making it straightforward to update in a single location.
- Q: Is `rapidfuzz` acceptable as a third-party dependency if `difflib.SequenceMatcher` does not provide adequate suggestion quality, or must the implementation remain standard-library-only (NFR-003)?
  → A: The initial implementation MUST use `difflib.SequenceMatcher` from the standard library. If measurable evidence from the PR #1177 validation baseline demonstrates that `difflib` produces
  materially worse suggestion quality (e.g., fails to surface the correct candidate in the top 3 for ≥ 30% of known misspelled references), then `rapidfuzz` MAY be introduced as an optional dependency
  in a follow-up PR with its own justification. Pass G MUST NOT require `rapidfuzz` at launch.
- Q: What is the concrete similarity threshold for fuzzy matching that determines whether a candidate is surfaced as a suggestion versus discarded (FR-008, FR-009)? → A: A normalized similarity score
  of ≥ 0.75 (on a 0–1 scale as produced by `difflib.SequenceMatcher.ratio()`) is required to surface a candidate. Candidates scoring ≥ 0.90 with no competing candidates within 0.05 of that score MAY
  be classified as high-confidence matches. All three parameters (the suggestion threshold, the high-confidence threshold, and the disambiguation margin) MUST be defined as named constants so they
  can be tuned in a single location.
- Q: Which languages and file types are in scope for symbol extraction in the initial implementation (FR-002, FR-007)? → A: The initial implementation MUST support Python (`.py` files: module paths,
  class names, function/method names, CLI entry points from `pyproject.toml`). Other languages are out of scope for the initial release but the extraction interface MUST be designed so additional
  language extractors can be added without modifying Pass G core logic. File path references (any extension) MUST always be matched regardless of language support.
- Q: What is the concrete performance budget for "modest overhead" (NFR-002)? → A: Pass G SHOULD complete within 30 seconds for a repository containing up to 5,000 files and a plan with up to 200
  extracted references, measured on the CI runner hardware. If Pass G exceeds this budget, it MUST still complete (no timeout kill) but SHOULD log a warning indicating the elapsed time. This threshold
  MUST be defined as a named constant.

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
- The initial implementation targets Python repositories; the extraction interface is designed for multi-language extensibility.
- The project does not currently use `rapidfuzz`; the standard library `difflib` is the baseline fuzzy-matching engine.

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

- **Given** a plan reference that differs slightly from an existing symbol name, **when** the `difflib.SequenceMatcher.ratio()` similarity score is ≥ 0.75 for at least one candidate, **then** the
  finding includes one or more ranked candidate matches.
- **Given** a plan reference with no candidates scoring ≥ 0.75, **when** Pass G runs, **then** the finding states that no reliable suggestion was found instead of inventing a weak match.
- **Given** multiple candidates scoring within 0.05 of each other and all ≥ 0.75, **when** Pass G runs, **then** the finding is marked ambiguous rather than presenting one guess as definitive.

### US3 — Respect explicit "new symbol" intent

**Priority:** P1

As a developer authoring a plan, I want references that are clearly described as new code to avoid being flagged as invalid, so the analyzer does not produce noisy false positives.

**Acceptance scenarios**

- **Given** a plan step that uses a recognized new-symbol intent marker (e.g., "create", "add", "introduce", "implement", "define", "scaffold", "generate", "write", "build", "set up",
  "new file", "new class", "new function", "new module", "new command") for a symbol, **when** that symbol is not present
  in the repository, **then** Pass G does not emit an invalid-reference finding for that symbol.
- **Given** a plan that references a missing symbol without any recognized creation intent markers, **when** Pass G runs, **then** the symbol is still eligible to be flagged.
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

- **Given** a finding for an unresolved symbol, **when** it is serialized, **then** it includes the referenced text, match status, candidate matches (with similarity scores) if available, and the
  originating plan location.
- **Given** a future workflow wants to rewrite the plan, **when** it reads Pass G output, **then** it can identify which plan location and which suggestion should be applied.
- **Given** future remediation is not implemented yet, **when** Pass G runs now, **then** it still produces stable structured output without performing any edits.

## Edge Cases

1. **Empty or reference-free plans**
   If the plan contains no code references, Pass G should complete successfully and report that no actionable references were found.

2. **Ambiguous short names**
   If a symbol name like `run`, `Config`, or `main` exists in multiple places, Pass G should avoid claiming a single definitive match unless disambiguation evidence is strong (e.g., a single candidate
   scores ≥ 0.90 with no competitor within 0.05).

3. **Generated or protected files**
   References that point to generated files (e.g., `_version.py`), protected files, or files explicitly excluded by repository conventions (e.g., `.gitignore` patterns, `__pycache__`) should not
   produce misleading suggestions from files that should not be edited.

4. **Repository contains new code not reflected in index/cache**
   If symbol discovery relies on cached or precomputed data, the pass must either refresh deterministically or clearly report when discovery data is stale. The initial implementation SHOULD perform a
   fresh filesystem and AST scan each run to avoid stale-cache issues.

5. **Intentional new symbols**
   If the plan uses a recognized new-symbol intent marker (from the named marker constant: "create", "add", "introduce", "implement", "define", "scaffold", "generate", "write", "build", "set up",
   or noun phrases like "new file", "new class", etc.) for a symbol, the absence of that symbol in the
   codebase should not be treated as an error by default.

6. **Partially qualified references**
   If the plan names a file correctly but not the exact symbol within it, or names a symbol without the file path, Pass G should preserve
   that nuance instead of reducing everything to binary valid/invalid results.

7. **Non-Python file references**
   If the plan references non-Python files (e.g., `.md`, `.toml`, `.yml`, `.json`), file path matching MUST still apply even though symbol extraction within those files is out of scope for the initial
   implementation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001:** The system MUST extract candidate code references from the plan text, including file
  paths and symbol-like identifiers where feasible.
- **FR-002:** The system MUST analyze the current repository contents to build a searchable
  inventory of existing files and Python symbols (module paths, class names, function/method names, CLI entry points from `pyproject.toml`). The inventory interface MUST be designed so additional
  language extractors can be added without modifying Pass G core logic.
- **FR-003:** The system MUST compare extracted references against the repository inventory and
  classify each reference as matched, invalid, ambiguous, partial, skipped, or
  intentional-new-symbol when enough evidence exists.
- **FR-004:** The system MUST record the originating plan text or plan location for each
  extracted reference so findings can be traced back to the source statement.
- **FR-005:** The system MUST flag a reference as invalid when no exact match exists
  and the best fuzzy candidate (if any) scores below the confidence threshold
  (similarity score < 0.75), provided no explicit new-symbol intent is detected.
- **FR-006:** The system MUST detect explicit new-symbol intent markers in plan text and
  suppress invalid-reference findings for those intended creations.
  The following case-insensitive patterns constitute recognized markers: verb phrases
  ("create", "add", "introduce", "implement", "define", "scaffold", "generate", "write",
  "build", "set up", "register", "wire up") and noun phrases ("new file", "new class",
  "new function", "new module", "new command") appearing in the same plan step or sentence
  as the symbol reference. The marker list MUST be defined as a named constant with a default value,
  making it straightforward to update in a single location.
- **FR-007:** The system MUST support exact matching for file paths, module names, command
  names, class names, function names, and method names where those can be discovered reliably.
  The initial implementation MUST support Python; file path matching MUST apply to all file types.
- **FR-008:** The system MUST support fuzzy matching for unresolved references using
  `difflib.SequenceMatcher` and rank candidate matches by similarity score. A minimum
  normalized similarity score of 0.75 is required to surface a candidate.
- **FR-009:** The system MUST mark fuzzy results as suggestions, not exact matches, unless the
  similarity score is ≥ 0.90 and no competing candidate scores within 0.05, in which case the
  result MAY be classified as a high-confidence match.
- **FR-010:** The system MUST preserve multiple candidate matches for ambiguous references
  rather than discarding lower-ranked but still plausible candidates (all candidates scoring ≥ 0.75).
- **FR-011:** The system MUST exclude or specially classify references that resolve only to
  generated files (e.g., `_version.py`), protected files, or otherwise non-editable files according to repository conventions (e.g., `.gitignore` patterns, `__pycache__` directories).
- **FR-012:** The system MUST integrate as Pass G in `speckit.analyze` without breaking the
  existing A–F passes or their report structure.
- **FR-013:** The system MUST emit Pass G findings in a structured format that downstream
  phases can consume programmatically.
- **FR-014:** The system MUST include human-readable report text explaining why a reference was
  flagged and, when available, what candidate corrections were found (including similarity scores).
- **FR-015:** The system MUST complete successfully even when extraction yields zero references
  or when some references cannot be classified.
- **FR-016:** The system MUST avoid modifying the plan or repository as part of Pass G in the
  initial implementation.

### Non-Functional Requirements

- **NFR-001 (Determinism):** Given the same repository state, configuration, and plan input,
  Pass G MUST produce the same classifications and candidate ordering on repeated runs.
- **NFR-002 (Performance):** Pass G SHOULD complete within 30 seconds for a repository containing
  up to 5,000 files and a plan with up to 200 extracted references, measured on CI runner
  hardware. If Pass G exceeds this budget, it MUST still complete (no timeout kill) but SHOULD
  log a warning indicating the elapsed time. The threshold MUST be defined as a named constant.
- **NFR-003 (Dependency discipline):** The initial implementation MUST use
  `difflib.SequenceMatcher` from the Python standard library for fuzzy matching. `rapidfuzz`
  MAY be introduced as an optional dependency in a follow-up PR only if measurable evidence
  from the PR #1177 validation baseline demonstrates that `difflib` fails to surface the correct
  candidate in the top 3 for ≥ 30% of known misspelled references. Pass G MUST NOT require
  `rapidfuzz` at launch.
- **NFR-004 (Report compatibility):** Pass G output MUST fit the existing report integration
  pattern so current consumers do not require a breaking schema change.
- **NFR-005 (Graceful degradation):** When symbol extraction or fuzzy matching is incomplete
  for a language or file type, the pass MUST still return useful findings instead of failing
  the full analysis.

## Success Criteria

1. When run against the real PR #1177 validation baseline, Pass G identifies the known bad plan references that motivated this feature.
2. For the same validation baseline, Pass G does not flag clearly valid references from the plan as invalid.
3. For misspelled or near-match references in the validation baseline, Pass G provides at least one plausible candidate suggestion (scoring ≥ 0.75) where such a candidate exists in the repository.
4. For explicit "new symbol" plan statements using recognized intent markers in test coverage or validation fixtures, Pass G suppresses invalid-reference findings for those intended new symbols.
5. The final `speckit.analyze` output contains a dedicated Pass G section that is both human-readable and machine-consumable.
6. The pass can be rerun on unchanged inputs and produce stable classifications and candidate ordering, demonstrating deterministic behavior.
7. Pass G completes within 30 seconds for the project's own repository (approximately 2,000+ files).

## Needs Clarification

All previously open questions have been resolved in the Clarifications section above. No remaining
open questions.

## Open Implementation Notes

- Start with exact matching plus conservative fuzzy suggestions using `difflib.SequenceMatcher`.
- Define similarity thresholds (0.75 minimum, 0.90 high-confidence) and disambiguation margin (0.05) as named constants.
- Define new-symbol intent markers as a named constant list with a default value.
- Define performance warning threshold (30 seconds) as a named constant.
- Prefer reporting ambiguity over overstating certainty.
- Keep the finding schema extensible enough for optional future remediation flows.
- Design the symbol extraction interface to support pluggable per-language extractors; ship Python support only in the initial release.
- Use fresh filesystem and AST scanning per run to avoid stale-cache issues in the initial implementation.

---

*Generated by Copilot SDK (claude-opus-4.6)*
