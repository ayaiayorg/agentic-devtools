# Tasks — Spec 006: Plan Phase Context Budget Management

## Tasks — Spec 006: Plan Phase Context Budget Management

**Branch**: `006-plan-phase-fails-large` | **Issue**: #1175

## User Story Map

| Label | Story | Priority |
|-------|-------|----------|
| US1 | Passthrough — below-budget content passes through byte-identical | P1 |
| US2 | Reduction — oversized content reduced via deterministic formatting stripping | P1 |
| US3 | Truncation — hard-truncate when reduction alone is insufficient | P1 |
| US4 | Summary-only — drop comments and truncate description as last resort | P2 |
| US5 | Configurable budget — override default via `AGDT_PLAN_CONTEXT_BUDGET` env var | P2 |
| US6 | Content validation — non-empty + substantive shape check | P2 |
| US7 | Permanent failure — clear `ContextBudgetError` when budget cannot be met | P3 |
| US8 | Determinism/reviewability — budget reduction output is deterministic and reviewable | P3 |

---

## Phase Mapping: Plan → Tasks

| Plan Phase | Plan Title | Task Phases | Task IDs |
|------------|-----------|-------------|----------|
| Phase 1 | Core Budget Module (TDD) | Phases 1–2 (Setup + Foundational) | T001–T010 |
| Phase 2 | SpecKit Trigger Integration | Phases 3, 7 (Passthrough + Configurable Budget) | T011–T016, T039–T049 |
| Phase 3 | Reduction Functions Implementation | Phase 4 (Reduction Pipeline) | T017–T028 |
| Phase 4 | Truncation & Summary-Only Stages | Phases 5–6 (Truncation + Summary-Only) | T029–T038 |
| Phase 5 | Validation, Error Handling & Polish | Phases 8–10 (Validation + Failure + Polish) | T050–T066 |

---

## Phase 1: Setup

- [ ] T001 Create module file `agentic_devtools/context_budget.py` with module docstring and `from __future__ import annotations`
- [ ] T002 Create test directory `tests/unit/context_budget/__init__.py`

## Phase 2: Foundational

- [ ] T003 [P] Write tests for `ReductionStage` enum in `tests/unit/context_budget/test_reductionstage.py` —
  verify all four members (`PASSTHROUGH`, `REDUCED`, `TRUNCATED`, `SUMMARY_ONLY`) and `.value` strings
- [ ] T004 [P] Write tests for `ContextBudgetError` in `tests/unit/context_budget/test_contextbudgeterror.py` — verify it subclasses `Exception`, carries message, is raisable/catchable
- [ ] T005 [P] Write tests for `BudgetResult` frozen dataclass in `tests/unit/context_budget/test_budgetresult.py` —
  verify fields, frozen immutability, `stage`/`original_chars`/`final_chars`/`budget` types
- [ ] T006 Implement `ReductionStage` enum in `agentic_devtools/context_budget.py`
- [ ] T007 Implement `ContextBudgetError` exception in `agentic_devtools/context_budget.py`
- [ ] T008 Implement `BudgetResult` frozen dataclass in `agentic_devtools/context_budget.py`
- [ ] T009 Run `tests/unit/context_budget/` — verify T003–T005 pass (GREEN)
- [ ] T010 Run `python scripts/validate_test_structure.py` — verify new test dir is valid

## Phase 3: US1 — Passthrough (P1)

- [ ] T011 Write tests for `enforce_context_budget()` passthrough path in
  `tests/unit/context_budget/test_enforce_context_budget.py` — below budget returns the original string objects unchanged (object identity via `is`),
  exactly-at-budget returns passthrough, stage is `PASSTHROUGH`, `original_chars == final_chars`
- [ ] T012 Implement `enforce_context_budget()` skeleton in `agentic_devtools/context_budget.py` — measure combined
  `len(description) + len(comments)`, return `BudgetResult` with `PASSTHROUGH` when ≤ budget
- [ ] T013 Run passthrough tests — verify GREEN
- [ ] T014 Write integration test for `run_plan_phase()` in `generate-spec-from-issue.sh` — small issue content passes through budget enforcement unchanged to `call_llm()`
- [ ] T015 Add `enforce_context_budget` invocation in `run_plan_phase()` in
  `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` before the `call_llm "$prompt"` call —
  invoke Python budget module to enforce budget on assembled prompt payload
- [ ] T016 Run integration test from T014 — verify GREEN

## Phase 4: US2 — Reduction Pipeline (P1)

- [ ] T017 [P] Write tests for `strip_markdown_formatting()` in
  `tests/unit/context_budget/test_strip_markdown_formatting.py` — headings, bold, italic, links `[text](url)` → `text`,
  horizontal rules; preserves plain text and the content of all three Markdown code formats:
  fenced code blocks (triple backticks), indented code blocks, and inline code spans (single backticks).
  Add explicit assertions for each format so tests verify code content is preserved while Markdown formatting markers are stripped
  according to the function contract
