# Tasks: SpecKit Pipeline Markdownlint Validation

> Source: [spec.md](spec.md) · [plan.md](plan.md)
>
> **User Stories**:
>
> - **US1** (P1): Auto-fix resolution — `markdownlint-cli2 --fix` resolves fixable violations automatically
> - **US2** (P1): LLM semantic remediation — remaining violations are fixed via LLM with full-file context
> - **US3** (P2): Exhaustion failure handling — validation loop terminates as a failure after exhaustion/max iterations and reports remaining violations
> - **US4** (P3): Iteration logging — per-iteration summaries with violation counts and file lists

## Task Group 1: Setup

- [ ] T001 Document integration assumptions: identify `generate-spec-from-issue.sh`
  orchestration insertion points (lines 655–719), list the existing helpers to be reused
  (`call_llm`, `strip_model_footer`, `append_model_footer`), and record any
  `.markdownlint-cli2.jsonc` constraints the loop must preserve — output as inline
  comments in the implementation PR or a short note in the PR description
- [ ] T002 Add `MARKDOWNLINT_MAX_ITERATIONS` env var handling near the top of
  `generate-spec-from-issue.sh` (alongside existing env vars, ~line 36–39) with default value `5`
  — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`

## Task Group 2: Foundational — Core Loop Infrastructure

- [ ] T003 Implement `parse_markdownlint_output` helper function in `generate-spec-from-issue.sh` that parses
  markdownlint-cli2 stdout/stderr in `filename:line:col rule/alias description` format into structured violation
  records containing `filename`, `line`, `col`, `rule`, and `description`
  — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T001
- [ ] T004 Implement `compute_violation_fingerprint` helper function that produces a deterministic hash/string
  from sorted normalized violations for stall detection, using stable identity fields (`filename`, `line`,
  `col`, `rule`); keep `description` available from T003 for iteration logging and LLM prompting context
  — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T003
- [ ] T005 Implement `check_npx_available` guard function that checks `command -v npx` and
  returns 1 with a warning to stderr if unavailable
  — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T001

## Task Group 3: US1 — Auto-Fix Resolution (P1)

- [ ] T006 [US1] Write auto-fix validation test in
  `.github/scripts/speckit-trigger/test_markdownlint_validation.sh`:
  create a temp spec dir with known auto-fixable violations (trailing spaces,
  inconsistent list markers), run `npx markdownlint-cli2 --fix`, then run
  `npx markdownlint-cli2` and assert exit code 0 on re-lint — executed
  manually during development and optionally in CI
  - Depends on: T001
- [ ] T007 [US1] Implement auto-fix pass inside `run_markdownlint_validation`:
  run `npx markdownlint-cli2 --fix "$SPEC_DIR/**/*.md"` as the first action each iteration
  — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T002, T005
- [ ] T008 [US1] Implement check-only pass after auto-fix:
  run `npx markdownlint-cli2 "$SPEC_DIR/**/*.md"` capturing output;
  if exit code 0, break loop (all clean)
  — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T007, T003
- [ ] T009 [US1] Verify auto-fix-only path: when all violations are auto-fixable, loop exits after iteration 1 with zero LLM calls — integration validation
  - Depends on: T008

## Task Group 4: US2 — LLM Semantic Remediation (P1)

- [ ] T010 [US2] Write LLM-required validation test in
  `.github/scripts/speckit-trigger/test_markdownlint_validation.sh`:
  create a temp spec dir with a semantic violation that `--fix` cannot resolve
  (e.g., heading hierarchy skip `# H1` → `### H3`), verify it persists after
  auto-fix — executed manually during development
  - Depends on: T008
- [ ] T011 [US2] Implement per-file LLM prompt construction: strip footer via
  `strip_model_footer`, build prompt with full file content + violation list,
  enforce <8K token budget
  — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T003, T004
- [ ] T012 [US2] Implement LLM remediation loop body: for each file with remaining violations,
  call `call_llm` with the per-file prompt, write corrected content back,
  re-append footer via `append_model_footer` — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T011
- [ ] T013 [US2] Implement LLM failure handling: if `call_llm` returns non-zero for a file,
  log warning to stderr and continue to next file (do not abort loop)
  — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T012
- [ ] T014 [US2] Implement stall detection: compare `compute_violation_fingerprint`
  of current iteration with previous; if identical, break loop with warning
  — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T004, T012
