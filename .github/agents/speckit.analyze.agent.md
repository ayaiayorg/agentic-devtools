---
description: Perform a non-destructive cross-artifact consistency and quality analysis across spec.md, plan.md, and tasks.md after task generation.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Identify inconsistencies, duplications, ambiguities, and underspecified items across the three core artifacts (`spec.md`, `plan.md`, `tasks.md`) before implementation. This command MUST run only after `/speckit.tasks` has successfully produced a complete `tasks.md`.

## Operating Constraints

**STRICTLY READ-ONLY**: Do **not** modify any files. Output a structured analysis report. Offer an optional remediation plan (user must explicitly approve before any follow-up editing commands would be invoked manually).

**Constitution Authority**: The project constitution (`.specify/memory/constitution.md`) is **non-negotiable** within this analysis scope. Constitution conflicts are automatically CRITICAL and require adjustment of the spec, plan, or tasks—not dilution, reinterpretation, or silent ignoring of the principle. If a principle itself needs to change, that must occur in a separate, explicit constitution update outside `/speckit.analyze`.

## Execution Steps

### 1. Initialize Analysis Context

Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` once from repo root and parse JSON for FEATURE_DIR and AVAILABLE_DOCS. Derive absolute paths:

- SPEC = FEATURE_DIR/spec.md
- PLAN = FEATURE_DIR/plan.md
- TASKS = FEATURE_DIR/tasks.md

Abort with an error message if any required file is missing (instruct the user to run missing prerequisite command).
For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

### 2. Load Artifacts (Progressive Disclosure)

Load only the minimal necessary context from each artifact:

**From spec.md:**

- Overview/Context
- Functional Requirements
- Non-Functional Requirements
- User Stories
- Edge Cases (if present)

**From plan.md:**

- Architecture/stack choices
- Data Model references
- Phases
- Technical constraints

**From tasks.md:**

- Task IDs
- Descriptions
- Phase grouping
- Parallel markers [P]
- Referenced file paths

**From fr-coverage.json (if present in FEATURE_DIR):**

- Load `FEATURE_DIR/fr-coverage.json` if it exists
- This file contains deterministic FR coverage data produced by `agdt-speckit-validate-frs`
- The data is pre-validated and should be reported as-is in the Coverage Summary section
- Do **not** re-evaluate FR coverage — use these results directly
- Include the `covered` and `uncovered` FR lists in the Coverage Gaps detection pass

**From constitution:**

- Load `.specify/memory/constitution.md` for principle validation
- Load `.specify/memory/markdown-rules.md` and apply it to all fenced code blocks in generated output.

### 3. Build Semantic Models

Create internal representations (do not include raw artifacts in output):

- **Requirements inventory**: Each functional + non-functional requirement with a stable key (derive slug based on imperative phrase; e.g., "User can upload file" → `user-can-upload-file`)
- **User story/action inventory**: Discrete user actions with acceptance criteria
- **Task coverage mapping**: Map each task to one or more requirements or stories (inference by keyword / explicit reference patterns like IDs or key phrases)
- **Constitution rule set**: Extract principle names and MUST/SHOULD normative statements

### 4. Detection Passes (Token-Efficient Analysis)

Focus on high-signal findings. Limit to 50 findings total; aggregate remainder in overflow summary.

**Scope distinction**: Category A detects duplicate *requirements* (in spec.md). Category G detects duplicate *tasks* (in tasks.md). These are complementary passes operating on different artifact types.

#### A. Duplication Detection

- Identify near-duplicate requirements
- Mark lower-quality phrasing for consolidation

#### B. Ambiguity Detection

- Flag vague adjectives (fast, scalable, secure, intuitive, robust) lacking measurable criteria
- Flag unresolved placeholders (TODO, TKTK, ???, `<placeholder>`, etc.)

#### C. Underspecification

- Requirements with verbs but missing object or measurable outcome
- User stories missing acceptance criteria alignment
- Tasks referencing files or components not defined in spec/plan

#### D. Constitution Alignment

- Any requirement or plan element conflicting with a MUST principle
- Missing mandated sections or quality gates from constitution

#### E. Coverage Gaps

- Requirements with zero associated tasks
- Tasks with no mapped requirement/story
- Non-functional requirements not reflected in tasks (e.g., performance, security)
- **FR coverage data**: If `fr-coverage.json` was loaded, use its deterministic
  `covered`/`uncovered` lists as the authoritative source for FR-to-task coverage.
  Report any `uncovered` FRs as coverage gap findings (severity depends on context).

#### F. Inconsistency

- Terminology drift (same concept named differently across files)
- Data entities referenced in plan but absent in spec (or vice versa)
- Task ordering contradictions (e.g., integration tasks before foundational setup tasks without dependency note)
- Conflicting requirements (e.g., one requires Next.js while other specifies Vue)
- Missing Phase Mapping table: when plan and tasks phase structures differ (in numbering, count, or organizational scheme, e.g., domain-driven vs. story-driven) but `tasks.md` lacks a "Phase Mapping: Plan → Tasks" table — severity HIGH
- Stale Phase Mapping references: when the Phase Mapping table in `tasks.md` references plan phases not present in `plan.md` — severity MEDIUM

#### G. Task Deduplication

Detect duplicate, overlapping, or conflicting tasks in `tasks.md`. This pass operates on *tasks* (not requirements — that is Category A's scope).

**Comparison Dimensions** — Evaluate each pair/cluster of tasks across three independent dimensions:

1. **Description similarity** — Do the tasks express substantially the same intent or outcome? A strong match means the tasks would produce the same deliverable if implemented independently; mere keyword overlap is insufficient.
2. **File path overlap** — Do the tasks target a majority (≥50%) of the same files or directories? A strong match means most of the modified files are shared.
3. **Code section overlap** — Do the tasks name the same function, class, method, or module-level section? A strong match means both tasks explicitly reference the same code symbol or section heading.

Each dimension is evaluated independently. A finding MAY be supported by one or more dimensions.

**Classification Rules** — Classify each finding as one of:

| Overlap Type | Definition | Severity |
|--------------|-----------|----------|
| `duplicate` | Tasks are materially redundant — same work, same scope | CRITICAL |
| `conflicting` | Tasks prescribe contradictory or incompatible outcomes for the same scope | CRITICAL |
| `overlapping` (≥2 dimensions match strongly) | Tasks share meaningful scope across multiple dimensions but are not fully redundant | CRITICAL |
| `overlapping` (exactly 1 dimension matches strongly) | Tasks share scope in a single dimension only | HIGH |

**Severity Decision Tree**:

1. Is the cluster a duplicate (same work, same scope)? → CRITICAL
2. Is the cluster conflicting (contradictory outcomes)? → CRITICAL
3. Is the cluster overlapping with ≥2 dimensions matching strongly? → CRITICAL
4. Is the cluster overlapping with exactly 1 dimension? → HIGH

**Grouping Rules** — Use transitive closure to identify overlap clusters:

- If task A overlaps task B, and task B overlaps task C, all three form one cluster
- Emit one finding per cluster (not pairwise)
- The grouped finding severity is the highest severity present in the cluster

**Structured Output Contract** — Each Category G finding MUST include:

- `overlap_type`: one of `duplicate`, `overlapping`, `conflicting`
- `severity`: one of `CRITICAL`, `HIGH`
- `task_ids`: array of implicated task identifiers
- `dimensions`: array of which dimensions triggered (from: `description`, `file_path`, `code_section`)
- `rationale`: concise explanation (max 500 characters)

**Edge Case Handling**:

- Similar descriptions but different file scopes → at most `overlapping` / `HIGH` (single dimension)
- Same file but clearly different code sections → favor `overlapping` or no finding over `duplicate`
- Mixed-relationship clusters (3+ tasks) → use highest severity present; represent the dominant issue
- Broad-vs-narrow scope (one task nests within another) → treat as `overlapping` unless materially redundant
- Missing dimensions (task lacks file paths or code section info) → evaluate only available dimensions; do not infer missing data
- Contradictory verbs (one task adds, another removes same thing) → classify as `conflicting`
- Single-dimension-only evidence → maximum severity is `HIGH`

**Read-Only Constraint**: Category G MUST NOT modify, delete, merge, or rewrite tasks. It reports findings only. Any future deduplication action belongs in `speckit.tasks` (opt-in, not part of analysis).

**Required Structured JSON Block**: After the findings table, emit a `### Category G Structured Findings` section containing a JSON array of finding objects. This section is **required** when Category G findings exist (ensures the Structured Output Contract fields are always machine-parseable):

