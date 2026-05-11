# Spec: Fix request-copilot-review verification instability

## Status

Proposed

**Source Issue**: #1391

## Summary

The `agdt-gh-request-copilot-review` command successfully POSTs a review request
for `copilot-pull-request-reviewer[bot]`, but verification consistently reports
`"verified": false`. This forces AI agents and automation to add custom
workarounds, creating instability in the `agdt.address-copilot-review` pipeline.

## Problem Statement

The current verification logic in `_verify_reviewer_requested()` calls the
GitHub REST API endpoint
`GET /repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers` and iterates
only over the `users` array:

```python
for user in data.get("users", []):
    if user.get("login", "").lower() == COPILOT_REVIEWER_LOGIN.lower():
        return True
return False
```

The API response has two top-level arrays — `users` and `teams`:

```json
{
  "users": [
    {"login": "octocat", "id": 1, "type": "User"}
  ],
  "teams": [
    {"slug": "justice-league", "id": 2}
  ]
}
```

Bot accounts such as `copilot-pull-request-reviewer[bot]` have `"type": "Bot"`
and may appear in the `users` array with a delay after the POST succeeds. The
verification function does not account for propagation delay adequately — it
retries only **2 times** with a fixed **5-second** delay, giving a maximum
verification window of 10 seconds. If the bot has not yet appeared in the
`users` array within that window, verification fails permanently.

Additionally, the `teams` array is never inspected. Checking `teams` for the
bot is out of scope (see Non-Goals) since `teams` entries use `slug` rather
than `login` and the Copilot bot is a user-type account, not a team.

### Existing Diagnostics (what is already present)

The implementation already provides _some_ diagnostic output:

- A `Warning:` message to stderr when the verification API call itself fails
  (non-zero exit code).
- A `Warning:` message to stderr when the API response cannot be parsed as JSON.
- A `Verification retry {n}/2...` message to stderr on each retry attempt.

### Diagnostics Gaps (what is missing)

- **No response-shape details**: When verification fails (bot not found in
  `users`), there is no output showing what the API actually returned — the
  caller only sees `"verified": false` with no explanation of why.
- **No final failure context**: After exhausting retries, no summary message
  explains the total elapsed time, the number of users/teams found, or the
  exact login values that were checked.
- **No timing/backoff information**: The retry messages do not include
  timestamps or delay durations, making it difficult to diagnose whether the
  issue is a timing race or a structural mismatch.

## Goals

- Make verification succeed reliably when the Copilot bot review request is
  actually registered.
- Provide sufficient retry budget to handle normal API propagation delays.
- Surface actionable diagnostics when verification fails so operators can
  distinguish timing issues from structural mismatches.
- Preserve backward compatibility with existing JSON output keys and state keys.

## Non-Goals

- Changing the POST request logic (it already works correctly).
- Adding support for requesting reviews from arbitrary bots or teams.
- Modifying the `agdt.address-copilot-review` prompt workflow itself.
- Adding integration tests against live GitHub APIs (unit tests with mocked
  responses are sufficient).

## Clarifications

- [NEEDS CLARIFICATION] Should the bot login
  (`copilot-pull-request-reviewer[bot]`) be configurable (e.g., via state key or
  environment variable) or remain a code constant? Current code uses
  `COPILOT_REVIEWER_LOGIN` as a module-level constant.

## User Scenarios & Testing

### US-1 (P1): Verify the bot in the users array

As an AI agent running `agdt-gh-request-copilot-review`, I want verification to
check the `users` array in the API response so that the bot is found when GitHub
places it there.

**Acceptance Criteria / Scenarios**

- **AC-1.1**: Given the API response contains the bot in `users` with
  `"type": "Bot"`, when verification runs, then it returns `verified: true`.
- **AC-1.2**: Given the API response does not contain the bot in `users`,
  when verification runs, then it returns `verified: false` after exhausting
  retries. The outcome distinction with AC-5.1 is as follows:
  - **Well-formed response, bot not found** (AC-1.2): at least one response
    contained a valid JSON object with a `users` array, but the bot login was
    never present → `verified: false`, `degraded: false`.
  - **Malformed/empty responses on ALL attempts** (AC-5.1): every response was
    either non-JSON, an HTTP error, or missing the `users` key entirely →
    `verified: false`, `degraded: true`.
  - Precedence: if any single attempt returns a well-formed response (even with
    an empty `users` array), the result is classified under AC-1.2 (not
    degraded), because the API structure is confirmed as functional.

