# Implementation Plan: SpecKit Label Operations Token Fix

## 1. Technical Context

**Stack**: Bash shell scripts (`.github/scripts/speckit-trigger/`), GitHub Actions workflow YAML (`.github/workflows/`), `gh` CLI for GitHub API interaction.

**Key files**:

| File | Role |
| --- | --- |
| `.github/scripts/speckit-trigger/create-spec-pr.sh` | Main script — PR creation + label operations (lines 572–605 are the fix target) |
| `.github/scripts/speckit-trigger/lib/retry.sh` | Shared retry library (already exists, reusable) |
| `.github/workflows/speckit-issue-trigger.yml` | Issue-trigger workflow — calls `create-spec-pr.sh` (line 327: `GH_TOKEN` env) |
| `.github/workflows/speckit-phase-progression.yml` | Phase-progression workflow — calls `create-spec-pr.sh` (line 542: `GH_TOKEN` env) |

**Root cause**: Both workflows set `GH_TOKEN` to `SPECKIT_PR_TOKEN || COPILOT_GITHUB_TOKEN` (a PAT for PR creation).
Label operations (`gh label create`, `gh pr edit --add-label`) use this token implicitly via `GH_TOKEN`,
but it lacks `issues: write` scope. The job-level `permissions: issues: write` grants `GITHUB_TOKEN` the required scope,
but `GITHUB_TOKEN` is never passed to the script for label ops. All label errors are suppressed via `2>/dev/null`.

## 2. Research Summary

See [research.md](research.md) for detailed analysis. Key decisions:

- **Token mechanism**: Add `LABEL_TOKEN` as a workflow-level `env:` variable mapped to `${{ secrets.GITHUB_TOKEN }}` — no new CLI parameters
- **Retry reuse**: Leverage existing `lib/retry.sh` (`call_with_retry`) for label operation retries
- **Batch strategy**: `gh label create --force` per-label (no batch API), then single `gh pr edit --add-label` with comma-separated labels
- **Preflight check**: `gh label list --limit 1` using effective token — best-effort, cannot distinguish read vs. write

## 3. Design Overview

```text
┌─────────────────────────────┐
│  Workflow YAML (env block)  │
│  LABEL_TOKEN = GITHUB_TOKEN │
│  GH_TOKEN = PAT             │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│         create-spec-pr.sh               │
│                                         │
│  1. Resolve effective label token       │
│     (LABEL_TOKEN → fallback GH_TOKEN)   │
│                                         │
│  2. Preflight: gh label list --limit 1  │
│     • 401/403 → exit                    │
│     • 5xx/network → warn, continue      │
│                                         │
│  3. Deduplicate labels                  │
│                                         │
│  4. Ensure labels exist (per-label)     │
│     gh label create --force (with retry)│
│                                         │
│  5. Batch apply labels                  │
│     gh pr edit --add-label (with retry) │
│     Fallback → individual apply         │
│                                         │
│  All stderr visible (no 2>/dev/null)    │
│  Structured error messages (NFR-002)    │
└─────────────────────────────────────────┘
```

## 4. Implementation Phases

### Phase 1: Workflow YAML Changes (FR-002)

**Deliverable**: Both workflow files expose `LABEL_TOKEN` in the `env:` block of the "Create Pull Request" step.

**Changes**:

1. **`.github/workflows/speckit-issue-trigger.yml`** — Add `LABEL_TOKEN: ${{ secrets.GITHUB_TOKEN }}` to the `env:` block at line ~326 (the `create-pr` step).
2. **`.github/workflows/speckit-phase-progression.yml`** — Add `LABEL_TOKEN: ${{ secrets.GITHUB_TOKEN }}` to the `env:` block at line ~541 (the `create-pr` step).

No other workflow changes are needed. `GH_TOKEN` remains `SPECKIT_PR_TOKEN || COPILOT_GITHUB_TOKEN` for PR creation.

### Phase 2: Token Resolution & Preflight (FR-001, FR-009, FR-010)

**Deliverable**: `create-spec-pr.sh` resolves the effective label token and
sanity-checks authentication (detects 401/403 early) before label operations.
The preflight (`gh label list --limit 1`) exercises read access only and cannot
distinguish read vs. write permissions. Actual `issues: write` verification is
deferred to the write operations in Phase 3 — a 403 from `gh label create` or
`gh pr edit --add-label` is treated as a non-retriable hard failure with a clear
diagnostic.

