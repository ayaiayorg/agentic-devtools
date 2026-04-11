# Implementation Plan: SpecKit Pipeline Markdownlint Validation

## 1. Technical Context

**Technology stack:**

- **Shell**: Bash (uses `set -euo pipefail`)
- **Linter**: `markdownlint-cli2` (invoked via `npx`)
- **Auto-fix**: `markdownlint-cli2 --fix` built-in flag
- **LLM remediation**: Copilot SDK via existing `copilot_generate.py` wrapper + `call_llm` bash function
- **Config**: Root `.markdownlint-cli2.jsonc` (existing, shared across repo)

**Key dependencies:**

- `generate-spec-from-issue.sh` — the main orchestration script; new validation loop inserts after Phase 6 (Analyze)
- `copilot_generate.py` — existing Copilot SDK wrapper used for LLM calls
- `call_llm` / `call_with_retry` — existing bash helpers in `generate-spec-from-issue.sh`
- `strip_model_footer` / `append_model_footer` — existing footer management functions

**Architecture decision**: Single new function (`run_markdownlint_validation`) added to `generate-spec-from-issue.sh`,
called as Phase 7 after all artifacts are generated but before `GITHUB_OUTPUT` is written.
No new files needed for the core loop.

## 2. Research Summary

Key decisions for this implementation:

1. **Auto-fix first, LLM second** — `markdownlint-cli2 --fix` resolves ~80% of violations (whitespace, heading style, list markers) with zero LLM cost
2. **`$SPEC_DIR`-scoped glob** — pass `"$SPEC_DIR/**/*.md"` to markdownlint-cli2 so no files outside the spec directory are touched
3. **Footer strip-before-LLM, re-append-after** — prevents model-attribution footers from being corrupted by LLM edits
4. **Configurable max iterations** — `MARKDOWNLINT_MAX_ITERATIONS` env var (default: 5) with stall detection
5. **Fail fast on exhaustion/stall** — validation loop exits non-zero with clear diagnostics when the maximum iteration count
   is reached or no progress is being made, blocking commit/PR creation until markdownlint issues are resolved

## 3. Design Overview

```text
┌──────────────────────────────────────────────┐
│  generate-spec-from-issue.sh                 │
│                                              │
│  Phase 1: Specify   ─► spec.md               │
│  Phase 2: Clarify   ─► spec.md (updated)     │
│  Phase 3: Checklist ─► checklists/req.md     │
│  Phase 4: Plan      ─► plan.md + extras      │
│  Phase 5: Tasks     ─► tasks.md              │
│  Phase 6: Analyze   ─► analysis-report.md    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ Phase 7: Markdownlint Validation     │    │
│  │                                      │    │
│  │  for i in 1..MAX_ITERATIONS:         │    │
│  │    1. Run markdownlint-cli2 --fix    │    │
│  │    2. If clean → break (done)        │    │
│  │    3. Parse remaining violations     │    │
│  │    4. If same as last → stall break  │    │
│  │    5. Build LLM prompt (<8K tokens)  │    │
│  │    6. For each file with violations: │    │
│  │       - Strip footer                 │    │
│  │       - Send file + violations       │    │
│  │       - Write corrected content      │    │
│  │       - Re-append footer             │    │
│  │    7. Log iteration summary          │    │
│  │  end for                             │    │
│  │  Fail if max iterations exhausted    │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  Output GITHUB_OUTPUT variables              │
└──────────────────────────────────────────────┘
```

### Key Design Constraints

| Constraint | Solution |
|---|---|
| Only `$SPEC_DIR` files may be modified | Explicit glob: `"$SPEC_DIR/**/*.md"` |
| Reuse root markdownlint config | No `--config` needed; `.markdownlint-cli2.jsonc` auto-discovered |
| ≤120s common case | Auto-fix resolves most issues in <5s; 1-2 LLM iterations ≈ 30-60s each |
| ≤600s worst case | Max 5 iterations × ~120s each = max 600s |
| <8K token prompts | Per-file prompts with only the violations and file content |
| Footer preservation | Strip before LLM, re-append after |
| Graceful failure | Loop exits with diagnostics and non-zero return code; pipeline stops |

