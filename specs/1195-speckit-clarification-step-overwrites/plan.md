# Implementation Plan: SpecKit Clarification Step — Content-Preserving Augmentation

**Issue**: [#1195](https://github.com/ayaiayorg/agentic-devtools/issues/1195)
**Branch**: `speckit/1195/phase-3-plan`

## Technical Context

### Technology Stack

- **Shell**: `generate-spec-from-issue.sh` — 2084-line Bash script orchestrating the SpecKit pipeline (phases 1–5 + markdownlint)
- **Python**: `agentic_devtools` package — CLI commands, speckit agent prompt rendering, context budget enforcement
- **CI/CD**: GitHub Actions workflows (`speckit-issue-trigger.yml`, `speckit-phase-progression.yml`)
- **LLM**: Copilot SDK via `copilot_generate.py` (model: `claude-opus-4.6`, timeout: 600s)
- **Testing**: `agdt-test` / `agdt-task-wait` and related `agdt-test-*` commands (100% coverage required where applicable), shell integration tests, 1:1:1 test structure under `tests/unit/`

### Key Dependencies

- `copilot_generate.py` — LLM invocation wrapper
- `strip_llm_preamble`, `ensure_heading_start`, `append_model_footer` — existing post-processing helpers
- `check-idempotency.sh` — phase 2 idempotency checks (already looks for `## Clarifications` section)
- `speckit.clarify.agent.md` — interactive agent (already implements incremental augmentation correctly)

### Architecture Decisions

The defect is in `run_clarify_phase()` and `run_checklist_phase()` in `generate-spec-from-issue.sh` (lines 1255–1397). Both functions:

1. Read the existing file content
2. Send it to the LLM with instructions to output the "COMPLETE updated specification"
3. **Destructively overwrite** the file with the LLM response (`printf '%s\n' "$result" > "$SPEC_DIR/spec.md"`)

There is **no backup**, **no validation**, and **no atomic replace**. The fix must be surgical — adding safeguards around the existing write path without rearchitecting the pipeline.

## Research Summary

Detailed decisions for this fix are:

- **Backup naming convention** — `spec.md.bak` with `.bak.N` collision avoidance
- **Validation strategy** — section heading + requirement count comparison in Bash
- **Atomic replacement** — `mv` (POSIX rename) from `.tmp` staging file
- **Shared validation contract** — shell functions reusable by both CI and future Python validation
- **Prompt augmentation** — explicit preservation instructions added to LLM prompt

## Design Overview

### Three-Layer Protection Model

```text
┌─────────────────────────────────────────────┐
│ Layer 1: PREVENTION — Improved LLM Prompt   │
│ Explicit instructions to preserve all        │
│ sections and content, not just summarize     │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│ Layer 2: DETECTION — Structural Validation  │
│ Compare staged output against original:      │
│ • Mandatory section headings present         │
│ • All original section headings preserved    │
│ • Requirement entry count ≥95% retained      │
│ • Checklist item count 100% retained         │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│ Layer 3: RECOVERY — Backup + Restore        │
│ Pre-write backup with collision avoidance    │
│ Atomic rename from .tmp staging file         │
│ Automatic restore on post-replace failure    │
└─────────────────────────────────────────────┘
```

### Modified Clarify Phase Flow

```text
run_clarify_phase():
  1. Assert spec.md exists and is non-empty (FR-009)
  2. Warn if spec.md ≥ 50KB (FR-012)
  3. Create backup: spec.md.bak[.N] (FR-002)
  4. Read spec content, count sections + requirements
  5. Send to LLM with augmented prompt (FR-001, FR-003, FR-004)
  6. Write LLM output to spec.md.tmp (FR-006)
  7. Validate staged output against original baseline (FR-006):
     a. All mandatory sections present
     b. All original sections present
     c. Requirement count ≥95% of original
  8. On validation pass → mv spec.md.tmp spec.md (atomic replace)
  9. On validation fail → leave spec.md unchanged, report errors (FR-007)
```

### New Shell Functions

| Function | Purpose | Location |
|---|---|---|
| `create_backup` | Create backup with collision-avoidance naming | `generate-spec-from-issue.sh` |
| `restore_from_backup` | Restore original from backup file | `generate-spec-from-issue.sh` |
| `count_requirement_entries` | Count `FR-###`/`NFR-###` entries in a file | `generate-spec-from-issue.sh` |
| `count_checklist_items` | Count `- [ ]`/`- [x]` items in a file | `generate-spec-from-issue.sh` |
| `extract_section_headings` | Extract all `## ...` headings from a file | `generate-spec-from-issue.sh` |
| `validate_structural_integrity` | Compare staged output vs original | `generate-spec-from-issue.sh` |
| `safe_write_with_validation` | Orchestrate backup → stage → validate → replace | `generate-spec-from-issue.sh` |

## Implementation Phases

### Phase 1: Shell Utility Functions (Foundation)

**Deliverables**: Backup, counting, and validation helper functions

1. **`create_backup <filepath>`** — Create `<filepath>.bak`, with `.bak.N` suffix when collisions exist. Abort with OS-level error on write failure (FR-002). Return the backup path on stdout.

2. **`restore_from_backup <filepath> <backup_path>`** — Copy backup over the original. Used when post-replace validation fails (FR-007).

3. **`count_requirement_entries <filepath>`** — Count lines matching `^-\s+\*\*(FR|NFR)-[0-9]+\*\*:` in a file.
   Use a single `grep -cE` pattern so only valid `FR-###` or `NFR-###` requirement entries are counted. Return count on stdout.

4. **`count_checklist_items <filepath>`** — Count lines matching `^- \[(x| )\]` pattern (Markdown task list items per the Checklist Item Count Definition). Return count on stdout.

5. **`extract_section_headings <filepath>`** — Extract `## ...` headings, normalize by stripping trailing `*(mandatory)*` annotations and trimming whitespace. Return one heading per line on stdout.

6. **`validate_structural_integrity <original_file> <candidate_file> [--type spec|checklist]`** — Compare:
   - Mandatory sections present (for `--type spec`): `## Problem Statement`, `## User Scenarios & Testing`, `## Requirements`, `## Success Criteria`
   - All original section headings preserved
   - Requirement entry retention for `--type spec` must satisfy `retained_count >= ceil(0.95 * original_count)`; checklist item retention for `--type checklist` must satisfy `retained_count >=
     original_count` so all original checklist items are preserved even if additional items are added
   - Skip the retention check only when `original_count` is zero
   - Print specific failure reasons to stderr (NFR-002)
   - Return 0 on pass, 1 on fail

7. **`safe_write_with_validation <original_file> <candidate_content> [--type spec|checklist]`** — Orchestrate the full flow:
   - Create backup
   - Write candidate to `.tmp`
   - Run `validate_structural_integrity`
   - On pass: `mv .tmp original` (atomic replace)
   - On fail: remove `.tmp`, leave original unchanged, report errors
   - Return 0 on success, 1 on validation failure

### Phase 2: Modified Clarify Phase

**Deliverables**: Updated `run_clarify_phase()` with all safeguards

1. **Pre-flight checks** (FR-009):
   - Assert `spec.md` exists: `[[ -f "$SPEC_DIR/spec.md" ]]`
   - Assert non-empty: `[[ -s "$SPEC_DIR/spec.md" ]]`
   - Fail with clear, actionable error messages on either condition

2. **File size warning** (FR-012):
   - Check `stat -c%s` (or `wc -c`) of `spec.md`
   - If ≥50,000 bytes, emit warning to stderr (non-blocking)

3. **Augmented LLM prompt** (FR-001, FR-003, FR-004, FR-005, FR-011):
   - Add explicit preservation instructions at the top of the prompt:

     ```text
     CRITICAL PRESERVATION RULES:
     - You MUST output the COMPLETE specification with ALL sections intact
     - Do NOT summarize, truncate, or omit any section
     - Every section heading from the input MUST appear in your output
     - Every FR-### and NFR-### entry MUST be preserved unless explicitly merged
     - Replace [NEEDS CLARIFICATION] markers in-place with resolved answers
     - Append a ## Clarifications section (or add to existing) with session Q&A
     ```

   - Add the original section heading list and requirement count as a "checklist" in the prompt for the LLM to cross-reference

4. **Replace destructive write with `safe_write_with_validation`**:
   - Replace `printf '%s\n' "$result" > "$SPEC_DIR/spec.md"` with call to `safe_write_with_validation`
   - Pass `--type spec`

### Phase 3: Modified Checklist Phase

**Deliverables**: Updated `run_checklist_phase()` with same safeguards

1. **Pre-flight checks**: Assert `checklists/requirements.md` exists when updating (skip for initial creation during first phase 2 run — the checklist may not exist yet)

2. **Conditional safeguards**: Only apply backup/validation when the file already exists (initial creation skips validation since there's no baseline)

3. **Augmented LLM prompt**: Add preservation instructions for checklist items

4. **Replace destructive write with `safe_write_with_validation`**:
   - Pass `--type checklist`
   - 100% checklist item retention required

### Phase 4: Clarification Audit Trail

**Deliverables**: `## Clarifications` section guaranteed in output (FR-005)

1. **Post-validation augmentation**: After successful write, verify `## Clarifications` section exists in the output. If not (LLM omitted it despite instructions), append a minimal session entry:

   ```markdown
   ## Clarifications

   ### Session YYYY-MM-DD

   - Autonomous clarification pass completed. See inline updates for details.
   ```

2. **`[NEEDS CLARIFICATION]` marker handling** (FR-011): The LLM prompt already instructs replacement. Add a post-write check counting remaining markers and logging a warning if any survive.

### Phase 5: Shell Integration Tests

**Deliverables**: Shell-script-level tests for all new functions

Create `test_content_preservation.sh` in `.github/scripts/speckit-trigger/` (alongside existing `test_markdownlint_validation.sh` and `test_sc004_regression.sh`):

1. **Test `create_backup`**:
   - Creates `.bak` file with correct content
   - Uses `.bak.1`, `.bak.2` suffixes on collision
   - Returns non-zero on write failure (simulate with read-only directory)

2. **Test `count_requirement_entries`**:
   - Counts `FR-###` and `NFR-###` entries correctly
   - Returns 0 for file with no requirements
   - Ignores non-requirement bullets

3. **Test `count_checklist_items`**:
   - Counts `- [ ]` and `- [x]` items
   - Ignores plain bullets `- ...`
   - Returns 0 for empty file

4. **Test `validate_structural_integrity`**:
   - Passes when all sections retained and counts match
   - Fails when mandatory section missing
   - Fails when original section heading missing
   - Fails when requirement count drops below 95%
   - Passes when original has 0 requirements (skip check)
   - Strips `*(mandatory)*` annotations before matching

5. **Test `safe_write_with_validation`**:
   - Successful write: original replaced, backup retained
   - Failed validation: original unchanged, backup exists, `.tmp` cleaned up
   - Backup write failure: aborts without touching original

6. **Test `run_clarify_phase` integration**:
   - Missing `spec.md` → clear error
   - Empty `spec.md` → clear error
   - Truncated LLM response → validation rejects, original preserved
   - Successful augmentation → original replaced, backup retained

7. **Test `run_checklist_phase` integration**:
   - Existing checklist preserved when LLM truncates
   - New checklist created without validation (no baseline)

### Phase 6: Python Unit Tests

**Deliverables**: Python tests verifying the no-content-loss invariant

New test files under `tests/unit/` following the 1:1:1 policy. Since the core logic is in shell, the Python tests focus on:

1. **Validation logic tests** (if we extract any Python validation helpers):
   - `tests/unit/cli/speckit/validation/` — if a shared Python validation module is created for NFR-004 (parity)

2. **Prompt augmentation tests**:
   - Verify the preservation instructions are present in the clarify prompt
   - Verify section headings and counts are injected into the prompt

3. **Integration with existing speckit tests**:
   - Extend `tests/unit/cli/speckit/commands/test_speckit_clarify.py` if the Python command layer changes

### Phase 7: CI Workflow Updates

**Deliverables**: Updated workflow configurations

1. **`speckit-phase-progression.yml`**: No changes expected — the workflow calls `generate-spec-from-issue.sh --phase 2` which internally runs the updated functions

2. **Add shell test execution**: Add a step in CI to run `test_content_preservation.sh` (follow pattern of existing `test_markdownlint_validation.sh`)

3. **Idempotency check update**: Verify `check-idempotency.sh` phase 2 detection still works (it checks for `## Clarifications` section, which will now always be present)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM ignores preservation instructions despite prompt augmentation | Medium | Low (caught by Layer 2 validation) | Validation is the safety net; prompt is defense-in-depth |
| Validation false positive (rejects valid output due to counting edge cases) | Medium | Medium | Comprehensive test suite for counting logic; skip check when baseline is 0 |
| `mv` fails on non-POSIX filesystem | Low | Low | GitHub Actions runners use ext4; add error handling regardless |
| Backup disk space on large specs | Very Low | Low | Backups are tiny (KB); retained for audit per FR-010 |
| Shell function complexity increases maintenance burden | Medium | Medium | Keep functions small and well-documented; add thorough tests |
| Validation overhead exceeds 5s NFR-001 threshold | Very Low | Low | All operations are local file I/O + `grep`; sub-second expected |
| Checklist phase has no baseline on first run | N/A | N/A | Skip validation when file doesn't exist (conditional safeguards) |

## Dependencies

### Internal

- `generate-spec-from-issue.sh` — primary modification target
- `copilot_generate.py` — no changes needed (LLM invocation unchanged)
- `check-idempotency.sh` — verify compatibility with always-present `## Clarifications`
- `speckit-phase-progression.yml` — verify phase 2 step still works
- Existing shell tests (`test_markdownlint_validation.sh`, `test_sc004_regression.sh`) — follow same patterns

### External

- GitHub Actions runner environment (Bash 5.x, GNU coreutils for `stat`, `mv`, `grep`)
- `markdownlint-cli2` (already installed in CI; unaffected by changes)
- Copilot SDK / LLM API (unchanged interface; only prompt content changes)

---
*Generated by Copilot SDK (claude-opus-4.6)*
