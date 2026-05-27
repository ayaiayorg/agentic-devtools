# Implementation Plan: Improve SpecKit Generation Resilience

## Technical Context

- **Stack**: Bash shell scripts (`.github/scripts/speckit-trigger/`), Python (`copilot_generate.py`), GitHub Actions CI
- **Key Files**:
  - `generate-spec-from-issue.sh` — orchestrator (~3800 lines)
  - `lib/spec-validation.sh` — structural validation library
  - `lib/clarify-retry.sh` — clarify phase multi-layer retry
  - `.specify/presets/agdt-templates/templates/spec-template.md` — LLM template
- **Existing Retry Architecture**: `run_specify_phase_with_validation_retries()` loops up to `SPECIFY_MAX_RETRIES` (default: `3`), uses `_build_structured_specify_feedback()` for retry prompts, and
  `_validate_spec_content()` for validation
- **Validation Checks** (in `validate_spec_quality`): file size, mandatory sections, FR/NFR count, user story count, measurable criteria, bullet ratio
- **Existing Pattern**: `_build_structured_clarify_feedback` in clarify-retry.sh provides the model for adaptive retry enrichment

## Research Summary

See [research.md](research.md) for detailed decisions on:

- Skeleton injection strategy (pre-filled vs. instruction-only)
- Fallback skeleton implementation approach (template-based vs. code-generated)
- Dynamic threshold algorithm
- Example injection timing (retry 2+ only)

## Design Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                   Phase 1: Specify Pipeline                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Compute dynamic threshold (FR-004)                       │
│     └─ Adjust MIN_SPEC_BYTES based on ISSUE_BODY length      │
│                                                              │
│  2. Build specify prompt with skeleton injection (FR-001)     │
│     └─ Mandatory skeleton embedded in prompt template         │
│                                                              │
│  3. Call LLM → sanitize → validate                           │
│     └─ Enhanced sanitizer (FR-006)                           │
│                                                              │
│  4. On failure: adaptive retry with enriched feedback (FR-002)│
│     ├─ Structured failure categories + remediation hints      │
│     ├─ Example injection on retry ≥2 (FR-010)               │
│     └─ Actionable error messages (FR-005)                    │
│                                                              │
│  5. On total exhaustion: deterministic fallback (FR-003)      │
│     └─ Template skeleton + issue-derived content (FR-011)    │
│                                                              │
│  6. Metrics reporting (FR-007)                               │
│     └─ JSON summary to CI logs                               │
│                                                              │
│  7. Post-phase re-validation (FR-009)                        │
│     └─ After specify and clarify phases                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Skeleton Injection & Prompt Improvement (FR-001, FR-008)

**Deliverables**: Modified `run_specify_phase()` with mandatory skeleton in the prompt

**Tasks**:

1. Create a skeleton block containing all 4 mandatory sections as pre-filled headings with structural markers (e.g., `<!-- FILL: minimum 5 FR-### entries -->`)
2. Inject the skeleton into the specify prompt between the instructions and template reference sections
3. Add explicit instructions about prose-to-bullet ratio (MAX_BULLET_LINE_PCT reference)
4. Update `run_specify_phase_with_feedback()` to also include the skeleton on retries
5. Write tests in `test_specify_retry.sh` verifying skeleton presence in generated prompts

### Phase 2: Dynamic Threshold Adaptation (FR-004)

**Deliverables**: New function `_compute_dynamic_thresholds()` in `spec-validation.sh`

**Tasks**:

1. Add `AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR` env var (default: `0.6`, NFR-005)
2. Implement `_compute_dynamic_thresholds()` that:
   - Measures `ISSUE_BODY` character length
   - If < 200 chars → reduces `MIN_SPEC_BYTES` by factor (floor = default × 0.6 = 1229)
   - Leaves `MIN_FUNCTIONAL_REQUIREMENTS` and `MIN_USER_STORIES` unchanged
3. Call `_compute_dynamic_thresholds` at start of `run_specify_phase_with_validation_retries()`
4. Add test cases for threshold computation edge cases
5. Add validation of the reduction factor env var (0.0–1.0 range)

### Phase 3: Enhanced Sanitizer (FR-006)

**Deliverables**: Improved `strip_llm_preamble()` and `ensure_heading_start()`

**Tasks**:

1. Add BOM marker detection (`\xEF\xBB\xBF`) to `strip_llm_preamble` — strip before evaluating first line
2. Add multi-line preamble detection: if first 1–3 lines are conversational but line 2–4 is a heading, strip only the preamble lines
3. Improve `_is_valid_md_start` to recognize indented headings (up to 3 spaces, per CommonMark)
4. Suppress the "default prepended" warning when content already starts with valid heading after whitespace trimming
5. Add contract tests in `test_spec_validation.sh` for BOM, whitespace, and acknowledgment-line cases

### Phase 4: Adaptive Retry Enrichment (FR-002, FR-010)

