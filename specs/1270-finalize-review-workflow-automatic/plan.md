# Implementation Plan: Finalize Review Workflow — Automatic PR Comment Repair/Finalization

## Technical Context

- **Language/Runtime**: Python 3.10+, pip-installable CLI package (`agentic-devtools`)
- **Key Dependencies**: `requests` (Azure DevOps REST API), `json`, `concurrent.futures`
- **Architecture**: CLI entry points → sync functions → Azure DevOps PATCH API calls
- **State**: JSON file at `.agdt/workflows/{identity}/{worktree_key}/state.json`
- **Review State**: `reviews/review-state.json` — hierarchical PR thread/status data
- **Markers**: HTML comment markers (`<!-- agdt-review:v1 type:... -->`) for comment classification
- **Existing Completion Step**: `advance_pull_request_review_workflow(step="completion")` in `agentic_devtools/cli/workflows/commands.py:1011–1068`

## Research Summary

See [research.md](research.md) for detailed decisions on:

- Synchronous vs. background execution model for finalization
- Batch-first reuse of `submit_reviews()` internals vs. direct PATCH approach
- Identity resolution caching strategy
- Convergence comparison normalization approach

## Design Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│  advance_pull_request_review_workflow(step="completion")              │
│  (existing code in agentic_devtools/cli/workflows/commands.py)       │
├──────────────────────────────────────────────────────────────────────┤
│  1. Existing: load review state, cascade overall summary             │
│  2. NEW: run_finalization_pass(...)                                  │
│  3. Existing: (re-)derive decision, advance workflow step            │
└──────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  run_finalization_pass()  [NEW orchestrator]                          │
├──────────────────────────────────────────────────────────────────────┤
│  Phase 0: Resolve PAT identity (Connection Data API)                 │
│  Phase 1: Fetch current threads from ADO API                         │
│  Phase 2: Classify eligible comments (markers + authorship)          │
│  Phase 3: Compute expected terminal content per comment              │
│  Phase 4: Compare observed vs expected (convergence check)           │
│  Phase 5: Batch-first repair (batch via submit_reviews + cascade)     │
│  Phase 6: Verify convergence (re-fetch from API)                     │
│  Phase 7: Targeted fallback for non-converged comments               │
│  Phase 8: Final verification + retry rounds (max 2)                  │
│  Phase 9: Emit report (stdout + JSON file)                           │
└──────────────────────────────────────────────────────────────────────┘
```

**New Package**: `agentic_devtools/cli/azure_devops/finalization/`

This package contains the following modules:

- `__init__.py` — exports `run_finalization_pass`, `FinalizationReport`
- `models.py` — data classes (`EligibleComment`, `EligibleComments`, `ConvergenceResult`, `BatchRepairResult`, `TargetedRepairResult`, `FinalizationReport`)
- `identity.py` — `resolve_pat_identity()` — wraps the Connection Data API call
- `classification.py` — `classify_eligible_comments()` — marker-based + authorship filtering
- `convergence.py` — `compute_expected_content()`, `normalize_for_comparison()`, `check_convergence()` — convergence computation and comparison
- `repair.py` — `batch_repair_pass()`, `targeted_repair()` — batch-first and targeted fallback repair
- `verification.py` — `verify_convergence()` — re-reads from API and confirms state
- `reporting.py` — `build_finalization_report()` — structures the output report
- `orchestrator.py` — `run_finalization_pass()` — the top-level orchestrator that sequences phases 0–9

## Implementation Phases

### Phase 1: Identity Resolution and Comment Classification (FR-004 through FR-009)

**Deliverables:**

1. `resolve_pat_identity(organization, headers) -> str | None` — calls `/_apis/connectionData`, returns `authenticatedUser.id` GUID
2. `classify_eligible_comments(threads, pat_user_id, review_state) -> EligibleComments` — uses `classify_agdt_threads()` + `parse_marker()` to identify eligible file-summary, overall-summary, and
   activity-log-entry comments, filtered by `author.id == pat_user_id`
3. Data class `EligibleComment` (thread_id, comment_id, marker_type, marker_data, current_content, file_path)
4. Data class `EligibleComments` (file_summaries, overall_summary, activity_log_entries, skipped)

**Key Implementation Details:**

- Reuse existing `_get_current_user_id()` from `agentic_devtools/cli/azure_devops/pull_request_details_commands.py` or factor it into a shared helper
- **Activity-log entry scanning**: `classify_agdt_threads()` only inspects the *first* comment's
  marker/content to classify a thread. Activity-log entries are posted as *replies* (non-first
  comments) within the activity-log thread, so they will not be found by `classify_agdt_threads()`
  alone. `classify_eligible_comments()` must therefore scan *all* comments within threads
  identified as activity-log threads (or add a dedicated helper, e.g.,
  `_scan_thread_replies_for_markers(thread, pat_user_id)`) to collect individual
  activity-log-entry comments by their reply-level markers.
- Activity-log entries scoped by session ID matching from `review-state.json`
- Comments with `author.id != pat_user_id` → skipped with reason in report

**Tests (TDD):**

- `tests/unit/cli/azure_devops/finalization/identity/test_resolve_pat_identity.py`
- `tests/unit/cli/azure_devops/finalization/classification/test_classify_eligible_comments.py`

---

### Phase 2: Convergence Computation and Comparison (FR-012, FR-013, FR-014, FR-022, FR-023)

**Deliverables:**

1. `compute_expected_content(comment: EligibleComment, review_state) -> str` — dispatches to
   `render_file_summary()`, `render_overall_summary()`, or `_format_activity_log_entry()` based on marker type;
   returns **body-only content without the leading marker line** so that it can be compared directly against
   normalized observed content
2. `normalize_for_comparison(content: str) -> str` — strips the leading `<!-- agdt-review:v1 ... -->`
   marker line (if present) from any content string; applied to observed content before comparison so both
   sides are marker-free
3. `check_convergence(comment: EligibleComment, expected: str) -> bool` — compares
   `normalize_for_comparison(observed)` against `expected` (which is already marker-free from
   `compute_expected_content()`)
4. `ConvergenceResult` data class (comment, converged: bool, expected_content, observed_content)

**Key Implementation Details:**

- Marker line stripping: add a public helper `strip_marker_line(content: str) -> str` in `marker.py` that uses
  `parse_marker()` internally to detect and remove the leading marker line, keeping the regex as a private
  implementation detail of the marker module
- For file-summary: call `render_file_summary(file_entry, suggestions, base_url, **attribution_params)`
- For overall-summary: call `render_overall_summary(state, base_url, **attribution_params)`
- For activity-log-entry: call `_format_activity_log_entry(status_emoji="✅", status_text="Completed", ...)`
  and return the body portion only (exclude the marker line that `_format_activity_log_entry()` may prepend)
- FR-022: Model Review Progress table rows with intermediate states (`⏳`, `🔃`) must be resolved
- FR-022: Stale file links pruned from overall summary (compare against current `review_state.files` keys)

**Tests (TDD):**

- `tests/unit/cli/azure_devops/finalization/convergence/test_compute_expected_content.py`
- `tests/unit/cli/azure_devops/finalization/convergence/test_normalize_for_comparison.py`
- `tests/unit/cli/azure_devops/finalization/convergence/test_check_convergence.py`

---

### Phase 3: Batch-First Repair Pass (FR-003, FR-010, FR-021, FR-011)

**Deliverables:**

1. `batch_repair_pass(eligible: EligibleComments, review_state, config, headers, pr_id, dry_run) -> BatchRepairResult`
2. Drives convergence via `submit_reviews()` (or its underlying parallel file-processing and
   single-cascade logic) as required by FR-003/FR-010, reserving direct PATCH for targeted
   fallback only (FR-011)
3. Does NOT alter file verdicts — preserves existing `approved`/`needs-work` outcomes (FR-021)
4. Drives file-summary comments to their terminal rendered content
5. Single cascade at end (FR-010)

**Key Implementation Details:**

- Build `valid_items` list from review state file entries (not from `batch_reviews.items` state key)
- **Batch-first via `submit_reviews()` internals**: Reuse the existing `submit_reviews()`
  function (or its internal parallel file-processing path) as the entry point for driving
  file-summary convergence (FR-003). The implementation **MAY** add a `repair_mode=True`
  flag to `_process_file_parallel()` that short-circuits suggestion rotation
  (`clear_suggestions_for_re_review()`) and suggestion POST paths while still rendering
  and posting file-summary content via the existing batch mechanism. This preserves the
  single-cascade invariant (at most one `execute_cascade()` at the end of the batch,
  skipped when no file operations succeeded) consistent with FR-010.
- Direct PATCH is reserved for targeted fallback (Phase 4/FR-011) only — the batch-first
  pass must not bypass `submit_reviews()` internals
- For activity-log entries: call `_complete_active_session()` which internally calls `_update_activity_log_comment_status()`
- Catch `SystemExit` from internal calls and translate to non-blocking failure (CLAR-003)

**Tests (TDD):**

- `tests/unit/cli/azure_devops/finalization/repair/test_batch_repair_pass.py`

---

### Phase 4: Verification and Targeted Fallback (FR-015 through FR-017)

**Deliverables:**

1. `verify_convergence(eligible: EligibleComments, expected_map, config, headers, pr_id) -> list[ConvergenceResult]`
2. `targeted_repair(non_converged: list[EligibleComment], expected_map, config, headers, pr_id, review_state, dry_run) -> TargetedRepairResult`
3. Retry logic: up to 2 additional rounds, 5-second delay between rounds (NFR-001)

**Key Implementation Details:**

- Verification re-fetches individual comments via `config.build_api_url(repo_id, "pullRequests", pr_id, "threads", thread_id, "comments", comment_id)` (GET)
- Targeted repair uses the same URL construction with a PATCH request, setting content = `build_marker(...)` + rendered body
- Activity-log entries use `_update_activity_log_comment_status()` directly for targeted repair (FR-011)
- Each retry round only targets comments still non-converged
- Total retry overhead capped at 10 seconds (2 rounds × 5s backoff)

**Tests (TDD):**

- `tests/unit/cli/azure_devops/finalization/verification/test_verify_convergence.py`
- `tests/unit/cli/azure_devops/finalization/repair/test_targeted_repair.py`

---

### Phase 5: Orchestrator and Reporting (FR-001, FR-002, FR-018, FR-019, NFR-001–006)

**Deliverables:**

1. `run_finalization_pass(review_state, pr_id, config, headers, dry_run) -> FinalizationReport`
2. `FinalizationReport` data class (status, repaired, skipped, unchanged, failed, details, duration_ms)
3. Report persisted to `finalization-report-{commit_hash_short}.json`
4. Human-readable summary printed to stdout
5. Dry-run mode: full classification + convergence check, no mutations, report shows what would change

**Key Implementation Details:**

- Called from `advance_pull_request_review_workflow(step="completion")` after existing cascade logic
- Wrapped in try/except: any exception → non-blocking failure report (NFR-002)
- Missing/corrupt `review-state.json` → no-op success (FR-019)
- Idempotent: re-running on converged state → no-op, reports "already finalized" (NFR-004)
- 60-second timeout enforced via wall-clock check (NFR-001)

**Tests (TDD):**

- `tests/unit/cli/azure_devops/finalization/orchestrator/test_run_finalization_pass.py`
- `tests/unit/cli/azure_devops/finalization/reporting/test_build_finalization_report.py`

---

### Phase 6: Integration into Completion Step

**Deliverables:**

1. Modify `advance_pull_request_review_workflow()` in `agentic_devtools/cli/workflows/commands.py` (lines 1011–1068) to call `run_finalization_pass()` after the existing cascade
2. Wire up dry-run detection via `is_dry_run()`
3. Ensure the finalization report is available as a template variable for the completion prompt

**Key Implementation Details:**

- **Insertion point and critical ordering**: In the current `advance_pull_request_review_workflow`
  implementation, `decision` is derived from `review_state.overallSummary.status` *before* the
  `execute_cascade()` call and before `save_review_state()`. Because `run_finalization_pass()`
  may update overall/file statuses in `review_state`, the call must be placed **after
  `execute_cascade()` and before `save_review_state()`**, so that post-finalization state is
  persisted in a single save. `decision` **must be explicitly re-derived after finalization
  returns**. Concretely, the implementation must:
  1. Call `execute_cascade()` (existing),
  2. Call `run_finalization_pass()` (new — placed after cascade, before save),
  3. Call `save_review_state(review_state)` (existing — now persists post-finalization state),
  4. Re-derive `decision` from `review_state.overallSummary.status` after the finalization
     call returns, ensuring the workflow step receives the post-finalization status.
  Without the re-derivation, `decision` would remain stale (reflecting pre-finalization state).
- Non-blocking: wrap in try/except, log warning on failure — if finalization raises, fall through to the existing `decision` derivation unchanged
- Pass the already-loaded `review_state`, `config`, `headers` to avoid re-fetching

**Tests (TDD):**

- `tests/unit/cli/workflows/commands/test_advance_pull_request_review_workflow.py` (extend existing)

---

### Phase 7: Documentation and Final Validation

**Deliverables:**

1. Update `.github/copilot-instructions.md` with finalization behavior documentation
2. Update `CHANGELOG.md`
3. Run full PR checks (`bash scripts/run-pr-checks.sh`)
4. Verify idempotency by running completion step twice on the same state

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `submit_reviews()` internals call `sys.exit(1)` | High | Medium | Catch `SystemExit` and translate to non-blocking failure |
| API rate limiting during comment patching | Low | Medium | Respect `Retry-After` headers; bounded retry model caps at 10s |
| Identity resolution fails (network/PAT issue) | Low | High | Hard stop: no mutations if identity unknown (FR-009) |
| Large PR with 50+ files exceeds 60s budget | Low | Medium | Batch-first approach minimizes API calls; timeout enforcement |
| Marker format changes break classification | Very Low | High | Use existing `parse_marker()` public API, not raw regex |
| Existing completion tests break | Medium | Medium | Finalization is additive and wrapped in try/except |

## Dependencies

### Internal Dependencies

- `agentic_devtools.cli.azure_devops.marker` — `parse_marker()`, `has_agdt_marker()`, `classify_agdt_threads()`, `build_marker()`, `strip_marker_line()`
- `agentic_devtools.cli.azure_devops.review_templates` — `render_file_summary()`, `render_overall_summary()`
- `agentic_devtools.cli.azure_devops.review_scaffold` — `_update_activity_log_comment_status()`, `_format_activity_log_entry()`
- `agentic_devtools.cli.azure_devops.review_state` — `load_review_state()`, `save_review_state()`, `ReviewState`
- `agentic_devtools.cli.azure_devops.status_cascade` — `cascade_overall_summary_update()`, `execute_cascade()`
- `agentic_devtools.cli.azure_devops.file_review_commands` — `_process_file_parallel()`, `_complete_active_session()`
- `agentic_devtools.cli.azure_devops.auth` — `get_pat()`, `get_auth_headers()`
- `agentic_devtools.cli.azure_devops.config` — `AzureDevOpsConfig`
- `agentic_devtools.state` — `is_dry_run()`, `get_value()`

### External Dependencies

- Azure DevOps REST API (`/_apis/connectionData`, thread/comment PATCH via `config.build_api_url()`)
- No new pip dependencies required

---
*Generated by Copilot SDK (claude-opus-4.6)*
