# Spec: SpecKit pipeline task deduplication in analysis step

**Source Issue**: #1201 (<https://github.com/ayaiayorg/agentic-devtools/issues/1201>)

## Summary

Add a new **Category G** detection pass to `speckit.analyze` that identifies likely duplicate, overlapping, or conflicting tasks
produced during the SpecKit pipeline. The analysis must remain **read-only** in Phase 1: it reports findings and metrics without
mutating task lists. Any remediation or task merging behavior remains explicitly opt-in and deferred to `speckit.tasks`.

This spec expands the original summary into the repository's standard Phase 1 format so later planning and task derivation can proceed reliably.

## Problem Statement

The current analysis pipeline can surface task quality issues across multiple categories, but it does not explicitly detect
when two or more tasks cover the same work, partially overlap in scope, or contradict each other. This creates three problems:

1. Redundant implementation work when duplicate tasks are left unresolved.
2. Reviewer confusion when tasks partially overlap but are not clearly distinguished.
3. Execution risk when conflicting tasks prescribe incompatible outcomes.

Without a dedicated deduplication pass, downstream plan/tasks phases may inherit noisy or contradictory task sets that are harder to execute and validate.

## Goals

- Add a new analysis category (`G`) without changing the behavior of existing categories `A` through `F`.
- Detect likely task duplication based on description similarity, file path overlap, and code section overlap.
- Classify findings into `duplicate`, `overlapping`, and `conflicting`.
- Group related tasks into a single finding rather than emitting only pairwise noise.
- Keep the Phase 1 behavior read-only inside `speckit.analyze`.
- Produce metrics that help users understand how much overlap exists in a task set.

## Non-goals

- Automatically rewriting, deleting, or merging tasks during `speckit.analyze`.
- Changing the existing semantics of categories `A` through `F`.
- Requiring users to resolve deduplication findings before analysis can complete.
- Defining the final remediation UX beyond an opt-in future path in `speckit.tasks`.

## Users and stakeholders

- **Primary user:** AI agent or developer running `speckit.analyze` and reviewing task quality.
- **Secondary user:** Maintainer reviewing generated plan/tasks output for consistency.
- **Downstream consumer:** Later SpecKit phases that depend on clean, non-redundant task data.

## User Scenarios & Testing

### P1 — Detect duplicate or overlapping tasks during analysis

As a user running `speckit.analyze`, I want the pipeline to identify tasks that appear to cover the same work so that I can reduce redundancy before later phases derive implementation plans.

**Acceptance scenarios**

1. **Given** a task list containing two or more tasks with highly similar descriptions and overlapping file or code targets,
   **when** `speckit.analyze` runs, **then** Category G reports a deduplication finding.
2. **Given** a task list with no meaningful overlap, **when** `speckit.analyze` runs, **then** Category G reports no deduplication findings.
3. **Given** existing categories `A` through `F`, **when** Category G is added, **then** those existing passes still run unchanged.

### P1 — Classify overlap severity correctly

As a user reviewing findings, I want the system to distinguish between duplicates, overlaps, and conflicts so that I can prioritize remediation appropriately.

**Acceptance scenarios**

1. **Given** two tasks that describe the same outcome with effectively the same scope, **when** analyzed, **then** the finding is classified as `duplicate` with severity `CRITICAL`.
2. **Given** two or more tasks that share some but not all scope, **when** analyzed, **then** the finding is classified as
   `overlapping` with severity `CRITICAL` when at least 2 of the 3 comparison dimensions match strongly, or `HIGH` when
   exactly 1 dimension matches strongly and the tasks are neither duplicates nor conflicts
   `[NEEDS CLARIFICATION: source issue proposes all overlapping findings as CRITICAL — see Open Questions §3]`.
3. **Given** two or more tasks that prescribe incompatible or contradictory actions, **when** analyzed, **then** the finding is classified as `conflicting` with severity `CRITICAL`.
4. **Given** the three overlap types, **when** results are presented, **then** each type maps to the explicit severity
   defined above so that analyze-step behavior is deterministic and testable.

### P2 — Report grouped findings and useful metrics

As a user reviewing analysis output, I want related overlapping tasks grouped into a single finding and summarized with metrics so that the report is concise and actionable.