**Deliverables**: Enhanced `_build_structured_specify_feedback()` and example injection

**Tasks**:

1. Extend `_build_structured_specify_feedback()` to include per-category remediation suggestions (not just failure descriptions)
2. Add specific guidance per failure type:
   - `MISSING_SECTIONS` → list exact headings needed with example content
   - `BELOW_SIZE_THRESHOLD` → instruct to expand each section with prose paragraphs
   - `INSUFFICIENT_REQUIREMENTS` → show FR-### format example
   - `BULLET_SUMMARY_DETECTED` → show prose paragraph conversion example
3. Create `_get_specify_example_spec()` function that returns a truncated valid spec example
4. In `run_specify_phase_with_feedback()`, inject the example when `specify_retry_count >= 2`
5. Store the example spec as a static file (e.g., `.github/scripts/speckit-trigger/templates/example-valid-spec.md`)
6. Update existing tests and add new tests for enriched feedback content

### Phase 5: Deterministic Fallback Skeleton (FR-003, FR-011)

**Deliverables**: New function `_generate_fallback_skeleton()` in `spec-validation.sh`

**Tasks**:

1. Implement `_generate_fallback_skeleton()` that:
   - Takes `ISSUE_TITLE`, `ISSUE_BODY`, `ISSUE_NUMBER`, `ISSUE_URL` as inputs
   - Produces all 4 mandatory sections populated with issue-derived content
   - Generates ≥5 FR-### entries by extracting keywords/phrases from title+body
   - Generates ≥3 user story sections with Given/When/Then (synthesized from title)
   - Includes SC-### entries with measurable targets
   - Adds a visible fallback banner at top: `> ⚠️ **FALLBACK SKELETON** ...`
   - Adds guidance about which sections need manual enrichment
2. Integrate into `run_specify_phase_with_validation_retries()` — call after retry exhaustion instead of returning 1
3. Validate that fallback output passes `validate_spec_quality()` (self-test in function)
4. Ensure execution completes in < 1 second with no network calls (NFR-004)
5. Add comprehensive tests for fallback content correctness

### Phase 6: Actionable Error Feedback (FR-005)

**Deliverables**: Enhanced error output format in `validate_spec_quality()`

**Tasks**:

1. Extend the existing structured output format to include a `REMEDIATION:` suffix for each failure line
2. Format: `CATEGORY: detail | REMEDIATION: actionable suggestion`
3. Update `_build_structured_specify_feedback()` to parse and include remediation hints
4. Ensure human-readable formatting with emoji prefixes for log output (NFR-003)
5. Update test assertions for new output format (backward-compatible — existing parsers ignore the suffix)

### Phase 7: Metrics Reporting (FR-007)

**Deliverables**: New function `_report_specify_metrics()` and CI log output

**Tasks**:

1. Add counter variables: `specify_first_attempt_pass`, `specify_total_retries`, `specify_fallback_used`, `specify_failure_reasons`
2. At end of `run_specify_phase_with_validation_retries()`, emit JSON metrics to stderr
3. Format: `{"first_attempt_success": true/false, "total_attempts": N, "fallback_activated": bool, "failure_reasons": [...]}`
4. Output to GITHUB_OUTPUT for CI visibility: `specify_metrics=<json>`
5. Add tests verifying metrics output format

### Phase 8: Post-Phase Re-Validation (FR-009)

**Deliverables**: Re-validation call after clarify phase

**Tasks**:

1. After `run_clarify_phase()` completes, call `validate_spec_quality()` on the updated `spec.md`
2. If post-clarify validation fails, log a warning but do not block (clarify has its own retry logic)
3. Emit the validation result as part of metrics
4. Add integration test verifying re-validation runs after clarify

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Skeleton injection confuses LLM into not replacing markers | Medium | High | Use clear `<!-- FILL: ... -->` comments; test with multiple models |
| Fallback skeleton too generic to be useful | Low | Medium | Extract keywords from issue body; include fallback banner for awareness |
| Dynamic threshold allows invalid specs through | Low | Medium | Only reduce MIN_SPEC_BYTES; keep FR/US counts fixed |
| Example injection bloats prompt context | Low | Low | Truncate example to ~1500 chars; only inject on retry ≥2 |
| Breaking backward compatibility with existing parsers | Low | High | Extend output format additively; existing parsers ignore new fields |
| BOM handling breaks on non-UTF-8 files | Very Low | Low | Only strip known BOM sequences; pass through unknown encodings |

## Dependencies

- **Internal**: `spec-validation.sh`, `generate-spec-from-issue.sh`, `clarify-retry.sh`, spec template
- **External**: None (all changes are in bash scripts with no new dependencies)
- **Testing**: `test_specify_retry.sh`, `test_spec_validation.sh` (existing test infrastructure)
- **CI**: `.github/workflows/speckit-issue-trigger.yml` (no workflow changes needed; env vars suffice)

---
*Generated by Copilot SDK (claude-opus-4.6)*
