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
│  └─ Function return codes (library):              │
│       0  = pass (zero unresolved CRITICALs)       │
│       10 = unresolved CRITICALs detected          │
│       20 = report missing/empty/malformed          │
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
# Contract: `check-analysis-gate.sh` is a library script sourced by
# `generate-spec-from-issue.sh`; it is not the primary public CLI surface.
#
# Library requirements:
# - define functions only
# - no top-level `exit`
# - no top-level `set -euo pipefail`
# - no top-level side effects beyond function/constant definitions
#
# Primary sourced interface:
#   source "check-analysis-gate.sh"
#   check_analysis_gate <report_path> [block|draft] [github_actions_flag]
#
# Function return contract:
#
#   return 0 = report parsed successfully
#              and zero unresolved CRITICAL findings were detected
#
#   return 10 = report parsed successfully
#               and one or more unresolved CRITICAL findings were detected
#               (soft failure signal; caller decides whether to block or continue
#               in draft mode)
#
#   return 20 = report missing, empty, or malformed
#               (hard failure in all modes)
#
# On successful parse, the function also sets caller-visible variables and/or
# GitHub Actions outputs for downstream branching:
#   gate_result=pass|fail
#   critical_count=<integer>
#
# Process exit codes belong to a thin CLI wrapper only, e.g.:
#   check-analysis-gate-cli.sh <report_path> [--mode block|draft] [--github-actions]
#
# Wrapper exit-code mapping:
#
#   --mode block (default):
#     0 = pass
#     1 = unresolved CRITICAL findings detected
#     1 = report missing/empty/malformed
#
#   --mode draft:
#     0 = pass
#     0 = unresolved CRITICAL findings detected, but `gate_result=fail` is emitted
#         so downstream steps can continue and create a draft PR
#     1 = report missing/empty/malformed
#
# Rationale: because the main integration is via `source`, process termination
# behavior must be owned by the wrapper/caller rather than the library itself.
# The caller decides whether to terminate before downstream steps run.
# Structured output (gate_result=fail + critical_count) lets downstream steps
# decide whether to pass --draft to create-spec-pr.sh.

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

- `NEW` `.github/scripts/speckit-trigger/check-analysis-gate.sh` (sourced library — functions only, no top-level side effects)
- `NEW` `.github/scripts/speckit-trigger/check-analysis-gate-cli.sh` (thin CLI wrapper — argument parsing, exit codes)
- `NEW` `.github/scripts/speckit-trigger/fixtures/analysis-report-with-criticals.md` (test fixture)
- `NEW` `.github/scripts/speckit-trigger/fixtures/analysis-report-with-resolved-criticals.md` (test fixture)
- `NEW` `.github/scripts/speckit-trigger/fixtures/analysis-report-no-criticals.md` (test fixture)

**Tasks**:

1. **T01 — Create `check-analysis-gate.sh` library skeleton**: Define the `check_analysis_gate` function (no top-level side effects, no `exit`, no `set -euo pipefail`).
   The function accepts `<report_path>`, `[block|draft]`, and `[github_actions_flag]` as positional parameters.
   Return-code contract: `return 0` = pass (zero unresolved CRITICALs), `return 10` = unresolved CRITICALs detected (soft failure — caller decides whether to block or continue in draft mode),
   `return 20` = report missing/empty/malformed (hard failure in all modes). Input validation and fail-closed missing/empty check are inside the function.
   On successful parse, set caller-visible variables `gate_result=pass|fail` and `critical_count=<integer>`.
   **`errexit` guard requirement**: Because the caller (`generate-spec-from-issue.sh`) runs under
   `set -euo pipefail`, the function inherits `errexit`. Any internal command that may legitimately
   return non-zero — e.g., `grep` when a pattern is not found, `awk` returning no matches, or
   command substitutions — must be guarded with `|| true`, `|| :`, or an explicit `if`/`||`
   construct so the function can reach its own `return 10`/`return 20` rather than having the shell
   terminate on the intermediate non-zero exit. Alternatively, the function may temporarily disable
   `errexit` at entry (`set +e`) and restore it before returning (`set -e`), but the
   guard-per-command approach is preferred for clarity and auditability
