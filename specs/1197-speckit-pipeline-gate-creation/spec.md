# Feature Specification: SpecKit Pipeline CRITICAL Analysis Gate

**Feature Branch**: `1197-speckit-pipeline-gate-creation`
**Created**: 2026-04-15
**Status**: Draft
**Input**: User description: "Gate PR creation on zero CRITICAL analysis findings"
**Source Issue**: #1197 (<https://github.com/ayaiayorg/agentic-devtools/issues/1197>)

## Overview

The SpecKit pipeline (both the phased GitHub Actions workflow and the monolithic `generate-spec-from-issue.sh` path)
generates a cross-artifact `analysis-report.md` during the analyze phase. This report assigns severity levels
(CRITICAL, HIGH, MEDIUM, LOW, INFO) to findings. Today, the pipeline proceeds to commit, push, and create a PR
regardless of the severity of unresolved findings. This means PRs with CRITICAL findings — such as
"original spec overwritten" or "core feature not implemented in tasks" — are created and may be auto-merged,
triggering implementation on fatally flawed specifications.

This feature adds a quality gate that inspects the analysis report for unresolved CRITICAL findings
and blocks PR creation when any are present, preventing wasted reviewer and implementer effort.

## Clarifications

### Session 2026-04-21

- Q: `--draft` flag: add to `create-spec-pr.sh` or call `gh pr create --draft` independently?
  → A: **Add to `create-spec-pr.sh`** — centralizes PR creation logic (new FR-013)
- Q: Implement trigger secondary CRITICAL gate?
  → A: **Out of scope** — Phase 5 gate is sufficient; follow-up issue if needed
- Q: Update analyze prompt with RESOLVED formatting contract?
  → A: **Yes** — must be machine-parseable, not just convention (new FR-014)
- Q: "Phase 6/7" ambiguity in monolithic path?
  → A: **Corrected** — Phase 6 = analyze, Phase 7 = markdownlint (FR-009 updated)
- Q: Draft mode + missing/empty report?
  → A: **Fail closed regardless of gate mode** (FR-010 + edge case updated)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Block PR Creation on Unresolved CRITICAL Findings (Priority: P1)

As a pipeline operator, when the analysis phase produces one or more unresolved CRITICAL findings,
the pipeline MUST NOT create a PR. Instead, it should fail the workflow step with a clear, actionable message
listing the CRITICAL findings, so that the specification author can address them before a PR is created.

**Why this priority**: This is the core value proposition of the feature. Without this gate, the pipeline
continues to create PRs that require substantial rework, wasting reviewer time and potentially triggering
implementation on broken specifications. This was the direct problem observed in PR #1178.

**Independent Test**: Can be fully tested by generating a synthetic `analysis-report.md` with one or more
unresolved CRITICAL findings and running the gate check. The gate should exit non-zero and print the
CRITICAL findings. No PR creation or GitHub API calls are needed.

**Acceptance Scenarios**:

1. **Given** an `analysis-report.md` with 2 unresolved CRITICAL findings and 3 MEDIUM findings,
**When** the gate check runs after the analyze phase,
**Then** the pipeline exits with a non-zero exit code, prints each CRITICAL finding's ID, summary,
and recommendation, and does NOT proceed to commit or PR creation.

2. **Given** an `analysis-report.md` where all CRITICAL findings are marked RESOLVED
(e.g., `~~CRITICAL~~ → RESOLVED` or `**~~CRITICAL~~** RESOLVED`),
**When** the gate check runs,
**Then** the pipeline proceeds normally to commit and PR creation.

3. **Given** an `analysis-report.md` with only HIGH, MEDIUM, LOW, and INFO findings (zero CRITICAL),
**When** the gate check runs,
**Then** the pipeline proceeds normally to commit and PR creation.

4. **Given** an `analysis-report.md` with a `Critical Issues Count` metric of `0` in the Metrics section,
**When** the gate check runs,
**Then** the pipeline proceeds normally even if other severity findings are present.

---

### User Story 2 — Post CRITICAL Gate Failure Comment on Source Issue (Priority: P1)

As a specification author, when the pipeline blocks PR creation due to CRITICAL findings,
I want a comment posted on the source GitHub issue explaining why the pipeline was blocked and
listing the specific CRITICAL findings, so that I can understand what needs to be fixed and re-trigger the pipeline.