**Acceptance scenarios**

1. **Given** three tasks that all overlap the same scope, **when** analyzed, **then** the system emits one grouped finding rather than three separate pairwise findings.
2. **Given** one or more grouped findings, **when** output is rendered, **then** the report includes the participating task identifiers and the basis for the grouping.
3. **Given** a task set with overlap findings, **when** analysis completes, **then** summary metrics show counts by overlap type and overall finding count.
4. **Given** a grouped finding containing tasks with mixed severity levels, **when** the grouped finding severity is
   determined, **then** it equals the highest severity present in the group (`CRITICAL` overrides `HIGH`).

### P3 — Support future opt-in remediation in task processing

As a maintainer, I want the analysis output to be structured so that `speckit.tasks` can later offer opt-in deduplication or merge behavior without changing the read-only contract of `speckit.analyze`.

**Acceptance scenarios**

1. **Given** Category G findings already produced by analysis, **when** a future `speckit.tasks` deduplication flag is
   introduced, **then** it can consume structured findings without requiring analyze-time mutation.
2. **Given** the current Phase 1 scope, **when** `speckit.analyze` runs, **then** it performs detection only and does not auto-merge tasks.

## Requirements

### Functional requirements

#### FR-001: Add Category G to analysis passes

- The analyze agent MUST add a new detection category named **G**.
- Categories `A` through `F` MUST remain present and behaviorally unchanged.
- Category G MUST run as part of the standard analysis flow.

#### FR-002: Compare tasks across three dimensions

Category G MUST compare candidate tasks using these dimensions:

- **Description similarity** — semantic or textual similarity between task descriptions.
- **File path overlap** — shared or intersecting file or directory scope.
- **Code section overlap** — shared function/class/module/section targets where available.

A finding MAY be supported by one or more dimensions; not every dimension MUST be present for every finding.

#### FR-003: Classify findings into three overlap types with explicit severity

Category G MUST classify findings as:

- `duplicate` — tasks are materially redundant and appear to request the same work. **Severity: `CRITICAL`**.
- `overlapping` — tasks share meaningful scope but are not fully redundant. **Severity: `CRITICAL`** when at least 2 of the 3
  comparison dimensions match strongly `[NEEDS CLARIFICATION: define "match strongly" thresholds — see Open Questions §2]`;
  **`HIGH`** when exactly 1 dimension matches strongly and the tasks are neither duplicates nor conflicts
  `[NEEDS CLARIFICATION: the source issue (#1201) proposes all overlap types as CRITICAL; this HIGH downgrade for
  single-dimension overlap is a deviation — Phase 2 SHOULD confirm whether to align all overlapping findings to CRITICAL
  or keep the graduated severity — see Open Questions §3]`.
- `conflicting` — tasks prescribe contradictory or incompatible outcomes. **Severity: `CRITICAL`**.

Severity classification MUST be derived only from the comparison dimensions plus the overlap type so that analyze-step results are deterministic and testable.

#### FR-004: Group related tasks into a single finding

- When more than two tasks belong to the same overlap cluster, Category G MUST emit one grouped finding for that cluster.
- The grouped finding MUST identify all implicated tasks.
- The grouped finding MUST avoid unnecessary pairwise duplication in the reported output.
- The grouped finding severity is the highest severity present in the group (`CRITICAL` overrides `HIGH`).

#### FR-005: Keep analysis read-only

- `speckit.analyze` MUST NOT modify, delete, merge, or rewrite tasks as part of Category G detection.
- Remediation MUST remain outside the analysis step.
- Any future deduplication action in `speckit.tasks` MUST be opt-in via an explicit flag.

#### FR-006: Produce actionable output

Each Category G finding MUST include, at minimum:

- overlap type
- severity
- implicated task identifiers
- concise rationale describing which comparison dimensions triggered the finding

#### FR-007: Produce metrics

The analysis output MUST include summary metrics for Category G, including:

- total number of deduplication findings
- counts by overlap type (`duplicate`, `overlapping`, `conflicting`)
- number of grouped findings involving more than two tasks

### Non-functional requirements

#### NFR-001: Keep output understandable