### US-2 (P1): Retry with exponential backoff and sufficient time budget

As an AI agent, I want verification to use exponential backoff with a sufficient
total time budget so that normal GitHub API propagation delays do not cause false
negatives.

**Acceptance Criteria / Scenarios**

- **AC-2.1**: Given verification fails on the first attempt, when retries are
  configured, then the system retries with exponential backoff delays (e.g.,
  2s, 4s, 8s, 16s).
- **AC-2.2**: Given a maximum retry count, when all retries are exhausted, then
  the total sum of backoff delays provides at least 30 seconds of retry budget
  (e.g., 2s + 4s + 8s + 16s = 30s). Total wall time (including API call
  durations) may exceed this and is bounded by SC-002.
- **AC-2.3**: Given verification succeeds on any retry attempt, then the system
  returns `verified: true` immediately without waiting for remaining retries.

### US-3 (P2): Surface actionable diagnostics on verification failure

As a developer debugging a failed verification, I want the system to output
what the API actually returned and why verification failed so that I can
distinguish a timing issue from a structural mismatch.

**Acceptance Criteria / Scenarios**

- **AC-3.1**: Given verification fails after exhausting retries, when the final
  result is produced, then stderr includes: the login values found in `users`,
  the team slugs found in `teams`, the total elapsed time, and the number of
  retries attempted.
- **AC-3.2**: Given verbose/debug logging is enabled, when each verification
  attempt runs, then the raw API response shape (field names and counts) is
  logged.
- **AC-3.3**: Given a verification API call returns an unexpected HTTP status,
  then the status code and response body excerpt are included in the warning.

### US-4 (P2): Preserve backward compatibility with JSON output and state keys

As a consumer of `agdt-gh-request-copilot-review` output, I want the JSON
result schema and state keys to remain unchanged so that existing automation
and prompts continue to work.

**Acceptance Criteria / Scenarios**

- **AC-4.1**: Given a successful verification, when the JSON result is produced,
  then it contains at minimum: `prNumber`, `repo`, `requested`, `reviewer`,
  `verified`, and `retries`. The `retries` field is defined as the number of
  additional verification attempts after the initial one (i.e., 0 means success
  on first attempt; 4 means 4 retries were needed after the initial try, for
  5 total attempts).
- **AC-4.2**: Given verification completes, when state is updated, then
  `github.copilot_review_requested` and
  `github.copilot_review_request_verified` are set as before.
- **AC-4.3**: Given new diagnostic fields are added to the JSON output, then
  they are additive (no existing fields are removed or renamed).

### US-5 (P3): Degrade gracefully when verification is structurally impossible

As an AI agent running in a GitHub Enterprise (GHE) environment or a
non-standard GitHub configuration, I want the system to detect when verification
cannot structurally succeed and degrade gracefully rather than wasting time on
retries.

**Acceptance Criteria / Scenarios**

- **AC-5.1**: Given the verification API consistently returns an empty or
  malformed response across all retries, when the final result is produced,
  then it includes a `"degraded": true` flag and a human-readable message
  explaining the structural limitation.
- **AC-5.2**: Given graceful degradation is triggered, then the overall command
  still exits with code 0 (the POST succeeded; only verification is uncertain).
- **AC-5.3**: Given degradation, then `github.copilot_review_requested` is
  `true` and `github.copilot_review_request_verified` is `false`, matching
  current behavior for unverified requests.

## Success Criteria

- **SC-001**: `agdt-gh-request-copilot-review` reports `"verified": true` on at
  least 95% of runs where the POST request succeeds (observed from workflow logs
  over 20+ consecutive invocations — this is an observational metric collected
  from existing CI/workflow run logs, not a new integration test requirement).
- **SC-002**: Verification completes within ~55 seconds of wall-clock time in
  the worst case, computed as: (attempt\_count × per\_attempt\_timeout) +
  total\_backoff = (5 × 5s) + 30s = 55s. Returns immediately on first success.
