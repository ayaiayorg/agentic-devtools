# Implementation Plan: SpecKit Pipeline CRITICAL Analysis Gate

**Issue**: [#1197](https://github.com/ayaiayorg/agentic-devtools/issues/1197)
**Feature Branch**: `1197-speckit-pipeline-gate-creation`

## 1. Technical Context

### Technology Stack

- **Shell scripts** (bash): Primary pipeline scripts — `generate-spec-from-issue.sh` (~2000 LOC), `create-spec-pr.sh` (~350 LOC)
- **GitHub Actions workflows**: `speckit-phase-progression.yml`, `speckit-issue-trigger.yml`
- **GitHub Actions step outputs**: For inter-step structured data passing
- **Markdown parsing**: grep/sed/awk on `analysis-report.md` Findings Table
- **`post-issue-comment.sh`**: Existing template-based issue commenting with `{{variable}}` substitution
- **Repository variables**: `SPECKIT_COMMENT_ON_ISSUE`, `SPECKIT_AUTO_MERGE_PHASES`, `SPECKIT_CREATE_PR`, `SPECKIT_CREATE_BRANCH` — new: `SPECKIT_CRITICAL_GATE_MODE`

### Key Dependencies

- `analysis-report.md` Findings Table format (pipe-delimited markdown table with a `Severity` column;
  the header varies across reports — e.g., `| ID | Category | Severity | ... |` or
  `| ID | Pass | Severity | ... |` — so the parser must locate the `Severity` column dynamically
  by name rather than assuming a fixed column index)
- `create-spec-pr.sh` — PR creation centralization point (needs `--draft` flag)
- Phase progression workflow structure (Phase 5 = analyze in phased mode; Phase 6 = analyze in monolithic mode)
- Existing failure-handling patterns (issue comments, `speckit:failed` label)

### Architecture Decisions

- **Pure bash implementation** — no Python/Node dependencies (NFR-002)
- **Standalone gate script** — new `check-analysis-gate.sh` script callable from both pipeline paths
- **Fail-closed design** — missing/empty/malformed reports always block
- **Composable outputs** — GitHub Actions step outputs + `GATE_RESULT_JSON:` prefix for monolithic

## 2. Research Summary

Key design decisions and their rationale:

1. **Parsing strategy**: Regex-based line-by-line Findings Table parsing vs. awk column extraction → chose awk for robustness.
   Awk handles pipe-delimited columns reliably regardless of whitespace and formatting variants (`CRITICAL`, `**CRITICAL**`, etc.), whereas regex-per-line is fragile against bold/italic wrapping.
   The parser must first read the header row to locate the `Severity` column by name (not by fixed index),
   since existing reports use varying headers (e.g., `| ID | Category | Severity | ... |` vs
   `| ID | Pass | Severity | ... |`).
2. **Gate script architecture**: Standalone script vs. inline workflow logic → chose standalone `check-analysis-gate.sh`.
   A standalone script can be sourced by both the monolithic (`generate-spec-from-issue.sh`) and phased (`speckit-phase-progression.yml`) paths without duplication. It is also independently testable.
3. **Draft PR implementation**: `--draft` flag on `create-spec-pr.sh` vs. separate draft logic → chose flag per FR-013.
   Centralizing the draft flag in `create-spec-pr.sh` keeps PR creation in one place and avoids a second code path for draft-specific `gh pr create` invocations.
4. **Resolved detection regex**: Handling `~~CRITICAL~~` + RESOLVED variants → chose normalized regex pattern.
   Before matching, strip bold/italic markers (`*`, `_`) from each severity cell so that `~~**CRITICAL**~~`, `**~~CRITICAL~~**`, and `~~CRITICAL~~` all
   normalize to the same form. The normalized pattern `~~CRITICAL~~.*RESOLVED` (case-insensitive for RESOLVED) then correctly identifies addressed findings
   regardless of bold/italic wrapping, while treating bare `~~CRITICAL~~` without the RESOLVED marker as still unresolved.
5. **Analyzer prompt contract update**: How to encode the RESOLVED format requirement → explicit instruction block.
   Adding an instruction block to the LLM prompt defines the `~~ORIGINAL_SEVERITY~~ → RESOLVED` format as a machine-parseable contract, ensuring the gate script can reliably detect addressed findings.

## 3. Design Overview

### Component Architecture

```text
┌─────────────────────────────────────────────────┐
│ generate-spec-from-issue.sh                     │
│  ├─ Monolithic: Phase 6 → check_analysis_gate() │
│  └─ Phased:     Phase 5 → check_analysis_gate() │
└─────────────┬───────────────────────────────────┘
              │ sources
              ▼
┌─────────────────────────────────────────────────┐
│ check-analysis-gate.sh                          │
│  ├─ parse_findings_table()                      │
│  ├─ detect_unresolved_critical()                │
│  ├─ emit_gate_result()                          │
│  │   ├─ GitHub Actions outputs (phased)         │
│  │   └─ GATE_RESULT_JSON: line (monolithic)     │
│  └─ Returns:                                     │
│       0 = pass, or soft-fail in draft mode       │
│       1 = hard-fail (block mode) / malformed     │
└─────────────────────────────────────────────────┘
              │
  ┌───────────┴───────────┐
  ▼                       ▼
Gate pass               Gate fail
  │                       │
  ▼                       ▼
┌────────────┐   ┌──────────────────────────┐
│create-spec-│   │ Post issue comment        │
│pr.sh       │   │ (gate-failure template)   │
│(normal)    │   │ Apply speckit:failed label│
└────────────┘   └──────────────────────────┘
       OR (draft mode)
       ▼
┌────────────┐
│create-spec-│
│pr.sh       │
│ --draft    │
│(+ no       │
│ auto-merge)│
└────────────┘
```

### Gate Script Interface

```bash
# Usage:
check-analysis-gate.sh <report_path> [--mode block|draft] [--github-actions]

# Exit codes (mode-dependent):
#
#   --mode block (default):
#     0 = pass (zero unresolved CRITICAL findings)
#     1 = fail (one or more unresolved CRITICAL, or report missing/empty/malformed)
#
#   --mode draft:
#     0 = pass (zero unresolved CRITICAL findings)
#     0 = unresolved CRITICALs detected, but gate_result=fail emitted via
#         structured output so downstream steps can create a draft PR
#     1 = report missing/empty/malformed (hard failure in all modes)
#
# Rationale: In draft mode the phased workflow must continue past the gate step
# to commit, push, and create a draft PR. A non-zero exit would fail the job
# before those steps run. Structured output (gate_result=fail + critical_count)
# lets downstream steps decide whether to pass --draft to create-spec-pr.sh.

# Outputs (when --github-actions):
#   GITHUB_OUTPUT: critical_count, critical_findings (JSON), gate_result

# Outputs (always):
#   stdout: GATE_RESULT_JSON:{...} line
#   stderr: Human-readable summary with banner
```

## 4. Implementation Phases

### Phase 1: Core Gate Script (`check-analysis-gate.sh`)

**Deliverables**: Standalone bash script that parses `analysis-report.md` and returns pass/fail

**Files**:

- `NEW` `.github/scripts/speckit-trigger/check-analysis-gate.sh`
- `NEW` `.github/scripts/speckit-trigger/fixtures/analysis-report-with-criticals.md` (test fixture)
- `NEW` `.github/scripts/speckit-trigger/fixtures/analysis-report-with-resolved-criticals.md` (test fixture)
- `NEW` `.github/scripts/speckit-trigger/fixtures/analysis-report-no-criticals.md` (test fixture)

**Tasks**:

1. **T01 — Create `check-analysis-gate.sh` skeleton**: Argument parsing (`<report_path>`, `--mode`, `--github-actions`), input validation, fail-closed missing/empty check.
   Exit-code semantics are mode-dependent: in `block` mode, exit 1 on unresolved CRITICALs; in `draft` mode, exit 0 but emit `gate_result=fail` via structured output so downstream steps can proceed
   to create a draft PR. Exit 1 for missing/empty/malformed reports in all modes
2. **T02 — Implement Findings Table parser**: Starting from the `| ID |` header line, parse only subsequent lines that begin with `|` (stop at the first
   non-`|` line, such as a blank line, `---` separator, or `##` heading — do NOT rely solely on the next `##` heading as a delimiter, since non-table lines
   like section separators may appear before it).
   Locate the `Severity` column dynamically by splitting the header row on `|` and finding the cell whose
   trimmed text equals `Severity` (do NOT assume a fixed column index — existing reports use
   `| ID | Category | Severity | ... |`, `| ID | Pass | Severity | ... |`, and potentially other variants).
   Skip the separator row (e.g., `| --- | --- | ... |`) by detecting lines where all cells match `-+`.
   Parse each data row's Severity value using the discovered column index.
   Handle formatting variants: `CRITICAL`, `**CRITICAL**`, `| CRITICAL |`, bold/italic combos
3. **T03 — Implement resolved-finding detector**: Before matching, normalize the severity cell by stripping bold/italic markers (`*`, `_`) so that variants
   like `~~**CRITICAL**~~`, `**~~CRITICAL~~**`, and `~~CRITICAL~~` all reduce to `~~CRITICAL~~`. Then match with the pattern
   `~~CRITICAL~~.*RESOLVED` (case-insensitive for RESOLVED). Bare `~~CRITICAL~~` without RESOLVED = unresolved
4. **T04 — Implement structured output**: Emit `GATE_RESULT_JSON:` line with `status`, `reason`, `criticalCount`, `reportPath`. When `--github-actions` flag: write `critical_count`,
   `critical_findings` (JSON array), `gate_result` to `$GITHUB_OUTPUT`
5. **T05 — Implement human-readable output**: Banner: `## ❌ SpecKit: CRITICAL Gate Failed` (matching NFR-003). List each finding: ID, summary, recommendation.
   Pass banner: `## ✅ SpecKit: CRITICAL Gate Passed`
6. **T06 — Implement malformed-report detection**: Fail closed if Findings Table header row not found or if the header row does not contain a `Severity` column. Set reason `report_parse_error`
7. **T07 — Create test fixtures**: Reports with: unresolved CRITICALs, resolved CRITICALs only, no CRITICALs, mixed resolved/unresolved, empty file, malformed (no table), formatting variants
   (`**CRITICAL**`, bold+italic, `~~**CRITICAL**~~ **RESOLVED**`, `**~~CRITICAL~~** RESOLVED`), and header variants (e.g., `| ID | Pass | Severity | ... |` to exercise dynamic column detection)
8. **T08 — Create test script `test_check_analysis_gate.sh`**: Automated bash tests exercising all fixtures. Verify exit codes, GATE_RESULT_JSON content, GitHub Actions outputs (simulated)

### Phase 2: Integrate Gate into Monolithic Pipeline

**Deliverables**: Monolithic path stops after Phase 6 when CRITICAL findings detected

**Files**:

- `EDIT` `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` (monolithic orchestration section, ~lines 1969-1979)

**Tasks**:

1. **T09 — Source gate script in `generate-spec-from-issue.sh`**: Add `source "$SCRIPT_DIR/check-analysis-gate.sh"` (or call as subprocess) after the analyze phase
2. **T10 — Add gate check after Phase 6 (monolithic)**: Between Phase 6 (analyze) and Phase 7 (markdownlint), call the gate function. On failure, exit non-zero with message. Phase 7 must NOT run if
   gate fails
3. **T11 — Pass `SPECKIT_CRITICAL_GATE_MODE` env var through**: Read `SPECKIT_CRITICAL_GATE_MODE` (default: `block`) and pass as `--mode` to gate check. In draft mode, don't block in monolithic path
   (let downstream handle draft)

### Phase 3: Integrate Gate into Phased Workflow

**Deliverables**: Phase 5 analyze workflow runs gate check before commit/push/PR creation

**Files**:

- `EDIT` `.github/workflows/speckit-phase-progression.yml` (Phase 5 section)
- `EDIT` `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` (single-phase section, ~lines 1902-1914)

**Tasks**:

1. **T12 — Add gate check after Phase 5 `run_single_phase`**: In the `5)` case of
   `run_single_phase`, after analyze + markdownlint, invoke the gate check with
   `--github-actions`. Mode-dependent behavior: in `block` mode (default), exit
   non-zero on unresolved CRITICALs (fails the workflow step). In `draft` mode,
   exit 0 but emit `gate_result=fail` via `$GITHUB_OUTPUT` so the workflow step
   succeeds and downstream steps can conditionally create a draft PR.
   This is the **authoritative integration point** — the gate runs inline during
   the "Generate Phase Artifacts" step, not as a separate workflow step, because
   the report file is only available inside the script's working directory.
   Pass `--mode "$SPECKIT_CRITICAL_GATE_MODE"` (defaulting to `block`) to respect
   the repository variable
2. **T13 — Capture gate outputs in workflow**: Ensure the "Generate Phase
   Artifacts" step exposes `critical_count`, `critical_findings`, and
   `gate_result` as step outputs (written to `$GITHUB_OUTPUT` by the gate script
   via `--github-actions`). Conditionally relevant only for Phase 5. Downstream
   steps reference these outputs to decide whether to proceed, create a draft PR,
   or post a failure comment
3. **T14 — Gate the "Commit Phase Artifacts" step**: Add condition: only run if
   `steps.generate.outputs.gate_result == 'pass'` OR
   `vars.SPECKIT_CRITICAL_GATE_MODE == 'draft'`. This prevents commit+push+PR
   when gate fails in block mode
4. **T15 — Add gate failure comment step**: New workflow step (`if: failure()` + gate-specific) that posts CRITICAL findings to the source issue. Uses `SPECKIT_COMMENT_ON_ISSUE` check. Applies
   `speckit:failed` label

### Phase 4: Draft PR Mode (`--draft` flag + auto-merge suppression)

**Deliverables**: `create-spec-pr.sh` supports `--draft`, pipeline creates draft PR in draft mode

**Files**:

- `EDIT` `.github/scripts/speckit-trigger/create-spec-pr.sh` (~lines 53-76, 282-294)
- `EDIT` `.github/workflows/speckit-phase-progression.yml` (Create PR + Auto-Merge steps)

**Tasks**:

1. **T16 — Add `--draft` flag to `create-spec-pr.sh`**: Parse `--draft` in the named arguments section. When set, pass `--draft` to `gh pr create`. Output `is_draft=true` to `GITHUB_OUTPUT`
2. **T17 — Inject CRITICAL findings into draft PR body**: When `--draft` + CRITICAL findings exist, prepend a `## ⚠️ CRITICAL Findings` section to the PR body with finding details. Accept findings
   via `--critical-findings-json` argument or environment variable
3. **T18 — Suppress auto-merge for draft PRs with CRITICALs**: In the "Auto-Merge" step of `speckit-phase-progression.yml`, add condition: skip auto-merge when `gate_result == 'fail'` (even in draft
   mode)
4. **T19 — Wire draft mode in workflow**: When `SPECKIT_CRITICAL_GATE_MODE == 'draft'` and gate fails, pass `--draft` + `--critical-findings-json` to `create-spec-pr.sh`. Normal flow for zero
   CRITICALs

### Phase 5: Issue Comment Template + Failure Handling

**Deliverables**: Gate failure posts actionable comment on source issue

**Files**:

- `NEW` `.github/scripts/speckit-trigger/templates/critical-gate-failed.md`
- `EDIT` `.github/workflows/speckit-phase-progression.yml` (failure step)
- `EDIT` `.github/workflows/speckit-issue-trigger.yml` (if Phase 1 ever runs analyze — unlikely but for completeness)

**Tasks**:

1. **T20 — Create `critical-gate-failed.md` template**: Template with: heading (`## ❌ SpecKit: CRITICAL Gate Failed`), findings table, workflow run link, re-trigger instructions. Variables:
   `{{FINDINGS_TABLE}}`, `{{PHASE_NUMBER}}`, `{{ISSUE_NUMBER}}`, `{{GITHUB_REPOSITORY}}`, `{{GITHUB_RUN_ID}}`
2. **T21 — Wire gate failure comment in phased workflow**: Use `post-issue-comment.sh` or inline `actions/github-script` to post the template when gate fails. Respect `SPECKIT_COMMENT_ON_ISSUE`.
   Apply `speckit:failed` label
3. **T22 — Wire gate failure comment in monolithic path**: In `generate-spec-from-issue.sh`, when gate fails and not in CI (no GITHUB_OUTPUT), print full details to stderr. In CI, the workflow
   failure handler covers commenting

### Phase 6: Analyzer Prompt Contract Update (FR-014)

**Deliverables**: Analyze prompt explicitly documents RESOLVED format as machine-parseable contract

**Files**:

- `EDIT` `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` (analyze prompt, ~lines 1720-1774)

**Tasks**:

1. **T23 — Update analyze phase prompt**: Add explicit instruction block to the LLM prompt defining the RESOLVED format contract: "When a finding has been addressed, change its severity cell to
   `~~ORIGINAL_SEVERITY~~ → RESOLVED`. Do NOT use strikethrough alone without the RESOLVED marker."
2. **T24 — Add examples to prompt**: Show correct resolved format: `| F-01 | ... | ~~CRITICAL~~ → RESOLVED | ... |` and incorrect: `| F-01 | ... | ~~CRITICAL~~ | ... |`

### Phase 7: Validation + SC-004 Regression Testing

**Deliverables**: Verify gate passes on all 8 existing analysis reports; end-to-end test coverage

**Tasks**:

1. **T25 — Run gate against all existing `analysis-report.md` files**: Script that iterates over all 8 existing reports in `specs/` and verifies `gate_result=pass` for each. This satisfies SC-004
2. **T26 — End-to-end integration test**: Test monolithic path with a synthetic spec directory containing CRITICAL findings. Verify script exits non-zero after Phase 6
3. **T27 — Test draft mode end-to-end**: Verify `create-spec-pr.sh --draft` creates correct output. Verify CRITICAL findings injected into PR body

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM produces non-standard CRITICAL format | Medium | High | NFR-004 regex handles `CRITICAL`, `**CRITICAL**`, and pipe-delimited variants; FR-014 updates prompt contract |
| Existing reports break gate (false positives) | Low | High | SC-004: Run gate against all 8 existing reports as acceptance test before merge |
| Gate adds latency > 5s | Very Low | Low | Pure bash grep/awk on <50 findings; NFR-001 trivially met |
| Draft mode accidentally auto-merges | Medium | High | Explicit auto-merge suppression check (T18); tested in T27 |
| Monolithic and phased paths diverge | Medium | Medium | Single `check-analysis-gate.sh` script shared by both paths; tested in T25-T26 |
| `create-spec-pr.sh` `--draft` flag conflicts with existing args | Low | Medium | Argument parsing already uses `--` prefix convention; no existing `--draft` |

## 6. Dependencies

### Internal

- `generate-spec-from-issue.sh` — Phase 6/7 orchestration section (monolithic) and `run_single_phase` case 5 (phased)
- `create-spec-pr.sh` — PR creation centralization point
- `speckit-phase-progression.yml` — Phase 5 workflow steps (commit, push, create-pr, auto-merge)
- `post-issue-comment.sh` + templates — Existing comment infrastructure
- Existing `speckit:failed` label pattern used by both workflows

### External

- GitHub Actions `ubuntu-latest` runner toolchain (bash, grep, sed, awk, jq)
- `gh` CLI (already available in workflow runner)
- No new runtime dependencies added (NFR-002 compliance)

---
*Generated by Copilot SDK (claude-opus-4.6)*
