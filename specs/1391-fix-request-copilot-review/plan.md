# Implementation Plan: Fix request-copilot-review verification instability

**Issue**: #1391
**Source file**: `agentic_devtools/cli/github/request_copilot_review.py`

## Technical Context

- **Language**: Python 3.10+, `from __future__ import annotations`
- **CLI framework**: argparse entry points defined in `pyproject.toml`
- **External dependency**: `gh` CLI for GitHub API calls via `run_safe()`
- **Test framework**: pytest with `unittest.mock`, 1:1:1 test structure under `tests/unit/`
- **Env var pattern**: `AGDT_DEBUG` is a new env var introducing truthy parsing ("1",
  "true", "yes" — case-insensitive) via a dedicated `_is_debug()` helper. This is a
  distinct parsing rule from other `AGDT_*` env vars: `AGDT_NO_VERIFY_SSL` treats any
  non-empty value as enabled, and `AGDT_USE_EMOJI` only recognizes literal
  "true"/"false". The `dry_run` flag is handled via state, not an env var.
- **No logging module in this file**: `request_copilot_review.py` uses
  `print(..., file=sys.stderr)` for all diagnostics (other modules in the codebase
  may use Python's `logging` module)

## Key Design Decisions

- `VerificationResult` as a dataclass vs NamedTuple → **dataclass** (mutable fields, clearer
  semantics)
- Backoff implementation approach → **inline loop, no library** (avoids external dependency
  for 4-iteration loop)
- `AGDT_DEBUG` check utility placement → **module-level helper** (`_is_debug()`) for reuse

## Design Overview

The change is scoped to a single file (`request_copilot_review.py`) and its tests.
The public API (`request_copilot_review()`, `request_copilot_review_command()`,
`COPILOT_REVIEWER_LOGIN`) remains unchanged. The public surface expands additively:
`VerificationResult` is added to `agentic_devtools/cli/github/__init__.py` re-exports
and `__all__`. Existing consumers are unaffected.

```text
request_copilot_review.py
├── VerificationResult (NEW dataclass)
├── _is_debug() (NEW helper)
├── _verify_reviewer_requested()  ← REFACTORED (returns VerificationResult)
├── _post_review_request()        ← UNCHANGED
├── request_copilot_review()      ← UPDATED (destructures VerificationResult)
└── request_copilot_review_command() ← UNCHANGED
```

## Implementation Phases

### Phase 1: Introduce `VerificationResult` dataclass (FR-008)

**Deliverables:**

1. Add `VerificationResult` dataclass at module level with fields:
   - `verified: bool`
   - `retries: int`
   - `elapsed_seconds: float` (rounded to 1 decimal place per spec)
   - `degraded: bool`
   - `diagnostics: dict | None`
2. Add `_is_debug() -> bool` helper that checks `AGDT_DEBUG` env var.
   Truthy values: `"1"`, `"true"`, `"yes"` (case-insensitive), matching
   `os.environ.get("AGDT_DEBUG", "").lower() in ("1", "true", "yes")`.
3. Add new test file: `tests/unit/cli/github/request_copilot_review/test_verificationresult.py`
4. Add new test file: `tests/unit/cli/github/request_copilot_review/test__is_debug.py`

### Phase 2: Refactor `_verify_reviewer_requested()` (FR-001–FR-004, FR-009, FR-010)

**Deliverables:**

1. Change signature to return `VerificationResult` instead of `bool`.
2. Move the retry loop INTO `_verify_reviewer_requested()` (currently in `request_copilot_review()`).
3. Implement deterministic exponential backoff: delays = [2, 4, 8, 16] seconds
   (max retries = 4, giving 5 total attempts; cumulative backoff budget = 30s,
   bounding wall-time to ~55s including request timeouts).
4. Add `timeout=5` to each `run_safe()` call (NFR-005).
5. Track `well_formed_response_seen` (any attempt with valid JSON containing `users` key).
6. Track `last_users_found` and `last_teams_found` from each attempt.
7. On each attempt, if `_is_debug()`, print structured response diagnostics to
   stderr including: top-level JSON keys (sorted alphabetically), `users` array
   length, and `teams` array length
   (e.g., `"Debug: keys=['teams','users'], users=3, teams=1"`).
   Keys **must** be sorted before printing to ensure deterministic output
   regardless of GitHub's JSON serialization order — this prevents brittle tests
   and makes log comparison reliable.
   This satisfies the spec requirement for both key enumeration and array counts.
8. On unexpected HTTP status (non-200), include the HTTP status code and a
   response body excerpt (first 200 chars) in the stderr warning (AC-3.3).
   **Implementation note**: Use `gh api -i` to include response headers in
   stdout. The first line contains the HTTP status (e.g., `HTTP/2.0 404 Not
   Found`). Parse the status code from that line, then split on the first blank
   line to separate headers from the JSON body. This pattern is already used in
   this repo (see `.github/workflows/scripts/check-release-exists.sh:17`).
   On non-zero `returncode` where status line parsing fails, fall back to
   reporting the exit code.
   The diagnostic message format:
   `"Warning: gh api returned HTTP {status_code}: {body[:200]}"`
   (or `"Warning: gh api failed (exit={returncode}): {stderr[:200]}"` as
   fallback when the status line cannot be parsed).
9. On success (bot found), return immediately with `verified=True, degraded=False`.
10. After exhausting retries:
    - Set `degraded=True` if no well-formed response was ever seen.
    - Build `diagnostics` dict with `lastUsersFound`, `lastTeamsFound`,
      `wellFormedResponseSeen`, and `message`.
    - Emit final stderr diagnostic containing: login values found in `users`,
      team slugs found in `teams`, total elapsed time (rounded to 1 dp), and
      retry count (FR-005).
11. Update existing tests in `test__verify_reviewer_requested.py` — they will need
    to assert on `VerificationResult` fields instead of bare `bool`.
12. Add new test scenarios for:
    - Exponential backoff delay values (AC-2.1)
    - Early return on success (AC-2.3)
    - Degraded mode when all responses malformed (AC-5.1)
    - Mixed responses — some malformed, some well-formed (edge case 8)
    - `AGDT_DEBUG` output (AC-3.2)
    - Timeout handling (edge case 6)
    - Diagnostic content on failure (AC-3.1, AC-3.3)

### Phase 3: Update `request_copilot_review()` caller (FR-006, FR-007)

**Deliverables:**

1. Replace the inline retry loop with a single call to `_verify_reviewer_requested()`.
2. Destructure `VerificationResult` to build the JSON result dict.
3. Add `elapsedSeconds` (float, rounded to 1 decimal place; always present
   when verification ran).
4. Add `diagnostics` (present only when `verified` is `false`).
5. Add `degraded` to result dict.
6. Preserve all existing keys: `prNumber`, `repo`, `requested`, `reviewer`,
   `verified`, `retries`.
7. Update existing tests in `test_request_copilot_review.py`:
   - Mock `_verify_reviewer_requested` to return `VerificationResult` instead of `bool`.
   - Assert new fields (`elapsedSeconds`, `diagnostics`, `degraded`).
   - Verify `diagnostics` is absent when `verified=True` (AC-4.1).
8. Add test for backward compatibility: existing keys still present (AC-4.3).

### Phase 4: Update `__init__.py` exports and run validation

**Deliverables:**

1. Add `VerificationResult` to `__init__.py` imports and `__all__`.
2. Run `python scripts/validate_test_structure.py` to confirm test structure.
3. Run `bash scripts/run-pr-checks.sh` to confirm all checks pass.
4. Run `ruff check --fix . && ruff format .` for lint compliance.

## Test Plan (1:1:1 structure)

All tests go under `tests/unit/cli/github/request_copilot_review/`:

| Test file | Symbol under test | New/Modified |
|---|---|---|
| `test_verificationresult.py` | `VerificationResult` | NEW |
| `test__is_debug.py` | `_is_debug` | NEW |
| `test__verify_reviewer_requested.py` | `_verify_reviewer_requested` | MODIFIED |
| `test_request_copilot_review.py` | `request_copilot_review` | MODIFIED |
| `test_request_copilot_review_command.py` | `request_copilot_review_command` | UNCHANGED |
| `test__post_review_request.py` | `_post_review_request` | UNCHANGED |

### Key test scenarios to add

| ID | Scenario | File |
|---|---|---|
| T1 | Bot found on 1st attempt → `verified=True, retries=0` | `test__verify_reviewer_requested.py` |
| T2 | Bot found on 3rd attempt → `verified=True, retries=2` | `test__verify_reviewer_requested.py` |
| T3 | All 5 attempts fail, well-formed → `verified=False, degraded=False` | `test__verify_reviewer_requested.py` |
| T4 | All 5 attempts malformed → `verified=False, degraded=True` | `test__verify_reviewer_requested.py` |
| T5 | Mixed malformed + well-formed → `degraded=False` | `test__verify_reviewer_requested.py` |
| T6 | Backoff delays = [2, 4, 8, 16] | `test__verify_reviewer_requested.py` |
| T7 | `timeout=5` passed to `run_safe` | `test__verify_reviewer_requested.py` |
| T8 | `AGDT_DEBUG=1` prints response shape | `test__verify_reviewer_requested.py` |
| T9 | Diagnostics contain `lastUsersFound`, etc. | `test__verify_reviewer_requested.py` |
| T10 | `elapsed_seconds` is a float | `test__verify_reviewer_requested.py` |
| T11 | Result JSON has `elapsedSeconds` when verified | `test_request_copilot_review.py` |
| T12 | Result JSON omits `diagnostics` when verified | `test_request_copilot_review.py` |
| T13 | Result JSON has `diagnostics` when not verified | `test_request_copilot_review.py` |
| T14 | All existing JSON keys preserved | `test_request_copilot_review.py` |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Existing tests break due to `_verify_reviewer_requested` signature change | High | Medium | Update mocks in Phase 3 to return `VerificationResult` |
| `time.sleep` mocking in tests becomes more complex with exponential backoff | Medium | Low | Use `side_effect` list to verify exact delay sequence |
| `timeout` parameter not supported by `run_safe` | Low | High | Verify `run_safe` passes kwargs to `subprocess.run` (it does) |
| New dataclass import changes `__init__.py` export surface | Low | Low | Only additive; existing imports unaffected |

## Dependencies

- **Internal**: `run_safe` from `subprocess_utils` (must support `timeout` kwarg)
- **Internal**: `set_value` / `get_value` from `state.py` (unchanged usage)
- **External**: `gh` CLI (unchanged usage)
- **Related issue**: #1120 (consolidate `COPILOT_REVIEWER_LOGIN` — out of scope)

---
*Generated by Copilot SDK (claude-opus-4.6)*
