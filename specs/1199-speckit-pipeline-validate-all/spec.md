# Spec: SpecKit pipeline: Validate all spec FRs have corresponding tasks

**Source Issue**: #1199
(<https://github.com/ayaiayorg/agentic-devtools/issues/1199>)
**Status**: Draft

## 1. Summary

Add a deterministic validation step to the SpecKit pipeline that cross-references
functional requirements (FR-###) in `spec.md` with task content in `tasks.md`.
The validation runs after the tasks phase and **blocks PR creation** when any FR
lacks corresponding task coverage. This prevents incomplete implementations from
reaching review, as identified in PR #1178.

## 2. Problem Statement

In PR #1178, the analysis report found that the core feature — using the issue
number as the directory prefix — was completely missing from the generated tasks.
The tasks implemented collision detection but not the primary feature itself. The
analysis step catches such gaps, but the PR was still created and reached review.
An implementer following those tasks would produce an incomplete implementation.

A deterministic, pre-PR-creation validation gate is needed so that missing FR
coverage is caught **before** a tasks PR is created, not after.

## 3. Scope

**In scope:**

- Deterministic extraction of FR identifiers from `spec.md`
- Text-search-based coverage check of each FR in `tasks.md`
- Pipeline integration that blocks PR creation when coverage is incomplete
- Auto-retry of task generation with explicit feedback about uncovered FRs
- Standalone CLI command (`agdt-speckit-validate-frs`) for local validation with
  `--json` output support, registered as both a `[project.scripts]` entry point in
  `pyproject.toml` pointing to `agentic_devtools.cli.runner:run_as_script` (the
  dispatch pattern used by `agdt-speckit-*` commands) **and** a `COMMAND_MAP`
  entry in `agentic_devtools/cli/runner.py` mapping to the actual implementation
  function (required for `agdt-speckit-*` commands routed through `run_as_script`)
- Enrichment of the analysis report with deterministic FR coverage data

**Out of scope:**

- LLM-based semantic matching of FRs to tasks (validation is deterministic)
- Modifying the spec or tasks file formats
- Validating NFR coverage (NFRs are informational, not blocking)
- Modifying the analysis phase logic beyond injecting coverage data

## 4. Assumptions

1. Functional requirements in `spec.md` follow the `FR-NNN` naming convention
   (e.g., `FR-001`, `FR-002`). The recommended canonical format is three-digit
   zero-padded (e.g., `FR-001`), but the validator accepts any digit count.
2. Task coverage is determined by text search: an FR is covered if its identifier
   (e.g., `FR-001`) appears in `tasks.md`.
3. The validation is deterministic (regex-based extraction + text search), not
   LLM-driven, so coverage gaps cannot be silently missed.
4. The default retry count for auto-retry of task generation is 2 (configurable).
5. FR identifiers in `spec.md` and `tasks.md` should use a consistent format.
   The validator matches identifiers as-written without normalization, so
   `FR-1` and `FR-001` are treated as distinct identifiers. Spec authors should
   use the canonical three-digit zero-padded format to avoid false negatives
   from padding mismatches.

## 5. Key Design Decision

Validation is *deterministic* — regex-based FR extraction combined with text
search in the tasks file. This guarantees that coverage gaps are always detected
regardless of LLM behavior, making the gate fully reliable as a CI check.

## 6. User Stories

### US1. Block incomplete task lists before PR creation (Priority: P1)

As a spec author, I want the SpecKit pipeline to validate that every FR in
`spec.md` has at least one corresponding reference in `tasks.md` before creating
the tasks PR, so that incomplete task lists never reach review.

**Acceptance Scenarios:**

1. **Given** a `spec.md` with FR-001 through FR-005 and a `tasks.md` that
   references all five FRs, **When** the validation step runs, **Then** it
   passes and the pipeline proceeds to create the PR.

2. **Given** a `spec.md` with FR-001 through FR-005 and a `tasks.md` that only
   references FR-001, FR-002, and FR-004, **When** the validation step runs,
   **Then** it fails, listing FR-003 and FR-005 as uncovered, and the PR is
   **not** created.

3. **Given** a `spec.md` with no FR-### identifiers (malformed spec), **When**
   the validation step runs, **Then** it reports a warning that no FRs were
   found and does not block (graceful degradation).

4. **Given** a validation failure, **When** the pipeline reports the failure,
   **Then** the output lists each uncovered FR identifier so the task generation
   step can be retried with explicit feedback.

### US2. Auto-retry task generation on validation failure (Priority: P2)

As a pipeline operator, I want the pipeline to automatically retry task
generation with explicit feedback about uncovered FRs, so that transient LLM
omissions are corrected without manual intervention.

**Acceptance Scenarios:**

1. **Given** the validation step fails with uncovered FRs, **When** the retry
   count is below the configured maximum (default: 2), **Then** the pipeline
   re-invokes task generation with a prompt that explicitly lists the uncovered
   FR identifiers.

2. **Given** the validation step fails and the retry count has reached the
   maximum, **When** the pipeline evaluates whether to retry, **Then** it stops
   retrying and fails the pipeline with a clear error message listing all
   uncovered FRs.

3. **Given** the retry prompt includes uncovered FRs, **When** the LLM
   generates new tasks, **Then** the validation step re-runs on the updated
   `tasks.md` and passes if all FRs are now covered.

### US3. Standalone CLI command for local validation (Priority: P2)

As a developer, I want a standalone CLI command to validate FR coverage locally,
so that I can check coverage without running the full pipeline.

**Acceptance Scenarios:**

1. **Given** I run the CLI command with `--spec-file spec.md --tasks-file
   tasks.md`, **When** all FRs are covered, **Then** the command exits with
   code 0 and prints a success summary.

2. **Given** I run the CLI command with `--json`, **When** validation completes,
   **Then** the output is a JSON object with `covered`, `uncovered`, and
   `total` fields.

3. **Given** I run the CLI command with files that have uncovered FRs, **When**
   validation fails, **Then** the command exits with a non-zero exit code and
   lists the uncovered FRs.

### US4. Enrich analysis report with FR coverage data (Priority: P3)

As a spec reviewer, I want the analysis report to include deterministic FR
coverage data, so that I can see at a glance which FRs have task coverage.

**Acceptance Scenarios:**

1. **Given** the analysis phase runs after successful validation, **When** the
   report is generated, **Then** it includes a section showing FR coverage
   status (covered/uncovered) for each FR identifier.

2. **Given** all FRs are covered, **When** the coverage section is rendered,
   **Then** it shows a green checkmark or "fully covered" summary.

## 7. Functional Requirements

FR-001. The validation step MUST extract all FR identifiers from `spec.md`
using the regex pattern `FR-\d+` (case-insensitive, one or more digits). The
identifier is captured exactly as written, preserving the original casing and any
leading zeros in the numeric suffix (e.g., `FR-1`, `FR-01`, and `FR-001` are
distinct identifiers). Uniqueness is determined by **case-insensitive**
comparison: if `spec.md` contains both `FR-001` and `fr-001`, they are treated
as the same identifier and the **first occurrence's casing** is preserved as the
canonical form for output and counting.

FR-002. The validation step MUST search `tasks.md` for each extracted FR
identifier to determine coverage. The search MUST be case-insensitive (e.g.,
`fr-001` in `tasks.md` matches `FR-001` extracted from `spec.md`). The search
MUST use word-boundary matching (e.g., regex `\bFR-001\b` with the
case-insensitive flag) to prevent prefix/substring false positives — searching
for `FR-1` MUST NOT match `FR-10` or `FR-100`.

FR-003. An FR is considered covered if its identifier (e.g., `FR-001`) appears
at least once in the text content of `tasks.md` as a whole-word,
case-insensitive match (i.e., bounded by word boundaries so that `FR-1` does
not match `FR-10` or `FR-100`). No normalization of leading zeros is applied —
the identifier must match the extracted form exactly (modulo case).

FR-004. The validation step MUST report a list of uncovered FR identifiers when
any FR lacks coverage.

FR-005. The validation step MUST block PR creation (exit with a non-zero code)
when one or more FRs are uncovered.

FR-006. The validation step MUST run after the tasks phase completes and before
the tasks PR is created.

FR-007. When validation fails and the retry count is below the configured
maximum, the pipeline MUST re-invoke task generation with a prompt that
explicitly lists the uncovered FR identifiers.

FR-008. The default maximum retry count MUST be 2, configurable via:

- **CLI flag**: `--max-retries <N>` on the `agdt-speckit-validate-frs` command.
- **Pipeline variable**: `SPECKIT_VALIDATE_MAX_RETRIES` environment variable.
- **Precedence**: CLI flag > environment variable > default (2).

FR-009. After each retry, the validation step MUST re-run on the updated
`tasks.md`.

FR-010. The standalone CLI command (`agdt-speckit-validate-frs`) MUST accept
`--spec-file` and `--tasks-file` arguments specifying the paths to the spec and
tasks files.

FR-011. The standalone CLI command MUST support a `--json` flag that outputs
results as a JSON object with the following schema:

- `covered`: sorted array of FR identifier strings (e.g., `["FR-001", "FR-003"]`),
  sorted by numeric suffix value in ascending order. Ties (identifiers with the
  same numeric value, e.g., `FR-1` and `FR-001`) are broken by string length
  (shorter first), then lexicographic order.
- `uncovered`: sorted array of FR identifier strings, same sort order as
  `covered`.
- `total`: integer — total number of unique FR identifiers extracted from `spec.md`.

Identifiers in the `covered` and `uncovered` arrays MUST preserve the original
casing as extracted from `spec.md` (per FR-001). The case-insensitive matching
described in FR-002 applies only to the coverage check against `tasks.md`, not
to the output representation. For example, if `spec.md` contains `FR-001`, the
JSON output includes `"FR-001"` regardless of whether `tasks.md` uses `fr-001`.

FR-012. The standalone CLI command MUST exit with code 0 when all FRs are
covered and a non-zero code when any FR is uncovered.

FR-013. The analysis report MUST include a deterministic FR coverage section
showing each FR identifier and its coverage status.

FR-014. When `spec.md` contains no FR-### identifiers, the validation step MUST
emit a warning and pass (graceful degradation, not a blocking failure).

## 8. Non-Functional Requirements

NFR-001. The validation step MUST complete in under 1 second for spec and tasks
files up to 100 KB combined.

NFR-002. The validation logic MUST be fully deterministic — no LLM calls, no
network requests, no randomness.

NFR-003. The validation step MUST be read-only with respect to `spec.md` and
`tasks.md` — it MUST NOT modify either file.

NFR-004. The validation output format MUST be consistent with existing SpecKit
pipeline output conventions (structured logging, exit codes).

NFR-005. The CLI command output (both human-readable and `--json`) MUST be
stable across runs for the same input (deterministic output).

## 9. Edge Cases

EC1. **Duplicate FR identifiers in spec**: If `spec.md` contains the same FR
identifier multiple times (e.g., in a summary and in the detailed section), it
MUST be counted once. Duplicate detection is **case-insensitive** — `FR-001`
and `fr-001` are considered the same identifier. The canonical form used in
output is the **first occurrence** in document order.

EC2. **FR identifier in code blocks**: FR identifiers appearing inside fenced
code blocks in `tasks.md` MUST still count as coverage (text search is
format-agnostic).

EC3. **Empty tasks file**: If `tasks.md` is empty or missing, all FRs are
uncovered and validation fails.

EC4. **Empty spec file**: If `spec.md` is empty or missing, no FRs are extracted
and the validation passes with a warning.

EC5. **FR identifiers with varying digit counts**: The regex MUST match
`FR-1`, `FR-01`, `FR-001`, and `FR-0001` as distinct identifiers. No
normalization is applied — identifiers are compared as-written. Spec authors
should use a consistent zero-padded format (e.g., `FR-001`) to avoid false
negatives from padding mismatches between `spec.md` and `tasks.md`.

## 10. Success Metrics

SM1. Zero SpecKit task PRs are created with incomplete FR coverage after the
validation gate is enabled.

SM2. The auto-retry mechanism resolves at least 80% of first-attempt coverage
gaps without manual intervention.

SM3. The validation step adds less than 1 second to the overall pipeline
execution time.

SM4. 100% unit test coverage for the validation module.

## 11. Clarification Changelog

The following clarifications were applied during Phase 2 review:

| # | Question | Answer Applied To |
|---|----------|-------------------|
| 1 | Pipeline ordering (validation vs. analyze phase) | FR-006, Summary, Assumptions §4 |
| 2 | Module placement (`validate_frs.py`) | Scope, §5 Key Design Decision |
| 3 | Analysis report enrichment mechanism | FR-013 (rewritten), US4 scenarios, `fr-coverage.json` |
| 4 | Human-readable CLI output format | FR-004 (expanded), US3 scenarios |
| 5 | Auto-retry prompt mechanism | FR-007 (expanded), US2 scenario 1 |

Also clarified retry failure handling, stale `fr-coverage.json` handling,
and non-functional expectations in the affected sections.

---

*Generated by Copilot SDK (claude-opus-4.6)*