**Why this priority**: Without clear feedback on the source issue, the author would need to dig through
workflow logs to understand why the pipeline stopped. This is essential for a usable quality gate,
especially since the pipeline is fully automated and the author may not be monitoring workflow runs.

**Independent Test**: Can be tested by verifying that the gate failure step posts a well-structured
comment on a test issue, including CRITICAL finding details and re-trigger instructions.

**Acceptance Scenarios**:

1. **Given** the gate check fails due to 3 unresolved CRITICAL findings,
**When** the failure handler runs,
**Then** a comment is posted on the source GitHub issue containing: a heading indicating
the gate failure, a table or list of the CRITICAL findings (ID, summary, recommendation),
a link to the workflow run logs, and instructions for re-triggering.

2. **Given** the repository variable `SPECKIT_COMMENT_ON_ISSUE` is set to `false`,
**When** the gate check fails,
**Then** no comment is posted on the issue
(consistent with existing pipeline behavior for other comments).

3. **Given** the gate check fails,
**When** the failure handler runs,
**Then** the `speckit:failed` label is applied to the source issue
(consistent with existing failure handling).

---

### User Story 3 — Opt-In Draft PR Mode for CRITICAL Findings (Priority: P2)

As a pipeline operator, I want the option to create the PR as a draft (instead of blocking entirely)
when CRITICAL findings exist, with the CRITICAL findings prominently displayed in the PR description,
so that the specification can be collaboratively reviewed and fixed via the PR workflow
rather than requiring issue-level iteration.

**Why this priority**: Some teams prefer to use PR discussions for specification refinement.
Blocking entirely is the safest default, but an opt-in draft mode provides flexibility for teams
that prefer collaborative PR-based iteration. This is explicitly mentioned as an option
in the issue description.

**Independent Test**: Can be tested by setting the opt-in variable, generating an analysis report
with CRITICAL findings, and verifying that a draft PR is created with CRITICAL findings
injected into the PR body.

**Acceptance Scenarios**:

1. **Given** the repository variable `SPECKIT_CRITICAL_GATE_MODE` is set to `draft`,
and the analysis report contains 2 unresolved CRITICAL findings,
**When** the pipeline proceeds to PR creation,
**Then** a draft PR is created with the CRITICAL findings listed in a prominent warning section
of the PR description body.

2. **Given** the repository variable `SPECKIT_CRITICAL_GATE_MODE` is set to `draft`,
and the analysis report contains 2 unresolved CRITICAL findings,
**When** the draft PR is created,
**Then** auto-merge is NOT triggered for this PR regardless of
the `SPECKIT_AUTO_MERGE_PHASES` configuration.

3. **Given** the repository variable `SPECKIT_CRITICAL_GATE_MODE` is unset or set to `block` (the default),
**When** CRITICAL findings are present,
**Then** the pipeline blocks PR creation entirely (User Story 1 behavior).

4. **Given** `SPECKIT_CRITICAL_GATE_MODE` is set to `draft`, and the analysis report has zero
unresolved CRITICAL findings,
**When** the pipeline runs,
**Then** a normal (non-draft) PR is created and auto-merge operates as usual.

---

### User Story 4 — Gate Coverage for Monolithic Pipeline Path (Priority: P2)

As a developer running the monolithic (non-phased) pipeline via `generate-spec-from-issue.sh`
without the `--phase` flag, I want the same CRITICAL finding gate to apply after the analyze phase (Phase 6),
so that the gate is enforced consistently regardless of which pipeline path is used.

**Why this priority**: The monolithic path is used for local development and legacy CI configurations.
Without this, the gate would only work in the phased GitHub Actions workflow,
leaving a gap where CRITICAL findings could slip through.

**Independent Test**: Can be tested by running `generate-spec-from-issue.sh` (monolithic mode) with a spec
directory containing an `analysis-report.md` with CRITICAL findings,
and verifying the script exits non-zero after the analyze phase.

**Acceptance Scenarios**:

1. **Given** the monolithic pipeline runs all phases, and Phase 6 (Analyze) produces a report
with 1 unresolved CRITICAL finding,
**When** Phase 6 completes,
**Then** the script exits with a non-zero exit code and a message listing the CRITICAL finding,
and Phase 7 (markdownlint) does NOT run.

2. **Given** the monolithic pipeline runs and Phase 6 produces a report with zero unresolved
CRITICAL findings,
**When** Phase 6 completes,
**Then** the script proceeds to Phase 7 (markdownlint validation) normally.

---