```json
[
  {
    "id": "F-01",
    "overlap_type": "duplicate",
    "severity": "CRITICAL",
    "task_ids": ["T001", "T002"],
    "dimensions": ["description", "file_path"],
    "rationale": "Tasks T001 and T002 both implement user authentication with identical file targets and matching descriptions."
  }
]
```

> **Output format**: The JSON array in the report MUST be emitted as **raw JSON without Markdown code fences**. The fenced block above is illustrative only (showing the schema). In actual output, emit the JSON directly so downstream parsers can extract it without stripping fence markers.

### 5. Severity Assignment

Use this heuristic to prioritize findings:

- **CRITICAL**: Violates constitution MUST, missing core spec artifact, or requirement with zero coverage that blocks baseline functionality; task deduplication finding — duplicate tasks, conflicting tasks, or multi-dimension overlap (≥2 dimensions)
- **HIGH**: Duplicate or conflicting requirement, ambiguous security/performance attribute, untestable acceptance criterion; task deduplication finding — single-dimension overlap
- **MEDIUM**: Terminology drift, missing non-functional task coverage, underspecified edge case
- **LOW**: Style/wording improvements, minor redundancy not affecting execution order

### 6. Produce Compact Analysis Report

Output a Markdown report (no file writes) with the following structure:

## Specification Analysis Report

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | Duplication | HIGH | spec.md:L120-134 | Two similar requirements ... | Merge phrasing; keep clearer version |

(Add one row per finding; generate sequential IDs in `F-NN` format — where F = Finding — shared across all categories.)

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|

**Constitution Alignment Issues:** (if any)

**Unmapped Tasks:** (if any)

**Metrics:**

- Total Requirements
- Total Tasks
- Coverage % (requirements with >=1 task)
- Ambiguity Count
- Requirement Duplication Count (Category A)
- Critical Issues Count
- Task Deduplication Finding Count
- Task Deduplication by Type (duplicate / overlapping / conflicting)
- Multi-Task Group Count (findings involving >2 tasks)

### 7. Provide Next Actions

At end of report, output a concise Next Actions block:

- If CRITICAL issues exist: Recommend resolving before `/speckit.implement`
- If only LOW/MEDIUM: User may proceed, but provide improvement suggestions
- Provide explicit command suggestions: e.g., "Run /speckit.specify with refinement", "Run /speckit.plan to adjust architecture", "Manually edit tasks.md to add coverage for 'performance-metrics'"

### 8. Offer Remediation

Ask the user: "Would you like me to suggest concrete remediation edits for the top N issues?" (Do NOT apply them automatically.)

## Operating Principles

### Context Efficiency

- **Minimal high-signal tokens**: Focus on actionable findings, not exhaustive documentation
- **Progressive disclosure**: Load artifacts incrementally; don't dump all content into analysis
- **Token-efficient output**: Limit findings table to 50 rows; summarize overflow
- **Deterministic results**: Rerunning without changes should produce consistent IDs and counts

### Analysis Guidelines

- **NEVER modify files** (this is read-only analysis)
- **NEVER hallucinate missing sections** (if absent, report them accurately)
- **Prioritize constitution violations** (these are always CRITICAL)
- **Use examples over exhaustive rules** (cite specific instances, not generic patterns)
- **Report zero issues gracefully** (emit success report with coverage statistics)

## Context

$ARGUMENTS