- [ ] T018 [P] Write tests for `remove_image_references()` in
  `tests/unit/context_budget/test_remove_image_references.py` — `![alt](url)`, `<img …>` tags, `!image!` Jira syntax,
  base64 data URIs; preserves all non-image content
- [ ] T019 [P] Write tests for `collapse_whitespace()` in
  `tests/unit/context_budget/test_collapse_whitespace.py` — multiple blank lines → single, trailing spaces removed,
  multiple spaces → single; preserves leading indent and single newlines
- [ ] T020 [P] Implement `strip_markdown_formatting()` in `agentic_devtools/context_budget.py`
- [ ] T021 [P] Implement `remove_image_references()` in `agentic_devtools/context_budget.py`
- [ ] T022 [P] Implement `collapse_whitespace()` in `agentic_devtools/context_budget.py`
- [ ] T023 Run reduction function tests — verify T017–T019 all GREEN
- [ ] T024 Write tests for `enforce_context_budget()` reduction path in
  `tests/unit/context_budget/test_enforce_context_budget.py` — over-budget content with markdown is reduced,
  stage is `REDUCED`, `final_chars ≤ budget`, determinism (identical input → identical output)
- [ ] T025 Wire reduction functions into `enforce_context_budget()` — apply `strip_markdown_formatting()` →
  `remove_image_references()` → `collapse_whitespace()` when over budget; return `BudgetResult` with `REDUCED`
  if now ≤ budget
- [ ] T026 Run reduction path tests — verify GREEN
- [ ] T027 Write integration test for `run_plan_phase()` — oversized issue body with markdown reaches `call_llm()` in reduced form after budget enforcement
- [ ] T028 Run integration test from T027 — verify GREEN

## Phase 5: US3 — Hard Truncation (P1)

- [ ] T029 Write tests for `hard_truncate()` in `tests/unit/context_budget/test_hard_truncate.py` — truncates at
  word boundary, appends `[…truncated]` marker, result ≤ limit, empty string input, limit smaller than marker length
- [ ] T030 Implement `hard_truncate()` in `agentic_devtools/context_budget.py` — find last word boundary before `limit - len(marker)`, append marker
- [ ] T031 Run hard truncate tests — verify GREEN
- [ ] T032 Write tests for `enforce_context_budget()` truncation path in
  `tests/unit/context_budget/test_enforce_context_budget.py` — over-budget content that cannot be sufficiently reduced
  is hard-truncated, stage is `TRUNCATED`, `final_chars ≤ budget`
- [ ] T033 Wire `hard_truncate()` into `enforce_context_budget()` — apply after reduction when still over budget; truncate combined content, return `BudgetResult` with `TRUNCATED`
- [ ] T034 Run truncation path tests — verify GREEN

## Phase 6: US4 — Summary-Only Fallback (P2)

- [ ] T035 Write tests for `enforce_context_budget()` summary-only path in
  `tests/unit/context_budget/test_enforce_context_budget.py` — when truncation still exceeds budget: comments dropped
  (empty string), description truncated to budget, stage is `SUMMARY_ONLY`
- [ ] T036 Write test for input that is only images/whitespace — verify falls through to summary-only stage
- [ ] T037 Implement summary-only stage in `enforce_context_budget()` — drop comments, truncate description to budget via `hard_truncate()`, return `BudgetResult` with `SUMMARY_ONLY`
- [ ] T038 Run summary-only tests — verify GREEN

## Phase 7: US5 — Configurable Budget (P2)

- [ ] T039 Write integration test for `run_plan_phase()` — `AGDT_PLAN_CONTEXT_BUDGET` env var overrides default 32,000
- [ ] T040 Write integration test — invalid (non-numeric) env var value falls back to default with warning to stderr
- [ ] T041 Implement env var reading in `run_plan_phase()` in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` —
  read `AGDT_PLAN_CONTEXT_BUDGET`, pass to Python budget module, fallback to `DEFAULT_CONTEXT_BUDGET` on invalid value
- [ ] T042 Add `DEFAULT_CONTEXT_BUDGET` constant export from `agentic_devtools/context_budget.py` (value: `32_000`)
- [ ] T043 Update environment variable documentation in `.github/copilot-instructions.md` (Environment Variables table)
  to add `AGDT_PLAN_CONTEXT_BUDGET`, its purpose, and the default `32_000` fallback behavior
- [ ] T044 Run env var integration tests — verify GREEN
- [ ] T045 [P] Write integration test for `generate-spec-from-issue.sh` —
  verify budget enforcement is applied to the issue body and comments before `call_llm()` invocation,
  and that oversized content is reduced appropriately
- [ ] T046 [P] Write integration test for `copilot_generate.py` —
  verify that the Python generation path surfaces oversized-input detection and fallback-compatible
  failure signaling back to the shell trigger
- [ ] T047 Wire budget enforcement into `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
  `run_plan_phase()` — call Python budget module before `call_llm()`, use reduced content for the prompt
