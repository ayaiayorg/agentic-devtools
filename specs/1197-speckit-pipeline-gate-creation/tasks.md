# Tasks: SpecKit Pipeline CRITICAL Analysis Gate

**Issue**: [#1197](https://github.com/ayaiayorg/agentic-devtools/issues/1197)
**Feature Branch**: `1197-speckit-pipeline-gate-creation`

## Dependencies Legend

| Marker | Meaning |
|--------|---------|
| `[P]` | Parallelizable — works on different files, no blocking dependencies |
| `→ Txx` | Depends on task Txx completing first |

---

## Phase 1: Setup

- [ ] T001 Create fixtures directory structure at `.github/scripts/speckit-trigger/fixtures/` (already exists; verify writable)
- [ ] T002 [P] Create test fixture `fixtures/analysis-report-with-criticals.md` — 2 unresolved CRITICAL + 3 MEDIUM findings
- [ ] T003 [P] Create test fixture `fixtures/analysis-report-with-resolved-criticals.md` — all CRITICALs use `~~CRITICAL~~ → RESOLVED`
- [ ] T004 [P] Create test fixture `fixtures/analysis-report-no-criticals.md` — only HIGH/MEDIUM/LOW/INFO findings
- [ ] T005 [P] Create test fixture `fixtures/analysis-report-mixed-resolved-unresolved.md` — 1 resolved + 1 unresolved CRITICAL
- [ ] T006 [P] Create test fixture `fixtures/analysis-report-empty.md` — empty file (0 bytes)
- [ ] T007 [P] Create test fixture `fixtures/analysis-report-malformed-no-table.md` — valid markdown but no Findings Table
- [ ] T008 [P] Create test fixture `fixtures/analysis-report-formatting-variants.md` — `CRITICAL`, `**CRITICAL**`, `| **CRITICAL** |`, bold+italic combos,
  `~~**CRITICAL**~~ **RESOLVED**`, `**~~CRITICAL~~** RESOLVED`
- [ ] T009 [P] Create test fixture `fixtures/analysis-report-dynamic-header.md` — uses `| ID | Pass | Severity | ... |` header variant to exercise dynamic column detection
- [ ] T010 [P] Create test fixture `fixtures/analysis-report-metrics-zero-but-table-critical.md` — Metrics says `Critical Issues Count: 0` but Findings Table has unresolved CRITICAL row (inconsistency
  edge case)
- [ ] T011 [P] Create test fixture `fixtures/analysis-report-strikethrough-no-resolved.md` — bare `~~CRITICAL~~` without RESOLVED marker (should be treated as unresolved)

---

## Phase 2: Foundational

- [ ] T012 Create `check-analysis-gate.sh` library skeleton: `check_analysis_gate` function signature accepting `<report_path> [block|draft] [github_actions_flag]`, return-code contract (0=pass,
  10=unresolved CRITICALs, 20=missing/empty/malformed), errexit guards, no top-level side effects → `.github/scripts/speckit-trigger/check-analysis-gate.sh`
- [ ] T013 Implement missing/empty report detection inside `check_analysis_gate` — `return 20` with reason `report_missing` when file absent or zero bytes → `check-analysis-gate.sh` | → T012
- [ ] T014 Implement Findings Table parser: locate `| ... Severity ... |` header dynamically by column name, skip separator rows,
  extract data rows until first non-pipe line → `check-analysis-gate.sh` | → T013
- [ ] T015 Implement resolved-finding detector: strip bold/italic markers (`*`, `_`) from severity cell, match `~~CRITICAL~~.*RESOLVED` (case-insensitive RESOLVED), classify bare `~~CRITICAL~~` as
  unresolved → `check-analysis-gate.sh` | → T014
- [ ] T016 Implement malformed-report detection: `return 20` with reason `report_parse_error` when Findings Table header not found or header lacks Severity column → `check-analysis-gate.sh` | → T014
- [ ] T017 Implement structured output emitter: `GATE_RESULT_JSON:` line to stdout with `gate_result`, `reason`, `critical_count`, `report_path` fields; GitHub Actions outputs (`critical_count`,
  `critical_findings` as compact JSON, `gate_result`) to `$GITHUB_OUTPUT` when `github_actions_flag` is set → `check-analysis-gate.sh` | → T015, T016
- [ ] T018 Implement human-readable output to stderr: `## ❌ SpecKit: CRITICAL Gate Failed` banner with finding ID/summary/recommendation list; `## ✅ SpecKit: CRITICAL Gate Passed` banner on success →
  `check-analysis-gate.sh` | → T017
- [ ] T019 Set caller-visible shell variables `gate_result` and `critical_count` before return so sourcing callers can branch on them → `check-analysis-gate.sh` | → T018
- [ ] T020 Create `check-analysis-gate-cli.sh` thin CLI wrapper: parse `--mode` and `--github-actions` flags, source library, call `check_analysis_gate`, map return codes to process exit codes (block:
  exit 1 on rc 10/20; draft: exit 0 on rc 10, exit 1 on rc 20), guard with `BASH_SOURCE` check → `.github/scripts/speckit-trigger/check-analysis-gate-cli.sh` | → T019
- [ ] T021 Source `check-analysis-gate.sh` in `generate-spec-from-issue.sh` after SCRIPT_DIR/REPO_ROOT assignments (first `source` statement in the file) →
  `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` | → T019
- [ ] T022 Create `test_check_analysis_gate.sh` automated test script: exercise all fixtures from T002–T011, verify return codes, `GATE_RESULT_JSON` content, caller-visible variables, and simulated
  GitHub Actions outputs → `.github/scripts/speckit-trigger/test_check_analysis_gate.sh` | → T020, T002–T011

---

## Phase 3: US1 — Block PR Creation on Unresolved CRITICAL Findings

- [ ] T023 [US1] Add gate check in `run_single_phase` case `5)` after analyze phase completes: call `check_analysis_gate` with `|| gate_rc=$?` guard,
  passing report path, gate mode, and `true` for github_actions_flag → `generate-spec-from-issue.sh` (~line 1910) | → T021
- [ ] T024 [US1] Add block-mode branching in case `5)`: exit non-zero on `gate_rc=10` or `gate_rc=20` to fail the workflow step → `generate-spec-from-issue.sh` | → T023
- [ ] T025 [US1] Add draft-mode branching in case `5)`: exit 0 on `gate_rc=10` (emit `gate_result=fail` via `$GITHUB_OUTPUT`), exit non-zero on `gate_rc=20` → `generate-spec-from-issue.sh` | → T024
- [ ] T026 [US1] Emit default `gate_result=pass` and `critical_count=0` to `$GITHUB_OUTPUT` for non-analyze phases (cases 2, 3, 4) so downstream `if:` conditions evaluate correctly →
  `generate-spec-from-issue.sh` | → T021
- [ ] T027 [US1] Add `SPECKIT_CRITICAL_GATE_MODE` env mapping to "Generate Phase Artifacts" step → `speckit-phase-progression.yml` (~line 480)
- [ ] T028 [US1] Gate "Commit Phase Artifacts" step: add `steps.generate.outputs.gate_result == 'pass' || vars.SPECKIT_CRITICAL_GATE_MODE == 'draft'`
  AND `steps.generate.outcome == 'success'` to `if:` condition → `speckit-phase-progression.yml` (~line 496) | → T027
- [ ] T029 [US1] Gate "Push Branch" step: add `gate_result` check + `steps.commit.outcome == 'success'` to existing `if:` condition → `speckit-phase-progression.yml` (~line 531) | → T028
- [ ] T030 [US1] Gate "Create Pull Request" step: add `gate_result` check + `steps.commit.outcome == 'success'` to existing `if:` condition → `speckit-phase-progression.yml` (~line 537) | → T029
- [ ] T031 [US1] Write gate test cases in `test_check_analysis_gate.sh`: verify exit code 1 (block mode) for unresolved CRITICALs, exit code 0 for all-resolved CRITICALs, exit code 0 for no CRITICALs
  → `test_check_analysis_gate.sh` | → T022

---

## Phase 4: US2 — Post CRITICAL Gate Failure Comment on Source Issue

- [ ] T032 [US2] Create `critical-gate-failed.md` comment template with `## ❌ SpecKit: CRITICAL Gate Failed` heading, `{{findings_table}}`, workflow run link via
  `{{GITHUB_REPOSITORY}}`/`{{GITHUB_RUN_ID}}`, `{{phase_number}}`, `{{issue_number}}`, and re-trigger instructions → `.github/scripts/speckit-trigger/templates/critical-gate-failed.md`
- [ ] T033 [US2] Extend existing "Handle Failure (Comment + Label)" step (~line 812) in `speckit-phase-progression.yml` to detect `steps.generate.outputs.gate_result == 'fail'` and include CRITICAL
  findings in the failure comment via `critical-gate-failed.md` template | → T032, T027
- [ ] T034 [US2] Format `findings_table` variable from `steps.generate.outputs.critical_findings` JSON for template substitution (markdown table with ID, Summary, Recommendation columns) →
  `speckit-phase-progression.yml` | → T033
- [ ] T035 [US2] Verify `speckit:failed` label application is handled by existing failure handler for gate failures (no new label logic needed — confirm `failure()` condition triggers) | → T033
- [ ] T036 [US2] Ensure gate failure comment respects `SPECKIT_COMMENT_ON_ISSUE` variable (existing handler already checks this — verify no bypass) | → T033
- [ ] T037 [US2] Write test: gate failure comment contains all CRITICAL finding IDs, summaries, and recommendations → `test_check_analysis_gate.sh` | → T034

---

## Phase 5: US4 — Gate Coverage for Monolithic Pipeline Path

- [ ] T038 [US4] Add gate check between Phase 6 (analyze) and Phase 7 (markdownlint) in monolithic orchestration:
  call `check_analysis_gate` with `|| gate_rc=$?` guard → `generate-spec-from-issue.sh` (~line 1976) | → T021
- [ ] T039 [US4] Implement block-mode branching in monolithic path: print CRITICAL findings to stderr and exit non-zero on `gate_rc=10` or `gate_rc=20`, skipping Phase 7 →
  `generate-spec-from-issue.sh` | → T038
- [ ] T040 [US4] Implement draft-mode branching in monolithic path: record `gate_result=fail` + `critical_count` for downstream draft-PR creation, continue to Phase 7 on `gate_rc=10`; exit non-zero on
  `gate_rc=20` → `generate-spec-from-issue.sh` | → T039
- [ ] T041 [US4] Read `SPECKIT_CRITICAL_GATE_MODE` env var (default: `block`) and pass as mode parameter to `check_analysis_gate` in monolithic path → `generate-spec-from-issue.sh` | → T038
- [ ] T042 [US4] Write test: monolithic path exits non-zero after Phase 6 with 1 unresolved CRITICAL finding → `test_check_analysis_gate.sh` | → T040
- [ ] T043 [US4] Write test: monolithic path proceeds to Phase 7 with zero unresolved CRITICALs → `test_check_analysis_gate.sh` | → T040

---

## Phase 6: US3 — Opt-In Draft PR Mode for CRITICAL Findings

- [ ] T044 [US3] Add `--draft` flag to named argument parsing in `create-spec-pr.sh` (~line 52–76) → `.github/scripts/speckit-trigger/create-spec-pr.sh`
- [ ] T045 [US3] Pass `--draft` to `gh pr create` invocation when `--draft` flag is set → `create-spec-pr.sh` | → T044
- [ ] T046 [US3] Output `is_draft=true` to `$GITHUB_OUTPUT` when `--draft` is used → `create-spec-pr.sh` | → T045
- [ ] T047 [US3] Add `--critical-findings-json` argument to `create-spec-pr.sh` for accepting findings payload → `create-spec-pr.sh` | → T044
- [ ] T048 [US3] Prepend `## ⚠️ CRITICAL Findings` warning section to PR body when `--draft` and `--critical-findings-json` are both present → `create-spec-pr.sh` | → T047
- [ ] T049 [US3] Suppress auto-merge in "Auto-Merge (if configured)" step: add `steps.generate.outputs.gate_result != 'fail'` to `if:` condition → `speckit-phase-progression.yml` (~line 620) | → T027
- [ ] T050 [US3] Wire `--draft` + `--critical-findings-json` arguments in "Create Pull Request" step when `SPECKIT_CRITICAL_GATE_MODE == 'draft'` and `steps.generate.outputs.gate_result == 'fail'` →
  `speckit-phase-progression.yml` | → T048, T030
- [ ] T051 [US3] Ensure normal (non-draft) PR created when `SPECKIT_CRITICAL_GATE_MODE=draft` but zero unresolved CRITICALs (no `--draft` flag passed) → `speckit-phase-progression.yml` | → T050
- [ ] T052 [US3] Write test: draft PR created with CRITICAL findings warning section in body → `test_check_analysis_gate.sh` | → T048
- [ ] T053 [US3] Write test: auto-merge suppressed for draft PRs with CRITICALs → `test_check_analysis_gate.sh` | → T049
- [ ] T054 [US3] Write test: normal PR + auto-merge when mode=draft but zero CRITICALs → `test_check_analysis_gate.sh` | → T051

---

## Phase 7: US5 — Structured Gate Output for Programmatic Consumption

- [ ] T055 [US5] Verify `critical_count`, `critical_findings` (JSON array with `id`, `summary`, `recommendation` per object), and `gate_result` are exposed as step outputs from "Generate Phase
  Artifacts" step → `speckit-phase-progression.yml` | → T027
- [ ] T056 [US5] Write test: `GATE_RESULT_JSON:` line contains `gate_result=fail`, `reason=critical_findings_detected`, `critical_count=2`, `report_path` on unresolved CRITICALs →
  `test_check_analysis_gate.sh` | → T022
- [ ] T057 [US5] Write test: `GATE_RESULT_JSON:` line contains `gate_result=pass`, `reason=no_critical_findings`, `critical_count=0` on clean report → `test_check_analysis_gate.sh` | → T022
- [ ] T058 [US5] [P] Write test: `reason=report_missing` when report file absent → `test_check_analysis_gate.sh` | → T022
- [ ] T059 [US5] [P] Write test: `reason=report_parse_error` when report has no Findings Table → `test_check_analysis_gate.sh` | → T022
- [ ] T060 [US5] Write test: `critical_findings` JSON array elements each contain `id`, `summary`, `recommendation` fields → `test_check_analysis_gate.sh` | → T022

---

## Phase 8: Analyzer Prompt Contract Update

- [ ] T061 [US1] Add explicit RESOLVED format contract instruction block to analyze phase LLM prompt: "When a finding has been addressed, change its severity cell to `~~ORIGINAL_SEVERITY~~ →
  RESOLVED`" → `generate-spec-from-issue.sh` (~lines 1720–1774) | → T021
- [ ] T062 [US1] Add correct/incorrect resolved format examples to analyze prompt:
  correct `| F-01 | ... | ~~CRITICAL~~ → RESOLVED | ... |`, incorrect `| F-01 | ... | ~~CRITICAL~~ | ... |` → `generate-spec-from-issue.sh` | → T061

---

## Phase 9: Polish & Cross-Cutting

- [ ] T063 [P] Create SC-004 regression script: iterate all 8 existing `analysis-report.md` files in `specs/` and verify `gate_result=pass` for each →
  `.github/scripts/speckit-trigger/test_sc004_regression.sh` | → T020
- [ ] T064 [P] E2E integration test: run gate CLI wrapper against synthetic spec dir with unresolved CRITICALs, verify exit code 1 in block mode → `test_check_analysis_gate.sh` | → T020
- [ ] T065 [P] E2E integration test: run `create-spec-pr.sh --draft --critical-findings-json '...'` in dry-run and verify PR body contains CRITICAL findings section → `test_check_analysis_gate.sh` | →
  T048
- [ ] T066 Verify gate check completes in <5s against largest fixture (NFR-001 performance validation) | → T022
- [ ] T067 Review all console banners use `## ❌ SpecKit: CRITICAL Gate Failed` / `## ✅ SpecKit: CRITICAL Gate Passed` consistently (NFR-003) | → T018, T032
- [ ] T068 Verify Findings Table is source of truth over Metrics section: test with `analysis-report-metrics-zero-but-table-critical.md` fixture returns `gate_result=fail` | → T022, T010
- [ ] T069 Verify bare `~~CRITICAL~~` without RESOLVED marker treated as unresolved: test with `analysis-report-strikethrough-no-resolved.md` fixture returns `gate_result=fail` | → T022, T011
- [ ] T070 Run full test suite `test_check_analysis_gate.sh` and SC-004 regression, confirm all pass | → T063, T064, T065

---
*Generated by Copilot SDK (claude-opus-4.6)*