- **SC-003**: When verification fails, the stderr diagnostic output contains
  enough information (login values, team slugs, elapsed time, retry count) to
  distinguish a timing race from a structural mismatch without additional
  debugging.
- **SC-004**: All existing JSON output fields (`prNumber`, `repo`, `requested`,
  `reviewer`, `verified`, `retries`) and state keys
  (`github.copilot_review_requested`, `github.copilot_review_request_verified`)
  remain unchanged — no renames or removals.
- **SC-005**: All new and modified logic is covered by unit tests with mocked
  `run_safe` responses; no live GitHub API access required.

## Requirements

### Functional Requirements

#### P1

- **FR-001**: `_verify_reviewer_requested()` must iterate over the `users`
  array in the API response when searching for the Copilot bot login.
  (The `teams` array uses `slug`, not `login`, and team-based reviewer
  routing is out of scope per Non-Goals.)
- **FR-002**: The retry loop must use exponential backoff (e.g., base 2s,
  factor 2×) instead of a fixed 5-second delay.
- **FR-003**: The maximum number of retries must provide at least 30 seconds of
  cumulative backoff delay (e.g., 4 retries: 2s + 4s + 8s + 16s = 30s). Total
  wall time including API call durations is bounded by SC-002 (~55s, computed as
  5 attempts × 5s timeout + 30s backoff).
- **FR-004**: Verification must return `True` as soon as the bot is found on
  any attempt, without waiting for remaining retries.

#### P2

- **FR-005**: On final verification failure, the system must emit a diagnostic
  message to stderr containing: login values found in `users`, team slugs found
  in `teams`, total elapsed time, and retry count.
- **FR-006**: New diagnostic fields added to the JSON result (e.g.,
  `diagnostics`, `elapsedSeconds`) must be additive — no existing fields may be
  removed or renamed.
- **FR-007**: The JSON result schema must continue to include `prNumber`,
  `repo`, `requested`, `reviewer`, `verified`, and `retries`. The `retries`
  field represents the number of additional attempts after the initial one
  (0 = success on first try).

#### P3

- **FR-008**: When the verification API returns an unexpected or empty response
  shape on every retry (i.e., no attempt produced a well-formed JSON object
  with a `users` key), the system should set a `degraded` flag in the result
  and include an explanatory message rather than reporting a hard failure. If
  at least one attempt returned a well-formed response, degraded mode is NOT
  triggered (see AC-1.2 composition rules).

### Non-Functional Requirements

- **NFR-001 Backward compatibility**: Existing JSON output fields and state keys
  must not be removed or renamed. New fields are additive only.
- **NFR-002 Determinism**: For a given sequence of API responses, the retry
  behavior and final result must be deterministic.
- **NFR-003 Performance**: The maximum verification window (~55s wall time)
  must not block the caller longer than necessary — early exit on success is
  required (FR-004).
- **NFR-004 Testability**: All retry and parsing logic must be unit-testable
  with mocked `run_safe` responses, without requiring live GitHub API access.
- **NFR-005 Per-attempt timeout**: Each verification API call must use a fixed
  `run_safe(..., timeout=...)` value of 5 seconds to prevent a single hung call
  from violating the SC-002 wall-time bound. The worst-case formula is:
  (attempt\_count × per\_attempt\_timeout) + total\_backoff = (5 × 5s) + 30s =
  55s. Timeouts are treated as retryable failures and included in diagnostic
  output.

## Edge Cases

1. The bot appears in `users` on the first attempt — verification should succeed
   immediately with zero retries.
2. The bot appears in `users` only after a delay (e.g., 3rd retry) — should
   succeed on that attempt.
3. The API returns `{"users": [], "teams": []}` on every attempt — should fail
   with diagnostics after exhausting retries.
4. The API returns a non-JSON response or HTTP error — should warn and continue
   retrying.
5. The API returns users but none match the expected login — diagnostics should
   list the logins that were found.
6. Network timeout during a verification attempt — should not crash; should
   retry on next attempt.
7. The bot login constant is correct but casing differs — comparison is already
   case-insensitive (preserved).

---
_Generated by Copilot SDK (claude-opus-4.6) — expanded per review feedback._