- [ ] T048 Wire budget enforcement into `.github/scripts/speckit-trigger/copilot_generate.py` —
  ensure generation-time handling for budget-aware prompt submission and oversized-input detection
- [ ] T049 Run SpecKit trigger integration tests — verify GREEN

## Phase 8: US6 — Content Validation (P2)

- [ ] T050 Write tests for `validate_content_shape()` in
  `tests/unit/context_budget/test_validate_content_shape.py` — empty string returns False, whitespace-only returns False,
  punctuation-only/symbol-only returns False, fewer than 3 alphanumeric characters (`[A-Za-z0-9]`) after trimming returns False,
  and content with at least 3 alphanumeric characters anywhere in the trimmed string returns True
- [ ] T051 Implement `validate_content_shape()` in `agentic_devtools/context_budget.py` — explicit rule: valid content must be
  non-empty after trimming and contain at least 3 alphanumeric characters (`[A-Za-z0-9]`); whitespace and punctuation
  do not count toward the threshold
- [ ] T052 Run validation tests — verify GREEN
- [ ] T053 Wire `validate_content_shape()` into `enforce_context_budget()` — check inputs before processing; if
  `description` is empty/non-substantive, treat it as empty for budgeting purposes (do not raise
  `ContextBudgetError` on that basis alone), skip description-preserving stages, and continue stage selection
  using `comments` and the existing summary-only/failure flow; only the explicit Phase 9 conditions raise
  `ContextBudgetError`

## Phase 9: US7 — Permanent Failure (P3)

- [ ] T054 Write tests for `enforce_context_budget()` error path in
  `tests/unit/context_budget/test_enforce_context_budget.py` — budget ≤ 0 raises `ContextBudgetError` immediately,
  negative budget treated as 0, already-minimal content that cannot fit raises `ContextBudgetError`
- [ ] T055 Implement error path in `enforce_context_budget()` — budget ≤ 0 → immediate `ContextBudgetError`; all stages exhausted → `ContextBudgetError` with descriptive message
- [ ] T056 Run error path tests — verify GREEN
- [ ] T057 Write integration test for `run_plan_phase()` in `generate-spec-from-issue.sh` —
  `ContextBudgetError` causes plan phase to fail gracefully with actionable error message
- [ ] T058 Implement graceful error handling in `run_plan_phase()` — catch budget error from Python module, print actionable message, exit with non-zero code
- [ ] T059 Run degraded-path integration test — verify GREEN

## Phase 10: Polish & Cross-Cutting

- [ ] T060 Add diagnostic output in `run_plan_phase()` when reduction occurs — `[Context Budget] Content reduced: {original} → {final} chars (stage: {stage})`
- [ ] T061 Verify determinism — add test asserting identical input produces byte-identical output across two calls
- [ ] T062 [P] Run full test suite — `agdt-test && agdt-task-wait`
- [ ] T063 [P] Run test structure validator — `python scripts/validate_test_structure.py`
- [ ] T064 Run PR checks — `bash scripts/run-pr-checks.sh`
  (lint, format, mypy, coverage, markdownlint)
- [ ] T065 Fix any lint/format/coverage issues found in T062–T064
- [ ] T066 Run final full suite — `agdt-test && agdt-task-wait` — confirm all green

---

## Dependency Graph

```text
T001 ─┬─► T003 ─┐
      ├─► T004 ─┤
T002 ─┴─► T005 ─┴─► T006, T007, T008 ─► T009 ─► T010
                                                    │
T011 ─► T012 ─► T013 ─► T014 ─► T015 ─► T016 ◄────┘
                                            │
T017 ─► T020 ─┐                             │
T018 ─► T021 ─┼─► T023 ─► T024 ─► T025 ─► T026 ─► T027 ─► T028
T019 ─► T022 ─┘                                              │
                                                              │
T029 ─► T030 ─► T031 ─► T032 ─► T033 ─► T034 ◄──────────────┘
                                            │
T035, T036 ─► T037 ─► T038 ◄───────────────┘
                         │
T039, T040 ─► T041, T042, T043 ─► T044 ◄───┘
T045 ─► T047 ─┐
T046 ─► T048 ─┴─► T049
T050 ─► T051 ─► T052 ─► T053
T054 ─► T055 ─► T056 ─► T057 ─► T058 ─► T059
                                          │
T060, T061 ◄─────────────────────────────┘
T062, T063 ─► T064 ─► T065 ─► T066
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
