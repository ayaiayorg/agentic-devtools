# Implementation Plan: Resilient Error Handling and Retry Logic for SpecKit Pipeline Scripts

## Technical Context

- **Language**: Bash (shell scripts targeting `bash 4+` with `set -euo pipefail`)
- **Platform**: GitHub Actions runners (Ubuntu)
- **Key dependencies**: `gh` CLI, `curl`, `jq`, GitHub REST API
- **Repository path**: `.github/scripts/speckit-trigger/`
- **Existing retry logic**: `call_with_retry` function inline in `generate-spec-from-issue.sh` (around line 271)
- **Issue**: [#1326](https://github.com/ayaiayorg/agentic-devtools/issues/1326)
- **Branch**: `speckit/1326/phase-3-plan`

## Research Summary

See [spec.md](spec.md) for detailed decisions on:

- Shared library sourcing strategy (`BASH_SOURCE[0]`-relative)
- Non-retryable pattern detection approach
- HTTP-aware vs. exit-code-based retry separation
- `Retry-After` header parsing strategy

## Design Overview

```text
.github/scripts/speckit-trigger/
├── lib/
│   └── retry.sh              ← NEW: shared library (call_with_retry + calculate_backoff_delay)
├── create-spec-pr.sh         ← MODIFIED: source lib/retry.sh, wrap gh pr create, add "already exists" recovery
├── post-issue-comment.sh     ← MODIFIED: source lib/retry.sh for backoff, add curl_with_retry wrapper
├── generate-spec-from-issue.sh ← MODIFIED: remove inline call_with_retry, source lib/retry.sh
├── check-analysis-gate-cli.sh ← AUDIT: verify exit-code propagation (no retry needed — local only)
├── sanitize-branch-name.sh    ← AUDIT: already correct (exits non-zero on error)
├── validate-label.sh          ← AUDIT: already correct
└── check-idempotency.sh       ← AUDIT: already correct
```

### Retry Architecture

```text
┌─────────────────────────────────────────┐
│  lib/retry.sh (shared library)          │
│  ├── calculate_backoff_delay()          │
│  │     $1=retry_number (1-based)        │
│  │     $2=initial_delay                 │
│  │     stdout: delay value              │
│  └── call_with_retry()                  │
│        $1=max_attempts                  │
│        $2=initial_delay                 │
│        $@=command                       │
│        Returns: 0 on success, 1 on fail │
└─────────────────────────────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌─────────────────────┐
│ create-spec-pr  │    │ post-issue-comment   │
│ • source lib    │    │ • source lib         │
│ • call_with_retry│    │ • curl_with_retry() │
│   wrapping gh   │    │   (HTTP-aware, uses  │
│ • "already      │    │    calculate_backoff │
│   exists"       │    │    _delay from lib)  │
│   recovery path │    └─────────────────────┘
└─────────────────┘
```

## Implementation Phases

### Phase 1: Create Shared Retry Library (US3)

**Deliverable**: `.github/scripts/speckit-trigger/lib/retry.sh`

1. Create `lib/` directory and `retry.sh` file
2. Implement `calculate_backoff_delay` function:
   - Input: `retry_number` (1-based), `initial_delay`
   - Output (stdout): `initial_delay × 2^(retry_number - 1)`
3. Implement `call_with_retry` function (extracted from `generate-spec-from-issue.sh`):
   - Same interface: `call_with_retry <max_attempts> <initial_delay> <command...>`
   - Enhanced error messages: include command name and exit code (FR-010)
   - Use `calculate_backoff_delay` internally for consistency
   - Log format: `"Attempt N/M failed (exit E). Command: '<cmd>', retrying in Ds..."` (FR-009)
   - Terminal failure: `"All M attempts failed. Command: '<cmd>', last exit code: E"` (FR-010)
4. Add sourcing guard (idempotent — safe to source multiple times)
5. Ensure portability: use `BASH_SOURCE[0]`-relative path resolution (FR-007)

### Phase 2: Harden `create-spec-pr.sh` (US1)

**Deliverable**: Modified `create-spec-pr.sh` with retry and proper exit codes

1. Source `lib/retry.sh` via `BASH_SOURCE[0]`-relative path
2. Wrap `gh pr create` failure path with retry logic (currently the script exits non-zero on failure without retrying)
3. Add non-retryable pattern detection function:
   - Check exit code 127 → fail immediately
   - Grep stderr for: `"not found"`, `"does not exist"`, `"permission denied"`, `"authentication"`, `"command not found"`
   - If match → fail immediately without retry
4. Wrap `gh pr create` with `call_with_retry` using a local wrapper function that:
   - Captures both stdout and stderr
   - Applies non-retryable pattern check on failure
   - Returns appropriate exit code
5. Add "already exists" recovery path (FR-013):
   - Detect "already exists" in stderr
   - Attempt recovery via `call_with_retry` wrapping `gh pr list --head <branch> --json url,number --jq '.[0]'`
   - Recovery wrapper treats empty/null output as failure (forces retry)
   - On success: extract URL/number, write to `GITHUB_OUTPUT`, exit 0
   - On failure after retries: write empty values, exit non-zero
6. Ensure `GITHUB_OUTPUT` fallback to `/dev/stdout` is preserved
7. Ensure empty `pr_url=` and `pr_number=` are written on all failure paths (NFR-005)

### Phase 3: Harden `post-issue-comment.sh` (US2)

**Deliverable**: Modified `post-issue-comment.sh` with HTTP-aware retry

1. Source `lib/retry.sh` via `BASH_SOURCE[0]`-relative path
2. Implement `curl_with_retry` function:
   - Parameters: `max_attempts`, `initial_delay`, plus curl args
   - Uses `curl -s -o <tmpfile> -w '%{http_code}' -L --post301 --post302 --post303` (FR-011)
   - Captures HTTP status code and response body separately
   - Retry classification:
     - **2xx**: success → return 0
     - **5xx**: retryable → retry
     - **429**: always retryable; parse `Retry-After`, use `max(Retry-After, backoff)`; if `Retry-After > 60` → fail immediately (NFR-002)
     - **403 with Retry-After**: retryable rate-limit; same logic as 429
     - **403 without Retry-After**: non-retryable → fail immediately
     - **4xx (other)**: non-retryable → fail immediately
   - Transport-level curl exit codes:
     - Retryable: 6, 7, 28, 35, 52, 56
     - All others: non-retryable → fail immediately
   - Uses `calculate_backoff_delay` from shared library for delay computation
   - Logs attempt/total/delay on each retry (FR-009)
   - Logs command name and HTTP status or exit code on failure (FR-010)
3. Replace bare `curl -s` call with `curl_with_retry`
4. Ensure non-zero exit on persistent failure (FR-004)

### Phase 4: Migrate `generate-spec-from-issue.sh` (US3-S3)

**Deliverable**: Modified `generate-spec-from-issue.sh` sourcing shared library

1. Add source statement: `. "$SCRIPT_DIR/lib/retry.sh"`
2. Remove inline `call_with_retry` function definition (search for `call_with_retry()`)
3. Verify all existing `call_with_retry` call sites still work
4. Behavioral change: enhanced error messages now include command name (FR-010)

### Phase 5: Audit Remaining Scripts (US4)

**Deliverable**: Audit report and any necessary fixes

Scripts making external network calls (need retry):

- `generate-spec-from-issue.sh` — handled in Phase 4
- `create-spec-pr.sh` — handled in Phase 2
- `post-issue-comment.sh` — handled in Phase 3
- `check-analysis-gate-cli.sh` — sources `check-analysis-gate.sh` (library, no network calls itself)

Pure local scripts (verify exit-code propagation only):

- `sanitize-branch-name.sh` — ✓ already uses `set -euo pipefail` and `exit 1`
- `validate-label.sh` — ✓ already uses `set -euo pipefail` and `exit 1`
- `check-idempotency.sh` — ✓ already uses `set -euo pipefail` and `exit 1`

Test harnesses (excluded from scope):

- `test_check_analysis_gate.sh`, `test_content_preservation.sh`, `test_markdownlint_validation.sh`, `test_sc004_regression.sh`

**Expected finding**: All local scripts already propagate failures correctly via `set -euo pipefail`.

### Phase 6: Testing

**Deliverable**: Test scripts validating all acceptance scenarios

1. Create test script for `lib/retry.sh`:
   - Test `calculate_backoff_delay` arithmetic
   - Test `call_with_retry` with a command that fails N times then succeeds
   - Test `call_with_retry` with a command that always fails
   - Test enhanced error message format
2. Create test script for `create-spec-pr.sh` retry behavior:
   - Stub `gh` to simulate transient failures, non-retryable patterns, "already exists"
   - Verify exit codes and `GITHUB_OUTPUT` content
3. Create test script for `post-issue-comment.sh`:
   - Mock HTTP endpoint (or stub curl) for various status codes
   - Verify retry behavior for 5xx, 429, 403±Retry-After, 4xx
   - Verify transport error handling (exit codes 6, 7, 28, etc.)
4. Structural verification tests (grep-based acceptance scenarios from US1-S7 and US2-S17)

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing `generate-spec-from-issue.sh` behavior during migration | High | Low | Retain identical interface; only error messages change |
| `BASH_SOURCE[0]` path resolution fails in unusual invocation contexts | Medium | Low | FR-007 test validates cross-directory invocation |
| `gh pr create` stderr format changes in future `gh` versions | Low | Medium | Pattern list is conservative; unknown patterns default to retryable |
| Retry delays slow down CI when API is persistently down | Medium | Low | NFR-001 caps at 3 attempts (5s + 10s = 15s max delay); NFR-002 caps Retry-After at 60s |
| "already exists" recovery via `gh pr list` returns stale data | Low | Low | Recovery uses `call_with_retry` to handle eventual consistency |

## Dependencies

- **Internal**: No changes to Python package code; shell scripts only
- **External**: `gh` CLI (already required), `curl` (already required), `jq` (already required)
- **CI**: No workflow YAML changes needed (scripts are called by existing workflow steps)
- **Backward compatibility**: `GITHUB_OUTPUT` fallback to `/dev/stdout` preserved for local testing

---
*Generated by Copilot SDK (claude-opus-4.6)*