### User Story 5 — Structured Gate Output for Programmatic Consumption (Priority: P3)

As a CI integration author, I want the gate check to produce structured output
(in addition to human-readable console messages) that can be consumed by downstream workflow steps,
so that other automation can react to the gate result programmatically.

**Why this priority**: Enables future automation such as Slack notifications, dashboard integrations,
or conditional workflow steps. Not required for the core gate functionality but provides extensibility.

**Independent Test**: Can be tested by running the gate check and verifying the structured output
contains the expected fields (finding count, finding details, gate result).

**Acceptance Scenarios**:

1. **Given** the gate check runs in the GitHub Actions workflow,
**When** CRITICAL findings are detected,
**Then** the step outputs `critical_count`, `critical_findings`
(JSON array of finding objects with `id`, `summary`, `recommendation`),
and `gate_result` (`fail` or `pass`) as GitHub Actions step outputs.

2. **Given** the gate check runs and no CRITICAL findings exist,
**When** the step completes,
**Then** `critical_count=0`, `critical_findings=[]`, and `gate_result=pass`
are set as step outputs.

3. **Given** the monolithic pipeline path runs and the gate completes,
**When** the gate emits the structured result,
**Then** the result is prefixed with `GATE_RESULT_JSON:` followed by machine-parseable JSON
containing at minimum: `gate_result` (`pass` or `fail`), `reason` (one of the enumerated reason codes below),
`critical_count` (integer count of unresolved CRITICAL findings),
and `report_path` (path used for the gate input when available).

The allowed `reason` codes are:

| Code | Meaning |
|------|---------|
| `no_critical_findings` | Zero unresolved CRITICAL findings — gate passed |
| `critical_findings_detected` | One or more unresolved CRITICAL findings — gate failed |
| `report_missing` | Analysis report file is missing or empty — gate failed (fail-closed) |
| `report_parse_error` | Analysis report could not be parsed (malformed markdown) — gate failed (fail-closed) |

---

### Edge Cases

- What happens when the `analysis-report.md` file is missing or empty after the analyze phase?
  The gate check should treat a missing/empty report as a failure
  (cannot verify zero CRITICAL findings) and block PR creation with a clear error message.
  This fail-closed behavior applies equally to draft and non-draft PR creation modes.
- What happens when the analysis report contains malformed markdown that cannot be parsed
  (e.g., missing Findings Table)? The gate check should fail closed (block PR creation)
  and report a parse error rather than silently allowing the PR through.
- What happens when CRITICAL findings use inconsistent formatting across different LLM runs
  (e.g., `CRITICAL` vs `**CRITICAL**` vs `| CRITICAL |`)?
  The parser must handle common markdown formatting variations robustly.
- What happens when the Metrics section says `Critical Issues Count: 0` but the Findings Table
  contains an unresolved CRITICAL row? The Findings Table is the source of truth —
  the gate should detect the inconsistency and block.
- What happens when a finding has `~~CRITICAL~~` strikethrough but is NOT followed by `RESOLVED`?
  The finding should be treated as unresolved CRITICAL
  (strikethrough alone is insufficient — the RESOLVED marker is required).
- Draft mode is requested, but the report is missing, empty, or malformed; the gate still
  fails closed.
- Monolithic mode emits human-readable logs in addition to the structured line; consumers must
  rely on the `GATE_RESULT_JSON:` line for automation.
- The report mixes resolved and unresolved CRITICAL findings; only unresolved findings are
  counted as blocking.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The pipeline MUST parse the `analysis-report.md` Findings Table to identify rows
with unresolved CRITICAL severity after the analyze phase completes.

- **FR-002**: A CRITICAL finding MUST be considered "resolved" only when its severity cell contains
both a strikethrough marker (`~~CRITICAL~~`) AND a RESOLVED indicator
(e.g., `RESOLVED`, `→ RESOLVED`).
A bare `CRITICAL` without strikethrough and RESOLVED MUST be treated as unresolved.

- **FR-003**: When one or more unresolved CRITICAL findings are detected and the gate mode is
`block` (default), the pipeline MUST exit with a non-zero exit code
and MUST NOT proceed to commit, push, or PR creation.

- **FR-004**: The gate failure output MUST list each unresolved CRITICAL finding with its ID,
summary, and recommendation in a human-readable format on the console/log.

- **FR-005**: When the gate blocks PR creation in the phased workflow, a comment MUST be posted
on the source GitHub issue (unless `SPECKIT_COMMENT_ON_ISSUE` is `false`) containing
the CRITICAL finding details and re-trigger instructions.