**Changes in `create-spec-pr.sh`**:

1. **Add token resolution block** (after line 128, after `GH_TOKEN` validation):

    ```bash
    # Resolve effective label token (FR-001, FR-010)
    if [[ -n "${LABEL_TOKEN:-}" ]]; then
        EFFECTIVE_LABEL_TOKEN="$LABEL_TOKEN"
    else
        echo "Warning: LABEL_TOKEN not set, falling back to GH_TOKEN — label operations may fail if this token lacks issues: write permission." >&2
        EFFECTIVE_LABEL_TOKEN="$GH_TOKEN"
    fi
    ```

2. **Add preflight check function** (before the label application section, ~line 570):

    ```bash
    _preflight_label_token() {
        local exit_code=0
        local stderr_tmp
        stderr_tmp=$(mktemp)
        GH_TOKEN="$EFFECTIVE_LABEL_TOKEN" gh label list --repo "$REPO_SLUG" --limit 1 > /dev/null 2>"$stderr_tmp" || exit_code=$?
        local stderr_content
        stderr_content=$(cat "$stderr_tmp")
        rm -f "$stderr_tmp"

        if [[ $exit_code -ne 0 ]]; then
            if echo "$stderr_content" | grep -qiE '(401|403|permission|unauthorized|forbidden)'; then
                echo "Error: Label token lacks required permissions (HTTP auth/permission error)." >&2
                echo "  Ensure LABEL_TOKEN uses GITHUB_TOKEN with permissions: issues: write" >&2
                return 1  # Hard fail — caller should exit
            else
                echo "Warning: Preflight label check failed (exit $exit_code): $stderr_content" >&2
                echo "  Proceeding with label operations (may be a transient error)." >&2
                return 0  # Soft fail — proceed
            fi
        fi
        return 0
    }
    ```

3. **Call preflight before label operations**:

    ```bash
    if ! _preflight_label_token; then
        echo "Error: Aborting label operations due to preflight failure." >&2
        # Still output PR results — PR was already created successfully
        echo "pr_url=$PR_URL" >> "${GITHUB_OUTPUT:-/dev/stdout}"
        echo "pr_number=$PR_NUMBER" >> "${GITHUB_OUTPUT:-/dev/stdout}"
        exit 1
    fi
    ```

### Phase 3: Label Operation Helper Functions (FR-003, FR-004, FR-005, FR-006)

**Deliverable**: Retry-capable label operation wrappers with structured error logging.

**New functions in `create-spec-pr.sh`**:

1. **`_is_transient_label_error`** — Classify HTTP errors as transient (429, 500, 502, 503, 504) vs. non-transient (401, 403, 404, 422):

    ```bash
    _is_transient_label_error() {
        local stderr_output="$1"
        echo "$stderr_output" | grep -qE '(429|500|502|503|504)'
    }
    ```

2. **`_log_label_error`** — Structured error logging per NFR-002:

    ```bash
    _log_label_error() {
        local operation="$1" label="$2" stderr_output="$3"
        local remediation=""
        if echo "$stderr_output" | grep -q "403"; then
            remediation="Ensure LABEL_TOKEN uses GITHUB_TOKEN with permissions: issues: write"
        elif echo "$stderr_output" | grep -q "404"; then
            remediation="Verify the repository and PR number are correct"
        elif echo "$stderr_output" | grep -q "422"; then
            remediation="Check that the label name is valid and not a duplicate"
        fi
        echo "Error: $operation failed for label '$label'" >&2
        echo "  Output: $stderr_output" >&2
        [[ -n "$remediation" ]] && echo "  Remediation: $remediation" >&2
    }
    ```

3. **`_create_label_with_retry`** — Wraps `gh label create --force` with retry for transient errors:

    ```bash
    _create_label_with_retry() {
        local label="$1"
        # ... uses EFFECTIVE_LABEL_TOKEN, calls gh label create
        # ... retries on transient errors via _RETRY_ABORT_CODE pattern
    }
    ```

