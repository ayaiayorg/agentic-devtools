# Specification Quality Checklist: Resilient Error Handling and Retry Logic for SpecKit Pipeline Scripts

**Purpose**: Validate specification completeness before proceeding to planning
**Created**: 2026-05-05
**Feature**: [spec.md](../spec.md)
**Source Issue**: #1326

## Content Quality

- [ ] CHK001 Each user story clearly articulates value to a specific persona (maintainer, pipeline script developer, reliability engineer) rather than describing implementation mechanics
- [ ] CHK002 All four user stories follow "As a [role], I want [capability], so that [benefit]" format with explicit role, capability, and measurable benefit
- [ ] CHK003 Priority assignments (P1 for US1/US2, P2 for US3, P3 for US4) are justified with "Why this priority" rationale tied to real-world impact
- [ ] CHK004 Functional requirements FR-001 through FR-013 describe either observable runtime behaviours (exit codes, retry attempts, log output) or structural constraints verified via
  static inspection (e.g., FR-007/FR-008 library creation, FR-012 shared library sourcing). Named internal functions are prescribed under two distinct rules:
  (a) **shared integration points** reused across multiple scripts (e.g., `calculate_backoff_delay`, referenced in FR-005, FR-006, and Key Entities); and (b) **script-local wrappers** whose
  behaviour must be explicitly specified for testability (e.g., `curl_with_retry` in FR-005, scoped to `post-issue-comment.sh`). Rule (b) does not make the function a shared integration point —
  it remains local to one script but is named because its retry-decision contract (HTTP status classification, transport error handling, backoff delegation) must be verifiable

## Requirement Completeness

- [ ] CHK005 Each acceptance scenario in US1–US4 is independently testable without requiring live API access — via stubbed/mocked external commands (`gh`, `curl`) for network-dependent scripts, via
  direct function invocation for shared library helpers (US3), via injected error conditions (invalid input, missing variables) for pure local scripts (US4), and via structural grep-based
  inspection for code-organisation constraints (US1 scenario 7, US2 scenario 17)
- [ ] CHK006 Edge cases section covers rate limiting (429 and 403 with `Retry-After`), plain 429 without `Retry-After` (still retryable), plain 403 without `Retry-After` (non-retryable client
  error), missing `gh` CLI (exit code 127), unset `GITHUB_OUTPUT`, DNS failure, and HTTP redirects with explicit expected behaviour for each — and US2 has matching acceptance scenarios for all
  four rate-limit/403 permutations (429 with header, 429 without header, 403 with header, 403 without header)
- [ ] CHK007 All acceptance scenarios use Given/When/Then format with specific observable outcomes: HTTP codes, exit codes, or stderr patterns for runtime scenarios, and grep counts or
  structural match results for static-inspection scenarios (US1 scenario 7, US2 scenario 17)
- [ ] CHK008 Success criteria SC-001 through SC-006 include concrete verification methods (CI run logs, grep commands, integration tests, end-to-end pipeline runs)
- [ ] CHK009 Scope boundaries explicitly exclude pure local scripts (`sanitize-branch-name.sh`, `validate-label.sh`, `check-idempotency.sh`) from retry logic while including them in exit-code
  propagation audit
- [ ] CHK010 Dependencies on existing infrastructure are documented: `call_with_retry` in `generate-spec-from-issue.sh`, `GITHUB_OUTPUT` fallback to `/dev/stdout`, Bash 4.x+ on `ubuntu-latest` runners

## Feature Readiness

- [ ] CHK011 FR-001 and FR-002 (`create-spec-pr.sh` failure propagation and retry) have matching acceptance scenarios in US1 (scenarios 1–6) covering success-after-retry, exhausted retries,
  non-retryable pattern detection, missing `gh` binary (exit code 127), and exponential backoff timing verification. FR-012 (shared library sourcing and no-duplication) is independently verified by
  US1 scenario 7, which performs a four-part structural inspection: (a) confirms `create-spec-pr.sh` contains an actual `source`/`.` statement loading `lib/retry.sh` (excluding comments),
  (b) confirms it does NOT define its own `call_with_retry` function (comment lines are excluded via `grep -v '^[[:space:]]*#'` before counting to avoid false positives), (c) confirms at
  least **one** `call_with_retry` invocation exists on non-comment lines — proving the shared helper is actively used (without hard-coding a specific number of literal call sites, since
  a compliant implementation may route multiple retry paths through a local wrapper), AND (d) confirms via context-aware inspection that the primary
  `gh pr create` command is wrapped by `call_with_retry`, positively proving the shared helper is used for the PR creation path specifically