The new analysis MUST keep output understandable and not overwhelm the user with pairwise noise.

#### NFR-002: Ensure deterministic behavior

The feature SHOULD be deterministic for the same task input and comparison configuration.

#### NFR-003: Preserve backward compatibility

The feature MUST preserve backward compatibility for workflows that already depend on categories `A` through `F`.

#### NFR-004: Support future extensibility

The feature SHOULD be extensible so future remediation logic can consume the structured findings.

## Edge cases

- Two tasks have very similar descriptions but different file scopes; the system should avoid over-classifying them as duplicates without additional supporting evidence.
- Two tasks target the same file but clearly different code sections; the system should favor `overlapping` or no finding over `duplicate` where appropriate.
- A cluster contains three or more tasks with mixed relationships; the grouped finding should represent the dominant or most severe issue clearly.
- One task is broad and another is narrow but nested within the same scope; the system should treat this as overlap unless the tasks are materially redundant.
- Tasks may omit file paths or code sections; Category G should still work using available evidence rather than failing outright.
- Contradictory verbs or expected outcomes in otherwise similar tasks should be surfaced as `conflicting`, not `duplicate`.

## Success Criteria

The spec is considered successful when:

1. `speckit.analyze` includes Category G alongside existing categories `A` through `F`.
2. The system can distinguish `duplicate`, `overlapping`, and `conflicting` findings.
3. Related multi-task overlap is emitted as a single grouped finding.
4. Analysis remains read-only and does not merge or rewrite tasks.
5. Output includes both actionable findings and summary metrics.
6. Later phases can derive plan/tasks work items from this document without needing to infer missing requirements.

## Assumptions and constraints

- Existing analyze-pass architecture can accommodate an additional category without redesign.
- Task comparison can rely on the task data already available during analysis.
- Future remediation belongs to `speckit.tasks`, not `speckit.analyze`.
- This spec intentionally does not lock in a specific algorithm, only the required behavior and outputs.

## Open questions

1. **Similarity threshold behavior:** Should the similarity threshold be configurable, or should the implementation use a fixed threshold initially?
   - Current status: **Open clarification**
   - Recommendation for implementation planning: start with a fixed threshold unless a strong use case for configurability already exists.
2. **"Match strongly" definition:** FR-003 references dimensions that "match strongly" to determine
   `overlapping` severity (`CRITICAL` vs `HIGH`), but the spec does not yet define explicit thresholds
   or criteria for what constitutes a strong match for each dimension (description similarity,
   file path overlap, code section overlap). Phase 2 planning SHOULD resolve this by defining
   testable thresholds or heuristics for each dimension.
   - Current status: **`[NEEDS CLARIFICATION]`**
   - Recommendation: defer concrete thresholds to Phase 2 planning where implementation context
     is available, but ensure each dimension has a documented criterion before coding begins.
3. **Overlapping severity alignment with source issue:** The source issue (#1201) proposes that
   duplicate/overlapping tasks be reported as CRITICAL findings. This spec introduces a `HIGH`
   severity path for `overlapping` findings when only 1 comparison dimension matches strongly.
   Phase 2 SHOULD decide whether to align all `overlapping` findings to `CRITICAL` (matching the
   source issue) or keep the graduated `CRITICAL`/`HIGH` severity model.
   - Current status: **`[NEEDS CLARIFICATION]`**
   - Recommendation: resolve during Phase 2 planning based on real-world task overlap data.

## Out of scope for this phase

- Auto-merging duplicate tasks
- Interactive conflict resolution UX
- Reordering tasks based on deduplication results
- Blocking pipeline execution solely because low-severity overlap exists

## Notes for downstream phases

Later planning/tasks phases should derive work from:

- adding Category G to the analyze pass sequence
- implementing three-dimension comparison logic
- defining overlap classification and severity mapping
- implementing grouped finding generation
- exposing Category G metrics in analysis output
- preserving read-only behavior in `speckit.analyze`
- reserving opt-in remediation for future `speckit.tasks` work

---

*Traceability: derived for issue [#1201](https://github.com/ayaiayorg/agentic-devtools/issues/1201). Replaces the previous bullet-only summary with a Phase 1 specification suitable for planning and task generation.*