4. **`_apply_label_with_retry`** — Wraps single `gh pr edit --add-label` with retry:

    ```bash
    _apply_label_with_retry() {
        local pr_url="$1" label_csv="$2"
        # ... uses EFFECTIVE_LABEL_TOKEN
    }
    ```

### Phase 4: Label Deduplication & Batch Application (FR-007, FR-008)

**Deliverable**: Replace the current per-label loop (lines 572–605) with deduplicated batch logic.

**Changes**:

1. **Collect all labels** (source issue labels + phase/speckit label) into a single deduplicated list
2. **Ensure all labels exist** via per-label `gh label create --force` with retry
3. **Batch apply** via single `gh pr edit --add-label "label1,label2,label3"` with retry
4. **Fallback** on batch failure: apply each label individually via `gh pr edit --add-label`

Replace lines 572–605 with the new `_apply_all_labels` function.

### Phase 5: Remove Error Suppression (FR-003)

**Deliverable**: All `2>/dev/null` redirections on label operations are removed.

**Specific removals** (6 locations in current code):

| Line | Current code | Fix |
| --- | --- | --- |
| 583 | `gh label create "$label" --force 2>/dev/null \|\| true` | Remove `2>/dev/null`, use retry wrapper |
| 584 | `gh pr edit "$PR_URL" --add-label "$label" 2>/dev/null` | Remove `2>/dev/null`, use retry wrapper |
| 595 | `gh label create "$PHASE_LABEL" --force ... 2>/dev/null \|\| true` | Remove, handled by batch logic |
| 596-602 | `gh pr edit "$PR_URL" --add-label "$PHASE_LABEL" 2>/dev/null` | Remove, handled by batch logic |
| 601 | `gh label create "speckit:spec" --force ... 2>/dev/null \|\| true` | Remove, handled by batch logic |
| 602 | `gh pr edit "$PR_URL" --add-label "speckit:spec" 2>/dev/null` | Remove, handled by batch logic |

### Phase 6: Testing

**Deliverable**: Shell-based tests verifying the new label logic.

1. **Unit tests** (new file: `.github/scripts/speckit-trigger/tests/test_label_operations.sh`):
   - Token resolution: `LABEL_TOKEN` set → used; unset → falls back to `GH_TOKEN` with warning
   - Preflight: auth error → exit; transient error → proceed
   - Error classification: transient vs. non-transient
   - Label deduplication
   - Batch comma-separated construction
   - Structured error message format

2. **Integration validation**: Run both workflows on a test issue and verify labels appear on the PR.

### Phase 7: Documentation

**Deliverable**: Update script header comments and workflow comments.

1. Update `create-spec-pr.sh` header comment (line 27) to document `LABEL_TOKEN`
2. Add inline comments in workflow YAML explaining `LABEL_TOKEN` vs. `GH_TOKEN`

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| `GITHUB_TOKEN` lacks `issues: write` despite job-level `permissions` | Low | High | Both workflows already declare `permissions: issues: write`; `GITHUB_TOKEN` inherits this |
| Retry loops exceed 60s NFR-001 timeout | Low | Medium | Per-label worst case: (N creates + 1 batch apply + N fallback applies) × 3 attempts × ~4s backoff. For typical PR (≤5 labels): ~5s without retries, ~60s worst case with all retries. **Short-circuit strategy**: track elapsed wall-clock time from the first label operation; if cumulative time exceeds 45s, skip remaining retries and log a warning. This guarantees the 60s NFR-001 cap regardless of label count. |
| `gh label create --force` fails silently for valid labels | Low | Medium | `--force` is idempotent; test with existing labels to confirm |
| Batch `gh pr edit --add-label` fails due to one bad label | Medium | Low | Fallback to individual application identifies the bad label |
| Breaking existing PR creation flow | Low | Critical | Label changes are isolated after `_do_create_pr`; PR creation uses `GH_TOKEN` unchanged |

## 6. Dependencies

**External**:

- `gh` CLI (already available on GitHub Actions runners)
- `jq` (already available on `ubuntu-latest` runners)
- GitHub REST API (label and PR endpoints)

**Internal**:

- `lib/retry.sh` — reused for label operation retries (no changes needed)
- `create-spec-pr.sh` — primary target of changes
- Both workflow YAML files — `env:` block changes only

---
*Generated by Copilot SDK (claude-opus-4.6)*