- [ ] T015 [US2] Verify LLM remediation path: semantic violation is resolved after LLM pass, footer is preserved, file content is correct — integration validation
  - Depends on: T012, T014

## Task Group 5: US3 — Exhaustion Failure Handling (P2)

- [ ] T016 [US3] Implement max iteration exhaustion handling: when loop counter exceeds `MARKDOWNLINT_MAX_ITERATIONS`,
  log remaining violation count and exit function with non-zero return code
  — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T014
- [ ] T017 [US3] Implement npx unavailability guard at top of
  `run_markdownlint_validation`: call `check_npx_available`, if false log actionable
  error and return non-zero immediately
  — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T005, T007
- [ ] T018 [US3] Verify exhaustion failure: set `MARKDOWNLINT_MAX_ITERATIONS=1`
  with an unfixable violation, confirm function returns non-zero and pipeline
  stops with diagnostics — integration validation
  - Depends on: T016

## Task Group 6: US4 — Iteration Logging (P3)

- [ ] T019 [US4] [P] Implement per-iteration logging to stderr:
  iteration number (`[Phase 7] Iteration N/MAX`), violation count,
  list of affected files
  — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T008
- [ ] T020 [US4] [P] Implement summary logging at loop exit: total iterations run,
  final violation count (0 if clean), whether stall was detected,
  whether max iterations were reached
  — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T016
- [ ] T021 [US4] Verify logging output: run validation with known violations, confirm stderr contains iteration-by-iteration summaries with correct counts — integration validation
  - Depends on: T019, T020

## Task Group 7: Orchestration Integration

- [ ] T022 Wire `run_markdownlint_validation` call into orchestration section of `generate-spec-from-issue.sh` as Phase 7,
  after Phase 6 (Analyze, ~line 691) and before `GITHUB_OUTPUT` writes (~line 703)
  — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T016, T017, T019, T020
- [ ] T023 Update phase numbering in echo statements from `Phase N/6` to
  `Phase N/7` for all existing phases, and add `Phase 7/7: Markdownlint Validation` echo
  — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T022
- [ ] T024 Update script header comment to document the new Phase 7 and `MARKDOWNLINT_MAX_ITERATIONS` env var — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T023
- [ ] T025 Verify `$SPEC_DIR` scoping: place a deliberately-violated `.md` file outside `$SPEC_DIR`, run validation, confirm it is NOT modified — integration validation
  - Depends on: T022

## Task Group 8: Polish & Cross-Cutting

- [ ] T026 [P] Create or update `specs/1191-speckit-pipeline-markdownlint-validation/quickstart.md` to document final usage, function name, env var, and any deviations from plan
  - Depends on: T024
- [ ] T027 [P] Run full pipeline end-to-end (`generate-spec-from-issue.sh`) with a real issue to validate Phase 7 integrates cleanly with Phases 1–6
  - Depends on: T022
- [ ] T028 [P] Measure and document the "first-push pass rate" success metric
  using pipeline/workflow logs from representative first-push executions;
  record sample size, pass/fail counts, computed rate, and whether the ≥90% target
  is met or remains aspirational
  - Depends on: T027
- [ ] T029 [P] Verify timing: common-case run (auto-fix only) completes in ≤120s;
  worst-case run (max iterations with LLM) completes in ≤600s
  - Depends on: T027
- [ ] T030 Verify no regressions: existing spec artifacts (spec.md, plan.md,
  tasks.md, analysis-report.md, checklists/) are unchanged when validation loop
  finds zero violations
  - Depends on: T027
- [ ] T031 [US3] Implement empty-spec-directory guard: before running markdownlint,
  check that `$SPEC_DIR` contains at least one `*.md` file; if none exist,
  log success and return 0 immediately (per EC9)
  — `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  - Depends on: T007

---

> **Note — gitignored artifacts**: The PR description (auto-generated by the SpecKit
> GitHub Action) links to `quickstart.md`, `research.md`, and `contracts/` as
> generated artifacts, but these files are gitignored (`.gitignore` lines 61–64:
> `specs/*/research.md`, `specs/*/quickstart.md`, `specs/*/contracts/`) and cannot
> be committed to the repository. Reviewers should expect those links to return 404.
> `quickstart.md` creation is tracked by T026; `research.md` and `contracts/` are
> generated locally during pipeline runs but are not versioned. To eliminate the
> broken links, the SpecKit PR description template should be updated to only list
> artifacts that are actually committed (tracked in a separate issue).

---
*Generated by Copilot SDK (claude-opus-4.6)*