- [ ] CHK012 User scenarios cover the complete lifecycle: PR creation failure (US1), comment posting failure (US2), shared library extraction (US3), and remaining script hardening audit (US4)
- [ ] CHK013 Success criteria SC-001 through SC-004 define measurable pass/fail conditions (GitHub Actions step status, PR creation without intervention, retry-then-succeed behaviour, single
  definition via grep pattern). SC-004's grep verifies both that `call_with_retry` is defined in exactly one file under `.github/scripts/` AND that the defining file is `lib/retry.sh`
  specifically (e.g., via `grep -rlE 'call_with_retry[[:space:]]*(\(|\{)' .github/scripts/ | grep -x '.*/lib/retry\.sh'`). This pattern matches both `call_with_retry() {` and
  `function call_with_retry {` declaration styles, ensuring no alternative syntax bypasses the check. The surviving definition is the shared library — not an inline copy in another script
- [ ] CHK014 NFR-001 through NFR-006 constrain timing (60s max), compatibility (Bash 4.x+), and backward compatibility without dictating internal algorithms beyond the exponential backoff formula
- [ ] CHK015 FR-011 (redirect handling with preserved POST semantics) has a matching acceptance scenario in US2 that validates all three redirect types (301, 302, 303) are exercised at the story
  level, not only documented as an edge case
- [ ] CHK016 FR-010 (diagnostics in error messages) has matching acceptance scenarios in US2 covering both failure modes — HTTP status code diagnostics (scenario 13) and transport exit code
  diagnostics (scenario 14) — and in US3 covering both the final exhausted-attempts message (scenario 2) and the intermediate per-attempt retry log (scenario 5), ensuring the diagnostics contract
  is validated for both primary scripts and both log types (intermediate and terminal)
- [ ] CHK017 FR-009 (retry observability logging) has matching acceptance scenarios that verify retry logs include the attempt number, total configured attempts, and computed delay — directly
  validated in US3 scenario 5 (for the shared `call_with_retry` helper) and in US2 scenario 18 (for `post-issue-comment.sh`'s HTTP-aware `curl_with_retry` loop), ensuring the
  attempt/total/delay contract is independently testable at the story level for both primary retry mechanisms, not merely implied by timing assertions in other scenarios
- [ ] CHK018 FR-013 (ambiguous-success recovery for `create-spec-pr.sh`) has a matching acceptance scenario in US1 (scenario 8) covering the "already exists" recovery path, and SC-001 is scoped
  to exclude this legitimate success path so that a recovered PR does not conflict with the failure-reporting criterion
- [ ] CHK019 FR-005's DRY requirement (`post-issue-comment.sh` reuses `calculate_backoff_delay` from the shared library) is independently verified by US2 scenario 17, which performs a four-part
  structural inspection: (a) confirms `post-issue-comment.sh` contains an actual `source`/`.` statement loading `lib/retry.sh` (excluding comments), (b) confirms it does NOT define its own
  `calculate_backoff_delay` function (comment lines are excluded via `grep -v '^[[:space:]]*#'` before counting to avoid false positives), (c) confirms `calculate_backoff_delay` is invoked
  on non-comment lines, AND (d) confirms via `sed`-based function-body extraction (using a pattern that matches both `curl_with_retry() {` and `function curl_with_retry {` declaration
  styles) that `calculate_backoff_delay` is called on a non-comment line inside `curl_with_retry` (or a helper directly called by it) — comment lines are excluded via
  `grep -v '^[[:space:]]*#'` in the function-body grep step — positively proving the shared library's backoff computation is on the retry execution path rather than at an unrelated
  call site

## Notes

- This checklist was generated from the specification content for issue #1326
- Items marked incomplete require spec updates before proceeding to planning

---
*Generated by Copilot SDK (claude-opus-4.6)*