## 4. Implementation Stages

### Stage 1: Core Validation Loop Function

**Deliverable**: `run_markdownlint_validation` function in `generate-spec-from-issue.sh`

1. Add `MARKDOWNLINT_MAX_ITERATIONS` env var handling (default: 5)
2. Implement the validation loop:
   - Run `npx markdownlint-cli2 --fix "$SPEC_DIR/**/*.md"` (auto-fix pass)
   - Run `npx markdownlint-cli2 "$SPEC_DIR/**/*.md"` (check-only pass, capture output)
   - Parse violations from stderr/stdout (format: `filename:line:col rule/alias description`)
   - Compare violation fingerprint with previous iteration for stall detection
   - If violations remain and not stalled → proceed to LLM remediation
3. Per-iteration logging to stderr with iteration number, violation count, file list

### Stage 2: LLM Remediation Prompt

**Deliverable**: LLM prompt construction and file correction logic

1. Build per-file LLM prompts:
   - Strip model footer from file content
   - Include full file content + markdownlint violation list
   - Instruction: output ONLY the corrected markdown, no commentary
   - Keep under 8K tokens (file content + violations + system prompt)
2. Write corrected content back to file
3. Re-append model footer via `append_model_footer`
4. Handle LLM failure gracefully (log warning, continue to next file)

### Stage 3: Orchestration Integration

**Deliverable**: Wire Pipeline Phase 7 into the main pipeline orchestration

1. Add Pipeline Phase 7 call after Phase 6 (Analyze) and before `GITHUB_OUTPUT`
2. Check `npx` availability; fail with actionable error and non-zero exit if not found (per EC5)
3. Update phase numbering in echo statements (existing are 1-6, new is 7)
4. Ensure the function returns non-zero on exhaustion (fail with diagnostics per FR-013)

### Stage 4: Testing & Validation

**Deliverable**: Manual and automated validation

1. Create a test markdown file with known violations in a temp spec dir
2. Run the validation function standalone to verify:
   - Auto-fix resolves simple issues
   - LLM resolves semantic issues
   - Stall detection works
   - Max iteration cap works
   - Footer preservation works
   - `$SPEC_DIR` scoping is enforced (files outside are untouched)
3. Verify timing: common case ≤120s, worst case ≤600s

## 5. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| LLM introduces new violations | Medium — could stall loop | Medium | Stall detection breaks infinite loops; max iteration cap |
| markdownlint-cli2 not available (npx missing) | Medium — pipeline fails validation | Low | Guard with `command -v npx` check; fail with actionable error and non-zero exit (per EC5) |
| LLM response corrupts markdown structure | High — could break artifacts | Low | Full file content in prompt gives LLM context; footer strip/re-append protects attribution |
| Timeout exceeded (>600s) | Medium — pipeline slow | Low | Max iterations cap; auto-fix resolves most issues in pass 1 |
| Footer regex mismatch after LLM edit | Low — duplicate/missing footer | Medium | `strip_model_footer` + `append_model_footer` are idempotent |

## 6. Dependencies

### External

- `npx` + `markdownlint-cli2` (already in CI environment)
- Copilot SDK via `copilot_generate.py` (already configured with `COPILOT_GITHUB_TOKEN`)

### Internal

- `generate-spec-from-issue.sh` — host script for the new function
- `call_llm` — existing LLM invocation helper (includes retry logic)
- `strip_model_footer` / `append_model_footer` — existing footer management
- `.markdownlint-cli2.jsonc` — root config (auto-discovered by markdownlint-cli2)

---
*Generated by Copilot SDK (claude-opus-4.6)*
