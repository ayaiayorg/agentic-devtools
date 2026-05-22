# Implementation Plan: Structural Validation and Retry for Phase 1 (Specify)

**Issue**: [#1505](https://github.com/ayaiayorg/agentic-devtools/issues/1505)
**Branch**: `speckit/1505/phase-3-plan`

## Technical Context

- **Technology**: Bash shell scripts (`set -euo pipefail`)
- **Key Files**:
  - `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` — main pipeline orchestrator
  - `.github/scripts/speckit-trigger/lib/clarify-retry.sh` — Phase 2 retry library (reference pattern)
  - `.github/scripts/speckit-trigger/lib/retry.sh` — shared retry library
- **Architecture**: Sourced library pattern with sourcing guards, return-code contracts (0=success, 1=validation fail, 2=operational fail)
- **Existing Functions Used**: `call_llm`, `strip_llm_preamble`, `ensure_heading_start`, `extract_section_headings`, `count_requirement_entries`, `MANDATORY_SECTIONS`
- **Current Flow**: Phase 1 calls `run_specify_phase()` → `strip_llm_preamble` → `ensure_heading_start` → writes directly to disk with no quality validation

## Research Summary

See [research.md](research.md) for decisions on:

- Validation function design (single function vs. multi-function)
- Retry loop placement (inline in orchestrator vs. library function)
- Feedback format (structured categories matching Phase 2 pattern)

## Design Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                   Phase 1 (Specify) Flow                         │
├─────────────────────────────────────────────────────────────────┤
│  run_specify_phase()                                            │
│       ↓                                                         │
│  strip_llm_preamble() + ensure_heading_start()                  │
│       ↓                                                         │
│  ┌──────────────────────────────────┐                           │
│  │  validate_spec_quality()  [NEW]  │ ← lib/spec-validation.sh  │
│  │  - mandatory sections            │                           │
│  │  - FR count ≥ 5                  │                           │
│  │  - user story count ≥ 3          │                           │
│  │  - measurable success criteria   │                           │
│  │  - byte size ≥ 2048              │                           │
│  │  - bullet-point ratio ≤ 80%      │                           │
│  └──────────────┬───────────────────┘                           │
│                 │                                                │
│       PASS? ────┼──── YES → write to disk                       │
│                 │                                                │
│                 NO → _build_structured_specify_feedback()        │
│                      → retry LLM                                 │
│                      (up to SPECIFY_MAX_RETRIES=3)              │
│                 │                                                │
│       EXHAUSTED → exit 1 with failure details to stderr         │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase A: Create `lib/spec-validation.sh` Library

**Deliverable**: New sourceable library file with all validation functions and threshold constants.

**Tasks**:

1. Create `.github/scripts/speckit-trigger/lib/spec-validation.sh` with:
   - Sourcing guard (`_SPEC_VALIDATION_LIB_LOADED`)
   - Threshold constants at the top: `MIN_FUNCTIONAL_REQUIREMENTS=5`, `MIN_USER_STORIES=3`, `MIN_SPEC_BYTES=2048`, `MIN_MEASURABLE_CRITERIA_PCT=50`, `MAX_BULLET_LINE_PCT=80`, `SPECIFY_MAX_RETRIES=3`
   - Function `_count_user_stories <filepath>` — counts headings matching `### User Story` prefix (case-insensitive) that have at least one Given/When/Then acceptance scenario
   - Function `_check_measurable_criteria <filepath>` — checks that ≥50% of `**SC-###**` entries contain a number/percentage/quantitative target
   - Function `_check_bullet_ratio <filepath>` — computes percentage of non-heading, non-blank lines that are bullet points
   - Function `_check_mandatory_sections <filepath>` — verifies all 4 mandatory sections present
   - Function `_count_functional_requirements <filepath>` — counts `**FR-###**` pattern entries
   - Function `validate_spec_quality <filepath>` — orchestrator that runs all checks, outputs structured failure categories on stdout, returns 0/1
   - Function `_build_structured_specify_feedback <filepath> <failures>` — formats failure categories into LLM retry prompt section

2. Add function header comments documenting parameters, return codes, stdout/stderr behavior (NFR-005)

### Phase B: Integrate Validation into Phase 1 Flow

**Deliverable**: Both Phase 1 execution paths (single-phase and sequential) validate before writing.

**Tasks**:

1. Add `source "$SCRIPT_DIR/lib/spec-validation.sh"` near existing library sourcing (line ~141)
2. Refactor the Phase 1 block in `run_single_phase()` (lines 3382-3396) to add validation + retry loop:
   - After `ensure_heading_start`, write content to a temp file
   - Call `validate_spec_quality "$temp_file"`
   - If passes → write to disk (existing behavior)
   - If fails → build structured feedback, re-prompt LLM with full original prompt + failed output + feedback
   - Track retry count (max `SPECIFY_MAX_RETRIES`); operational failures don't count
   - `call_llm` returns `1` on any failure, so `_run_specify_with_validation()` must follow
     the `lib/clarify-retry.sh` convention:
     - Return `2` for LLM/operational failures (empty response or `call_llm` rc≠0)
     - Return `1` for validation failures
   - The retry loop checks wrapper return code (`rc=2` → skip decrement, `rc=1` → decrement)
   - On exhaustion → `exit 1` with final failures on stderr
3. Apply identical logic to the sequential flow (lines 3528-3539)
4. Extract the retry loop into a function `_run_specify_with_validation()` to avoid duplicating it in both paths

### Phase C: Shared Helper Extraction

**Deliverable**: Existing helpers (`extract_section_headings`, `count_requirement_entries`) remain in `generate-spec-from-issue.sh` but new validation-specific logic lives in `lib/spec-validation.sh`.
Phase 2 can source `lib/spec-validation.sh` for shared counting utilities if beneficial.

**Tasks**:

1. Ensure `lib/spec-validation.sh` calls `extract_section_headings` and `count_requirement_entries` (which are defined in the sourcing script) — these are listed as dependencies in the library header
2. Document the dependency contract at the top of `lib/spec-validation.sh` (matching `lib/clarify-retry.sh` pattern)
3. Verify Phase 2 (`run_clarify_phase`) continues to work without changes — `validate_structural_integrity` is independent of the new `validate_spec_quality`

### Phase D: Test Suite

**Deliverable**: `test_spec_validation.sh` with ≥10 test cases covering all validation branches.

**Tasks**:

1. Create `.github/scripts/speckit-trigger/test_spec_validation.sh`
2. Follow the test pattern from `test_clarify_retry.sh` (assert_eq, assert_contains helpers, PASS/FAIL counters)
3. Test cases (minimum 10):
   - T01: Valid spec passes all checks
   - T02: Missing mandatory section fails with MISSING_SECTIONS
   - T03: Below 2048 bytes fails with BELOW_SIZE_THRESHOLD
   - T04: Fewer than 5 FRs fails with INSUFFICIENT_REQUIREMENTS
   - T05: Fewer than 3 user stories fails with INSUFFICIENT_USER_STORIES
   - T06: Non-measurable success criteria fails with NON_MEASURABLE_CRITERIA
   - T07: Bullet-only spec (>80% bullets) fails with BULLET_SUMMARY_DETECTED
   - T08: Exactly 5 FRs passes the FR check (boundary)
   - T09: Multiple failures reported together (compound failure)
   - T10: User story heading variants accepted (case-insensitive prefix matching)
   - T11: User stories without Given/When/Then don't count
   - T12: Overriding threshold constants changes validation behavior
4. Define mock functions for any dependencies (`extract_section_headings`, `count_requirement_entries`, `MANDATORY_SECTIONS`)

### Phase E: Integration Testing

**Deliverable**: Verify end-to-end behavior with mocked LLM.

**Tasks**:

1. Add integration test case that mocks `call_llm` to return underspecified output first, valid output second → verify retry fires once
2. Add integration test case where all retries fail → verify exit code 1 and stderr output
3. Run existing `test_clarify_retry.sh` and `test_content_preservation.sh` to confirm no regressions (SC-005)

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Validation too strict — legitimate specs rejected | High | Configurable thresholds; start conservative, tune based on first 20 runs (SC-003) |
| Validation too lenient — bad specs still pass | Medium | Measurability and bullet-ratio checks address the observed PR #1504 failure mode |
| Retry loop adds significant latency | Low | Only fires when validation fails; NFR-001 ensures <1s validation overhead in pass case |
| Breaking Phase 2 clarify behavior | High | Phase 2 uses `validate_structural_integrity` (original-vs-candidate), completely independent of new `validate_spec_quality` (absolute threshold); existing tests serve as regression guard |
| Shell function dependencies not available when sourcing | Medium | Document dependency contract in library header; fail fast with clear error on missing functions |

## Dependencies

### Internal

- `generate-spec-from-issue.sh` — provides `call_llm`, `strip_llm_preamble`, `ensure_heading_start`, `extract_section_headings`, `count_requirement_entries`, `MANDATORY_SECTIONS`
- `lib/retry.sh` — may reuse `calculate_backoff_delay` for retry timing (optional)
- `lib/clarify-retry.sh` — reference implementation for structured feedback pattern

### External

- None — pure shell implementation with no external dependencies beyond standard POSIX utilities (`grep`, `awk`, `wc`, `sed`)

---
*Generated by Copilot SDK (claude-opus-4.6)*