- **FR-006**: When the gate blocks PR creation, the `speckit:failed` label MUST be applied
to the source GitHub issue (consistent with existing failure handling).

- **FR-007**: When the repository variable `SPECKIT_CRITICAL_GATE_MODE` is set to `draft`,
the pipeline MUST create the PR as a draft instead of blocking,
with CRITICAL findings displayed prominently in the PR description.

- **FR-008**: When a draft PR is created due to CRITICAL findings, auto-merge MUST NOT be triggered
for that PR regardless of `SPECKIT_AUTO_MERGE_PHASES` configuration.

- **FR-009**: The gate MUST apply consistently in both the phased GitHub Actions workflow
(Phase 5 analyze) and the monolithic `generate-spec-from-issue.sh` pipeline path.
In the monolithic path, Phase 6 MUST be treated as the analysis phase and Phase 7 MUST be
treated as the markdownlint phase. Documentation, logging, and gate logic MUST use this
numbering consistently.

- **FR-010**: When the `analysis-report.md` file is missing or empty after the analyze phase,
the gate MUST fail closed (block PR creation) with a clear error message.
This fail-closed behavior applies equally to normal PR mode and draft PR mode —
the gate mode setting does not bypass the missing/empty report check.

- **FR-011**: The gate MUST produce GitHub Actions step outputs (`critical_count`,
`critical_findings`, `gate_result`) for programmatic consumption
by downstream workflow steps.
In the monolithic path, the gate result MUST be emitted in a machine-parseable structured
form prefixed with `GATE_RESULT_JSON:` so downstream tooling can reliably parse it.
Minimum JSON fields: `gate_result` (`pass` or `fail`), `reason` (one of the enumerated reason codes:
`no_critical_findings`, `critical_findings_detected`, `report_missing`, `report_parse_error`),
`critical_count` (integer count of unresolved CRITICAL findings),
and `report_path` (path used for the gate input when available).
The JSON fields use the same snake_case names as the GitHub Actions step outputs
and the caller-visible shell variables, ensuring a single consistent vocabulary.

- **FR-012**: The gate MUST only run after Phase 5 (analyze) in the phased workflow.
It MUST NOT affect Phases 1–4, which do not produce analysis reports.

- **FR-013**: Draft PR support MUST be implemented in `create-spec-pr.sh` via a `--draft` flag,
rather than by invoking `gh pr create --draft` independently elsewhere,
so that PR creation behavior remains centralized in a single script.

- **FR-014**: The analyze prompt/output contract MUST define resolved findings in a
machine-parseable way. A plain-text convention is insufficient. The gate MUST be able to
distinguish unresolved from resolved CRITICAL findings without heuristic parsing.

### Non-Functional Requirements

- **NFR-001**: The gate check MUST complete within 5 seconds for analysis reports up to 50 findings
(the current cap), adding negligible overhead to the pipeline.

- **NFR-002**: The gate check script MUST use only tools available in the GitHub Actions
`ubuntu-latest` runner (bash, grep, sed, awk) — no additional runtime dependencies.

- **NFR-003**: Console output for gate failures MUST be clearly distinguishable from other
pipeline output, using a consistent prefix or banner
(e.g., `## ❌ SpecKit: CRITICAL Gate Failed`) that matches the existing failure comment format.

- **NFR-004**: The CRITICAL severity parser MUST handle common markdown formatting variations
including: `CRITICAL`, `**CRITICAL**`, `| CRITICAL |`, `| **CRITICAL** |`,
and bold/italic combinations, without false positives on `~~CRITICAL~~` RESOLVED patterns.

- **NFR-005**: The gate check MUST be idempotent — running it multiple times on the same report
MUST produce the same result.

### Key Entities

- **Analysis Report** (`analysis-report.md`): The cross-artifact consistency report produced by
the analyze phase. Contains a Findings Table with rows keyed by ID, each having a Category,
Severity, Location(s), Summary, and Recommendation.
Also contains a Metrics section with aggregate counts including `Critical Issues Count`.

- **Finding**: A single row in the Findings Table. Key attributes: ID (e.g., `F01`),
Severity (CRITICAL/HIGH/MEDIUM/LOW/INFO), resolved status
(determined by strikethrough + RESOLVED marker).