2. **T01b — Create `check-analysis-gate-cli.sh` wrapper**: Thin CLI entry point that sources `check-analysis-gate.sh`, parses `--mode` and `--github-actions` flags,
   calls `check_analysis_gate`, and maps the library return codes to process exit codes.
   Exit-code semantics are mode-dependent: in `block` mode, exit 1 on return 10 or 20; in `draft` mode, exit 0 on return 10 (but `gate_result=fail` is still emitted), exit 1 on return 20.
   Guarded by `if [[ "${BASH_SOURCE[0]}" == "$0" ]]` so it is safe to source for testing
3. **T02 — Implement Findings Table parser**: Starting from the `| ID |` header line, parse only subsequent lines that begin with `|` (stop at the first
   non-`|` line, such as a blank line, `---` separator, or `##` heading — do NOT rely solely on the next `##` heading as a delimiter, since non-table lines
   like section separators may appear before it).
   Locate the `Severity` column dynamically by splitting the header row on `|` and finding the cell whose
   trimmed text equals `Severity` (do NOT assume a fixed column index — existing reports use
   `| ID | Category | Severity | ... |`, `| ID | Pass | Severity | ... |`, and potentially other variants).
   Skip the separator row (e.g., `| --- | --- | ... |`) by detecting lines where all cells match `-+`.
   Parse each data row's Severity value using the discovered column index.
   Handle formatting variants: `CRITICAL`, `**CRITICAL**`, `| CRITICAL |`, bold/italic combos
4. **T03 — Implement resolved-finding detector**: Before matching, normalize the severity cell by stripping bold/italic markers (`*`, `_`) so that variants
   like `~~**CRITICAL**~~`, `**~~CRITICAL~~**`, and `~~CRITICAL~~` all reduce to `~~CRITICAL~~`. Then match with the pattern
   `~~CRITICAL~~.*RESOLVED` (case-insensitive for RESOLVED). Bare `~~CRITICAL~~` without RESOLVED = unresolved
5. **T04 — Implement structured output**: Emit `GATE_RESULT_JSON:` line to stdout with the JSON fields
   `gate_result` (pass/fail), `reason`, `critical_count` (integer), and `report_path`.
   **Naming convention**: the JSON fields use the same snake_case names as the caller-visible
   shell variables (`gate_result`, `critical_count`) defined in the Gate Script Interface above,
   ensuring a single consistent vocabulary across shell variables, JSON output, and GitHub Actions
   outputs.
   When the `github_actions_flag` positional parameter is set: write `critical_count`,
   `critical_findings` (JSON array), and `gate_result` to `$GITHUB_OUTPUT`.
   **Important**: `critical_findings` must be emitted as compact single-line JSON
   (e.g., via `jq -c`) because `$GITHUB_OUTPUT` is line-oriented. A pretty-printed
   or multiline JSON value would corrupt step outputs. Alternatively, use the
   multiline heredoc syntax (`<<EOF`) to write the value, but compact single-line
   JSON via `jq -c` is preferred for simplicity
6. **T05 — Implement human-readable output**: Banner: `## ❌ SpecKit: CRITICAL Gate Failed` (matching NFR-003). List each finding: ID, summary, recommendation.
   Pass banner: `## ✅ SpecKit: CRITICAL Gate Passed`
7. **T06 — Implement malformed-report detection**: Fail closed if Findings Table header row not found or if the header row does not contain a `Severity` column. Set reason `report_parse_error`
8. **T07 — Create test fixtures**: Reports with: unresolved CRITICALs, resolved CRITICALs only, no CRITICALs, mixed resolved/unresolved, empty file, malformed (no table), formatting variants
   (`**CRITICAL**`, bold+italic, `~~**CRITICAL**~~ **RESOLVED**`, `**~~CRITICAL~~** RESOLVED`), and header variants (e.g., `| ID | Pass | Severity | ... |` to exercise dynamic column detection)
9. **T08 — Create test script `test_check_analysis_gate.sh`**: Automated bash tests exercising all fixtures. Verify exit codes, GATE_RESULT_JSON content, GitHub Actions outputs (simulated)

### Phase 2: Integrate Gate into Monolithic Pipeline

**Deliverables**: Monolithic path gates after Phase 6 analysis — blocks in block mode; continues in draft mode while emitting `gate_result=fail`

**Files**:

- `EDIT` `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` (monolithic orchestration section, ~lines 1969-1979)

**Tasks**:

1. **T09 — Source gate script in `generate-spec-from-issue.sh`**: Add
   `source "$SCRIPT_DIR/check-analysis-gate.sh"` near the top of the file, after the
   `SCRIPT_DIR` and `REPO_ROOT` variable assignments are established (the script currently
   defines all helpers inline and has no existing `source` statements, so this will be the
   first).
   Because `generate-spec-from-issue.sh` runs under `set -euo pipefail`, the caller **must not** invoke `check_analysis_gate` as a bare statement — a non-zero return (10 or 20) would terminate the
   script immediately. Instead, capture the return code with an `||` guard:

   ```bash
   report_path="$SPEC_DIR/analysis-report.md"
   gate_mode="${SPECKIT_CRITICAL_GATE_MODE:-block}"
   gate_rc=0
   check_analysis_gate "$report_path" "$gate_mode" || gate_rc=$?
   ```

   Note: `report_path` is defined explicitly here because `generate-spec-from-issue.sh`
   does not have an existing variable for this path — the analyze phase writes the report
   to `$SPEC_DIR/analysis-report.md` directly. `gate_rc` is intentionally a plain variable assignment (not `local`), because the
   Phase 6→7 integration point in the monolithic run is at **top-level script scope** (not
   inside a function). Using `local` at top-level scope would error (`local: can only be
   used in a function`) and, with `set -euo pipefail`, would abort the script.

   This lets the caller inspect `gate_rc` and branch on it (0 = pass, 10 = unresolved CRITICALs, 20 = malformed report) without triggering `set -e` termination
2. **T10 — Add gate check after Phase 6 (monolithic)**: Between Phase 6 (analyze) and Phase 7 (markdownlint), call the gate function using the safe `|| gate_rc=$?` pattern from T09.
   Branching logic by mode and return code:
   - **Block mode** (`gate_rc=10` or `gate_rc=20`): Print CRITICAL findings details to stderr and exit non-zero. Phase 7 (markdownlint) does **not** run.
     Note: `generate-spec-from-issue.sh` does not contain `gh` CLI or GitHub API logic for commenting or labeling — those responsibilities belong to the CI workflow failure handlers (see T22).
   - **Draft mode** (`gate_rc=10`): Record `gate_result=fail` and `critical_count` for downstream draft-PR creation, then **continue** — Phase 7 runs normally because the spec still needs linting
     before the draft PR is created.
   - **Draft mode** (`gate_rc=20`): Report is malformed — exit non-zero in all modes (hard failure). Phase 7 does **not** run.
   - **Pass** (`gate_rc=0`): Continue normally to Phase 7 in both modes
3. **T11 — Pass `SPECKIT_CRITICAL_GATE_MODE` env var through**: Read `SPECKIT_CRITICAL_GATE_MODE` (default: `block`) and pass as the mode positional parameter to `check_analysis_gate`.
   The mode value controls only the branching logic in T10 — it does **not** change the gate function's return codes (which are always 0/10/20 regardless of mode)

### Phase 3: Integrate Gate into Phased Workflow

**Deliverables**: Phase 5 analyze workflow runs gate check before commit/push/PR creation

**Files**:

- `EDIT` `.github/workflows/speckit-phase-progression.yml` (Phase 5 section)
- `EDIT` `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` (single-phase section, ~lines 1902-1914)

**Tasks**:

1. **T12 — Add gate check after Phase 5 `run_single_phase`**: In the `5)` case of
   `run_single_phase`, after analyze + markdownlint, invoke the gate via the
   **sourced function** (not the CLI wrapper), passing the `github_actions_flag`
   positional parameter as `true`:

   ```bash
   report_path="$SPEC_DIR/analysis-report.md"
   gate_mode="${SPECKIT_CRITICAL_GATE_MODE:-block}"
   gate_rc=0
   check_analysis_gate "$report_path" "$gate_mode" true || gate_rc=$?
   ```

   (The CLI wrapper `check-analysis-gate-cli.sh` with its `--github-actions` named
   flag is intended for standalone/test invocations only — inside
   `generate-spec-from-issue.sh`, the sourced function is the primary interface as
   established in the Gate Script Interface contract.)

   Mode-dependent behavior: in `block` mode (default), exit
   non-zero on unresolved CRITICALs (fails the workflow step). In `draft` mode,
   exit 0 but emit `gate_result=fail` via `$GITHUB_OUTPUT` so the workflow step
   succeeds and downstream steps can conditionally create a draft PR.
   This is the **authoritative integration point** — the gate runs inline during
   the "Generate Phase Artifacts" step, not as a separate workflow step, to avoid
   duplicating gate logic between the monolithic and phased paths and to share the
   single `check-analysis-gate.sh` library sourced by `generate-spec-from-issue.sh`.
   (Note: the report file is also written to the spec directory and `spec_dir` is
   exported as a step output, so a separate workflow step *could* read it — the
   inline approach is chosen for code-sharing, not file-availability reasons.)
   Pass `"$SPECKIT_CRITICAL_GATE_MODE"` (defaulting to `block`) as the mode
   positional parameter, and explicitly wire the workflow repository variable
   into that step's shell environment with `env: SPECKIT_CRITICAL_GATE_MODE:
   ${{ vars.SPECKIT_CRITICAL_GATE_MODE }}` (or pass the same value directly as a
   script argument). Do **not** rely on `vars.SPECKIT_CRITICAL_GATE_MODE` being
   auto-exported to the shell
2. **T13 — Capture gate outputs in workflow**: Ensure the "Generate Phase
   Artifacts" step exposes `critical_count`, `critical_findings`, and
   `gate_result` as step outputs (written to `$GITHUB_OUTPUT` by the gate script
   via `--github-actions`). The gate only runs during Phase 5 (phased) and
   Phase 6 (monolithic), but downstream steps in T14 reference `gate_result`
   unconditionally. To avoid empty-output breakage in Phases 2-4 (where the gate
   does not run), `generate-spec-from-issue.sh` must emit default outputs
   `gate_result=pass` and `critical_count=0` to `$GITHUB_OUTPUT` for every
   non-analyze phase. This ensures T14's `if:` conditions evaluate correctly
   regardless of which phase ran. The same step must also define the explicit
   `env:` mapping for `SPECKIT_CRITICAL_GATE_MODE` so the script and its gate
   helper see the configured mode consistently
3. **T14 — Gate downstream steps on gate result**: Add conditions to prevent
   commit, push, and PR creation when the gate fails in block mode:
   - **"Commit Phase Artifacts" step**: only run if
     `steps.generate.outcome == 'success'` AND
     (`steps.generate.outputs.gate_result == 'pass'` OR
     `vars.SPECKIT_CRITICAL_GATE_MODE == 'draft'`). The
     `steps.generate.outcome == 'success'` guard ensures that artifact generation
     actually succeeded — without it, `vars.SPECKIT_CRITICAL_GATE_MODE == 'draft'`
     alone would allow the commit step to run even if the generate step failed for
     non-gate reasons (since these steps override the default `success()` behavior).
   - **"Push Branch" step**: add
     `steps.generate.outputs.gate_result == 'pass' || vars.SPECKIT_CRITICAL_GATE_MODE == 'draft'`
     to its existing `if:` condition (AND-joined), and also require
     `steps.commit.outcome == 'success'`, so it cannot run when the gate
     blocked the commit step or when the commit step was skipped/failed — even
     though Push currently has its own independent `if:` expression that does not
     use `success()`. Without the commit-outcome guard, Push could run with empty
     branch/output values from `steps.commit`.
   - **"Create Pull Request" step**: similarly gate on
     `steps.generate.outputs.gate_result == 'pass' || vars.SPECKIT_CRITICAL_GATE_MODE == 'draft'`
     (AND-joined with any existing condition) and also on
     `steps.commit.outcome == 'success'`, so a blocked gate cannot accidentally
     proceed to create a PR with empty outputs.
   All three conditions ensure that a failed gate in block mode halts the entire
   commit → push → create-PR chain, not just the commit step
4. **T15 — Extend failure commenting for gate failures without duplication**:
   Do **not** add a second independent `if: failure()` issue-comment step, because
   `speckit-phase-progression.yml` already has a generic `Handle Failure (Comment + Label)`
   step that comments and applies `speckit:failed`. Instead, extend that existing
   failure handler to detect `steps.generate.outputs.gate_result == 'fail'` and include
   the CRITICAL findings in the single failure comment while preserving the existing
   `SPECKIT_COMMENT_ON_ISSUE` check and label application. If a separate gate-specific
   step is still used, its `if:` condition must be mutually exclusive with the generic
   failure handler so only one comment step runs for a given failure

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
   `{{findings_table}}`, `{{phase_number}}`, `{{issue_number}}`, `{{GITHUB_REPOSITORY}}`, `{{GITHUB_RUN_ID}}`.
   `{{GITHUB_REPOSITORY}}` and `{{GITHUB_RUN_ID}}` are auto-filled by `post-issue-comment.sh`;
   all other variables (`findings_table`, `phase_number`, `issue_number`) must be
   passed explicitly as `key=value` arguments when invoking `post-issue-comment.sh`
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