- **Gate Result**: The outcome of the CRITICAL finding check.
Either `pass` (zero unresolved CRITICAL findings, pipeline proceeds) or
`fail` (one or more unresolved CRITICAL findings, pipeline halts or creates draft).
Both GitHub Actions step outputs (`gate_result`) and monolithic JSON (`status`)
use this same `pass`/`fail` vocabulary.

- **Gate Mode**: Configurable behavior when CRITICAL findings are detected.
`block` (default) prevents PR creation entirely.
`draft` creates a draft PR with findings highlighted.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero PRs are created by the SpecKit pipeline with unresolved CRITICAL findings
when `SPECKIT_CRITICAL_GATE_MODE` is unset or `block` — verified by reviewing pipeline runs
over a 30-day period after deployment.

- **SC-002**: When CRITICAL findings exist and the gate is in `block` mode,
100% of gate failure comments posted to the source issue contain all unresolved CRITICAL
finding IDs and summaries.

- **SC-003**: The gate check adds less than 5 seconds of wall-clock time to any pipeline run,
as measured by the GitHub Actions step duration.

- **SC-004**: Existing pipeline runs with zero CRITICAL findings (the common case,
based on the 8 existing analysis reports in `specs/005-*`, `specs/1175-*`,
`specs/1176-*`, `specs/1179-*`, `specs/1191-*`, `specs/1193-*`, `specs/1194-*`,
and `specs/1196-*`) continue to succeed with no behavioral change — verified by
running the gate against all existing `analysis-report.md` files in the repository.

- **SC-005**: Both the phased workflow and the monolithic pipeline path enforce the same gate —
verified by unit tests covering both code paths with synthetic analysis reports
containing CRITICAL findings.

## Out of Scope

- **Automatic remediation**: The gate only blocks or downgrades to draft.
It does NOT attempt to fix CRITICAL findings automatically.
Remediation remains the responsibility of the specification author
(consistent with the analyze agent's read-only constraint).
- **Gating on non-CRITICAL severities**: HIGH, MEDIUM, LOW, and INFO findings
do NOT block PR creation. Only CRITICAL severity triggers the gate.
- **Retroactive enforcement**: Existing PRs already created before this gate is deployed
are not affected. The gate applies only to future pipeline runs.
- **Implementation phase gating**: The `speckit:needs-implementation` label and the implement
trigger workflow are not modified by this feature.
If a Phase 5 PR was previously merged without the gate, the implementation trigger still fires.
The Phase 5 gate is sufficient; a secondary gate at trigger time is out of scope
and may be tracked in a follow-up issue if needed.

## Dependencies

- The analyze phase MUST continue to produce `analysis-report.md` in the current format
(Findings Table + Metrics section). Changes to the report format would require
corresponding updates to the gate parser.
- The `create-spec-pr.sh` script must support a `--draft` flag to enable the draft PR mode.
The `--draft` flag must be added to `create-spec-pr.sh` directly to centralize
PR creation logic (see FR-013).
- The `speckit.analyze` agent prompt's severity definitions and RESOLVED formatting conventions
are the contract that the gate parser relies on. The analyze agent prompt must be updated to
explicitly document the RESOLVED formatting contract (strikethrough + RESOLVED text) as a
machine-parseable requirement, not just a convention (see FR-014).

## Change Log

- Restored full spec structure after Phase 2 clarification (was inadvertently truncated).
- Added `## Clarifications` section with all 5 Q&A pairs from Session 2026-04-21.
- Added **FR-013** for centralized `--draft` handling in `create-spec-pr.sh`.
- Added **FR-014** for machine-parseable resolved-state analyzer contract.
- Updated **FR-009** to clarify monolithic phase numbering: Phase 6 = analyze, Phase 7 = markdownlint.
- Updated **FR-010** to fail closed on missing/empty reports in both normal and draft modes.
- Updated **FR-011** to require monolithic structured output with the `GATE_RESULT_JSON:` prefix.
- Added **US5 acceptance scenario 3** for monolithic structured output parsing.
- Removed all `[NEEDS CLARIFICATION]` markers from Out of Scope and Dependencies.
- Corrected **SC-004** analysis report count from 5 to 8 (actual repo count).
- Standardized gate result vocabulary to `pass`/`fail` across both GitHub Actions step outputs
  and monolithic JSON (previously used `passed`/`blocked` vs `pass`/`fail`).
- Enumerated allowed `reason` codes for the `GATE_RESULT_JSON` structured output.

---
*Generated by Copilot SDK (claude-opus-4.6)*
