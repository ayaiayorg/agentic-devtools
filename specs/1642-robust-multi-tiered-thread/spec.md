# Feature Specification: Robust Multi-Tiered Thread Resolution System for the AI PR Loop

**Feature Branch**: `speckit/1642/phase-2-clarify`  
**Created**: 2026-05-28  
**Status**: Draft  
**Input**: GitHub Issue #1642: Robust Multi-Tiered Thread Resolution System for the AI PR Loop
**Source Issue**: #1642 (<https://github.com/ayaiayorg/agentic-devtools/issues/1642>)

---

## Clarifications

### Session 2026-05-28

- Q: Should the automation marker patterns (FR-006) be hardcoded or configurable via `.github/agdt-config.json`? → A: Hardcoded in source for the initial implementation with an explicit extension
  point (a module-level constant list). A future iteration can load overrides from `.github/agdt-config.json` under a `"resolution"` key, but this is out of scope for Phase 1. The hardcoded list is:
  `["autofix applied", "suggestion applied", "fix applied"]` (case-insensitive substring match against the most recent comment body).
- Q: What is the TTL for tentatively-marked threads before the system gives up re-evaluation? → A: 5 pipeline iterations OR 24 hours wall-clock time, whichever comes first. After expiry, the tentative
  marker reply is updated to indicate "resolution abandoned — manual review required" and the thread is no longer re-evaluated.
- Q: Which model and prompt template should the CLI fallback agent (FR-009) use? → A: Use `claude-sonnet-4.6` (standard tier, cost-effective for binary decisions) with a dedicated prompt template at
  `agentic_devtools/prompts/default-thread-resolution-fallback-prompt.md`. Use this exact repo-relative path consistently throughout the spec; do not shorten it to
  `default-thread-resolution-fallback-prompt.md`. The prompt is optimized for a single binary output (`RESOLVE` or `UNRESOLVE`) given the comment body, diff context, and file path.
- Q: How should the diff heuristic tier handle multi-line review comments that span a range (e.g., lines 10–25) where only part of the range was modified? → A: Any overlap between the modified lines
  and the comment's line range (`startLine` to `line`) constitutes a positive match. The tier resolves the thread if at least one line within the range was modified, since the reviewer's concern was
  about code that has now changed.
- Q: Should the "new commit since review" precondition (FR-003) compare against the specific review that created each thread, or against the most recent Copilot review on the PR? → A: Per-thread
  comparison against the specific review commit that originated the thread (the `commit_id` field on the review containing the
  thread's first comment). This allows threads from different review cycles to
  be independently evaluated — a thread from review cycle 1 can be resolved even while review cycle 2 is in progress.

---

## Problem Statement

The AI PR Loop's review thread resolution system currently relies almost exclusively on SDK/AI evaluation to determine whether a review comment has been addressed by the coding agent's fix. While a
programmatic diff heuristic exists (`check_lines_modified` in `diff_heuristic.py`), it is not integrated into the main resolution decision path within `finalize_post_repair`. Every comment —
regardless of how obvious the resolution signal is — incurs a full Copilot SDK call with model inference. This is wasteful, slow, and fragile: SDK timeouts, ambiguous responses, and token budget
exhaustion all lead to unresolved threads that block the merge pipeline or, conversely, to threads that are silently left unresolved when they could have been confidently resolved programmatically.

The current precondition gates on `ResolveThreadsAction.evaluate` require both `ci_passing` and `no_pending_review` before thread resolution can proceed. These gates are architecturally incorrect for
thread resolution specifically: whether a review comment was addressed by a code change is independent of whether CI is green or whether a new Copilot review is pending. The CI gate means that threads
cannot be resolved until a potentially slow CI pipeline completes, even when the diff clearly shows the comment was addressed. The pending-review gate means threads from a prior review cycle cannot be
resolved while a fresh review is in-flight — but the resolution of prior threads should not be coupled to new review lifecycle events. These irrelevant preconditions create unnecessary delays in the
merge pipeline and sometimes prevent resolution entirely when CI is flaky or review requests are pending for unrelated reasons.

The reply infrastructure for resolved threads is minimal: a single "Addressed" text reply is posted before resolution, with no structured explanation of why the system determined the comment was
addressed. Human reviewers inspecting the PR history see resolved threads with no audit trail explaining the resolution rationale. When the SDK produces an ambiguous or invalid response, there is no
retry with reformulated prompts, no dedicated fallback evaluation path, and no tentative-resolution mechanism that could mark a thread as "likely resolved" pending re-evaluation. The
`_verify_comments_via_sdk` function parses the raw SDK response with a simple string-contains check (`"COMMENT_RESOLVE" in raw and "COMMENT_UNRESOLVE" not in raw`), which is brittle and does not
enforce structured response formatting. Invalid or malformed responses default to `COMMENT_UNRESOLVE` without logging sufficient context for debugging, and without attempting a retry or reprompt.

Furthermore, the GraphQL query (`_REVIEW_THREADS_QUERY`) fetches only `isResolved` and comment `databaseId` fields. It does not retrieve `isOutdated` (which GitHub sets automatically when the
underlying code has changed since the comment was posted), comment bodies (needed for pattern matching like "autofix applied"), comment timestamps (needed for temporal correlation with commits), file
paths, or line numbers. These metadata fields would enable an entire tier of programmatic resolution signals that currently require no AI inference at all. A thread marked `isOutdated` by GitHub's own
heuristics is an extremely strong signal that the commented code was modified; a comment body containing "autofix applied" or similar automation markers indicates the fix was applied by a tool and
requires no AI judgment.

The combined effect of these deficiencies is a thread resolution system that is slower than necessary, more expensive in tokens, less reliable under failure conditions, harder to audit, and less
explainable to human reviewers than it could be.

---

## User Scenarios & Testing

### User Story 1 — Programmatic Resolution of Outdated Threads (Priority: P1)

As the AI PR Loop automation, I want to resolve review threads that GitHub has marked as `isOutdated` without invoking the Copilot SDK, so that obviously-addressed comments are resolved instantly and
cheaply. When GitHub marks a thread as outdated, it means the underlying code at the commented file/line has changed since the comment was posted. This is the strongest programmatic signal available
and should be the first tier of evaluation.

**Why this priority**: This is the highest-value programmatic signal — `isOutdated` is a platform-native indicator that requires zero AI inference, zero token cost, and resolves the largest category
of threads (any comment on code that was subsequently modified). Implementing this tier alone would eliminate the majority of SDK calls in typical PR review cycles.

**Independent Test**: Can be tested by creating a PR with a review comment on a specific line, pushing a commit that modifies that line, then verifying the resolution system resolves the thread
without any SDK invocation and posts a structured reply explaining the programmatic rationale.

**Acceptance Scenarios**:

1. **Given** a PR with an unresolved review thread where `isOutdated` is `true` in the GraphQL response, **When** the thread resolution action executes, **Then** the thread is resolved without
   invoking the Copilot SDK, and a structured reply is posted explaining that the commented code was modified (citing the `isOutdated` signal).
2. **Given** a PR with an unresolved review thread where `isOutdated` is `false`, **When** the thread resolution action executes, **Then** the system does not resolve based on this signal alone and
   proceeds to the next evaluation tier.
3. **Given** a PR where the GraphQL query fails to return the `isOutdated` field for a thread (API degradation or `isOutdated: null`), **When** the thread resolution action executes, **Then** the
   system falls through to
   the next tier gracefully without erroring, treating the value as "unknown".

---

### User Story 2 — Removal of Irrelevant Preconditions (Priority: P1)

As the AI PR Loop automation, I want thread resolution to proceed regardless of CI status and pending review state, so that addressed comments are resolved as soon as a fix commit is detected on the
branch rather than waiting for unrelated pipeline stages to complete. The determination of whether a code change addresses a review comment is logically independent of whether CI passes or whether a
new review has been requested.

**Why this priority**: The current `ci_passing` and `no_pending_review` preconditions create the most commonly observed failure mode — threads that are clearly addressed remain unresolved for minutes
or hours waiting for CI, or indefinitely when CI is flaky. Removing these gates is a prerequisite for the resolution system to function reliably in all scenarios.

**Independent Test**: Can be tested by simulating a PR where CI is failing (e.g., due to an unrelated flaky test) but a review comment has been addressed by the latest commit, then verifying the
thread is still evaluated and resolved.

**Acceptance Scenarios**:

1. **Given** a PR where CI status is `"failing"` and an unresolved review thread exists from a prior commit, **When** the thread resolution action evaluates preconditions, **Then** the action proceeds
   to execute (does not skip due to CI status).
2. **Given** a PR where a Copilot review is pending on the current HEAD and an unresolved review thread exists from a prior commit, **When** the thread resolution action evaluates preconditions,
   **Then** the action proceeds to execute (does not skip due to pending review).
3. **Given** a PR where no new commit exists since the review comment (same HEAD SHA as the review commit that originated the thread), **When** the thread resolution action evaluates preconditions,
   **Then** the action is
   skipped (the "new commit since review" precondition is the only valid gate, evaluated per-thread using commit OIDs).

---

### User Story 3 — Pattern-Based Resolution for Known Automation Markers (Priority: P2)

As the AI PR Loop automation, I want to resolve threads whose comment body contains known automation markers (such as "autofix applied", "suggestion applied", or tool-generated acknowledgments), so
that threads created by automated tooling are resolved programmatically without SDK cost.

**Why this priority**: This is the second tier of programmatic resolution. While less common than `isOutdated` threads, automation-marker threads are unambiguous and can be resolved with simple
pattern matching. This reduces SDK load further and handles cases where `isOutdated` may not be set (e.g., the comment is on a file that was not modified but the fix was applied elsewhere by an
autofix tool).

**Independent Test**: Can be tested by creating a PR thread with a comment body containing "autofix applied" and verifying it is resolved without SDK invocation.

**Acceptance Scenarios**:

1. **Given** a PR thread where the most recent comment body contains the text "autofix applied" (case-insensitive substring match), **When** the thread resolution action executes, **Then** the thread
   is resolved
   without SDK invocation, with a reply citing the automation marker.
2. **Given** a PR thread where the most recent comment body does not match any known automation pattern from the hardcoded list (`["autofix applied", "suggestion applied", "fix applied"]`) (older
   comments are ignored for this tier), **When** the thread resolution action executes, **Then** the system does not resolve on this tier and proceeds to
   the diff heuristic tier.

---

### User Story 4 — Diff Heuristic Integration for Line-Level Resolution (Priority: P2)

As the AI PR Loop automation, I want to resolve threads where the diff between the review commit and HEAD shows that the specific file and line range referenced by the comment were modified, so that
clear code changes at the exact commented location are resolved without SDK cost.

**Why this priority**: The `check_lines_modified` function already exists but is not wired into the resolution decision path. Integrating it as a programmatic tier between pattern matching and SDK
evaluation captures a large category of "the line was changed" resolutions at zero token cost.

**Independent Test**: Can be tested by creating a review comment on line 42 of a file, pushing a commit that modifies line 42, and verifying the thread is resolved by the diff heuristic without SDK
invocation.

**Acceptance Scenarios**:

1. **Given** a review comment anchored to file `src/foo.py` line 42, and the diff between review commit and HEAD shows line 42 was modified in `src/foo.py`, **When** the thread resolution action
   executes and the thread was not resolved by prior tiers, **Then** the thread is resolved with a reply citing the line-level modification.
2. **Given** a review comment anchored to file `src/foo.py` line 42, and the diff shows no modification to lines 40–44 in that file, **When** the thread resolution action executes, **Then** the system
   does not resolve on this tier and proceeds to SDK evaluation.
3. **Given** a PR-level comment with no file/line anchor, **When** the diff heuristic tier evaluates, **Then** it skips this comment (cannot determine line-level relevance) and proceeds to SDK
   evaluation.
4. **Given** a multi-line review comment spanning lines 10–25, and the diff shows only line 18 was modified, **When** the diff heuristic tier evaluates, **Then** the thread is resolved because at
   least one line within the comment's range was modified (any overlap constitutes a match).

---

### User Story 5 — SDK Evaluation with Strict Validation, Retry, and Fallback (Priority: P2)

As the AI PR Loop automation, I want the SDK evaluation tier to enforce a structured response format (VERDICT + EXPLANATION), retry on malformed responses with a reformulated prompt, and fall back to
a dedicated CLI agent when retries are exhausted, so that ambiguous SDK responses do not silently leave threads unresolved without due diligence.

**Why this priority**: The SDK tier is the final evaluator for threads that cannot be resolved programmatically. Its reliability directly determines the system's overall resolution rate. The current
string-contains parsing is brittle; structured validation and retry improve the hit rate substantially.

**Independent Test**: Can be tested by mocking the SDK to return malformed responses on first attempt and valid responses on retry, verifying the retry fires and the thread is ultimately resolved (or,
if all retries fail, the fallback agent is invoked).

**Acceptance Scenarios**:

1. **Given** a thread that reaches SDK evaluation, **When** the SDK returns a response in the format `VERDICT: COMMENT_RESOLVE\nEXPLANATION: ...`, **Then** the thread is resolved and the explanation
   is included in the posted reply.
2. **Given** a thread that reaches SDK evaluation, **When** the SDK returns a malformed response (no VERDICT line or unrecognized verdict value), **Then** the system retries once with a reformulated
   prompt that emphasizes the required format.
3. **Given** a thread where both SDK attempts return malformed responses, **When** retries are exhausted, **Then** the system invokes a dedicated CLI fallback agent (`claude-sonnet-4.6` with the
   `agentic_devtools/prompts/default-thread-resolution-fallback-prompt.md` template) for evaluation, and if that also
   fails, leaves the thread unresolved with a tentative marker reply.

---

### User Story 6 — Structured Reply and Audit Trail on Every Resolution (Priority: P2)

As a human reviewer inspecting a PR's thread history, I want every resolved thread to have a structured reply explaining why the system resolved it (which tier, what evidence, what confidence level),
so that I can audit the automation's decisions and override them if I disagree.

**Why this priority**: Auditability and explainability are essential for human trust in the automation. Without structured replies, reviewers cannot distinguish between a thread that was correctly
resolved and one that was erroneously dismissed.

**Independent Test**: Can be tested by resolving threads via each tier and verifying the reply content matches the expected structured format with tier identification, evidence citation, and
confidence indicator.

**Acceptance Scenarios**:

1. **Given** a thread resolved by the `isOutdated` programmatic tier, **When** the resolution reply is posted, **Then** it contains a structured HTML marker identifying the tier as
   "programmatic:outdated", the confidence as "high", and an explanation referencing GitHub's `isOutdated` signal.
2. **Given** a thread resolved by SDK evaluation, **When** the resolution reply is posted, **Then** it contains a structured HTML marker identifying the tier as "sdk:copilot", the SDK's explanation
   text, and the model identifier used.
3. **Given** a thread that could not be confidently resolved (tentative), **When** a reply is posted, **Then** it contains a "tentative" marker and an explanation that this resolution will be
   re-evaluated on the next loop iteration.

---

### User Story 7 — Tentative Resolution with Re-evaluation (Priority: P3)

As the AI PR Loop automation, I want to mark threads as "tentatively resolved" when evidence is suggestive but not conclusive, and re-evaluate them on the next pipeline iteration, so that borderline
cases are not permanently dismissed or permanently blocked.

**Why this priority**: This is an advanced reliability feature. The core system works without it (threads are either resolved or left open), but tentative markers improve the experience for threads in
ambiguous states.

**Tentative TTL**: Tentatively-marked threads are re-evaluated for a maximum of 5 pipeline iterations OR 24 hours wall-clock time (whichever comes first). After expiry, the tentative marker reply is
updated to "resolution abandoned — manual review required" and the thread is no longer re-evaluated.

**Independent Test**: Can be tested by creating a scenario where the SDK returns "ambiguous" and verifying the thread receives a tentative marker reply but is NOT resolved via GraphQL mutation, and on
the next iteration is re-evaluated.

**Acceptance Scenarios**:

1. **Given** a thread where SDK evaluation returns an ambiguous verdict, **When** the resolution action completes, **Then** the thread is NOT resolved (no GraphQL mutation), a tentative marker reply
   is posted, and the thread is flagged for re-evaluation in the resolution state.
2. **Given** a tentatively-marked thread on a subsequent pipeline iteration where new evidence is available (e.g., the line is now modified), **When** the resolution action runs, **Then** the
   programmatic tier resolves the thread normally, updating the tentative reply to a confirmed resolution reply.
3. **Given** a tentatively-marked thread that has been re-evaluated for 5 iterations without resolution, **When** the resolution action runs, **Then** the tentative marker reply is updated to
   "resolution abandoned — manual review required" and the thread is excluded from further re-evaluation.

---

### User Story 8 — Platform-Agnostic Resolution Engine Interface (Priority: P3)

As a developer extending the AI PR Loop to support Azure DevOps or Jira in the future, I want the resolution evaluation engine (tiers, state machine, reply formatting) to be defined through
platform-agnostic interfaces, so that only the thread-fetching and mutation operations need provider-specific implementations.

**Why this priority**: This is architectural investment for future extensibility. The current implementation works for GitHub only, but the issue explicitly requests a platform-agnostic foundation.

**Independent Test**: Can be tested by verifying that the evaluation engine accepts an abstract thread representation (not GitHub-specific types) and that a mock provider implementation can drive the
full resolution pipeline.

**Acceptance Scenarios**:

1. **Given** the resolution engine receives a thread via the platform-agnostic `ReviewThread` interface, **When** all tiers are evaluated, **Then** no GitHub-specific types or API calls are referenced
   in the evaluation logic (only in the provider adapter layer).
2. **Given** a new provider adapter is implemented (e.g., a mock `AzureDevOpsProvider`), **When** it supplies threads conforming to the `ReviewThread` interface, **Then** the resolution engine
   evaluates them identically to GitHub threads.

---

### Edge Cases

- What happens when the GraphQL API returns a thread with `isOutdated: null` (field not available on older GitHub Enterprise Server versions)? The system MUST treat this as "unknown" and fall through
  to subsequent tiers, never erroring.
- How does the system handle a thread with zero comments (edge case in GitHub API)? It MUST be skipped entirely as there is no content to evaluate.
- What happens when the diff between review commit and HEAD is empty (force-push that re-bases without code changes)? All line-level heuristics MUST return "not modified" and the system MUST fall
  through to SDK evaluation.
- How does the system behave when the SDK token budget is exhausted mid-batch? Remaining comments in the batch MUST be left unresolved (not tentative), logged with the budget-exhaustion reason, and
  retried on the next iteration.
- What happens when a thread has been resolved by a human between the snapshot fetch and the resolution attempt? The GraphQL mutation will return a no-op; the system MUST detect this gracefully and
  not count it as a failure.
- How does the diff heuristic handle multi-line comments where only part of the range was modified? Any overlap (at least one line modified within the `startLine` to `line` range) constitutes a
  positive match and triggers resolution.
- What happens when a tentatively-marked thread exceeds the re-evaluation TTL (5 iterations or 24 hours)? The system updates the reply to "resolution abandoned — manual review required" and stops
  re-evaluating.

---

## Requirements

### Functional Requirements

- **FR-001**: The system MUST evaluate threads through a tiered pipeline in strict order: (1) `isOutdated` check, (2) automation marker pattern match, (3) diff line-level heuristic, (4) SDK/AI
  evaluation. A thread resolved at any tier MUST NOT be evaluated by subsequent tiers.

- **FR-002**: The system MUST NOT use CI status (`ci_passing`) as a precondition for thread resolution. Thread resolution MUST proceed regardless of whether CI checks have passed, failed, or are still
  running.

- **FR-003**: The system MUST NOT use pending Copilot review state (`no_pending_review`) as a precondition for thread resolution. The only valid precondition for resolution is that a new commit exists
  on the branch since the review that created the thread. "The review that created the thread" is defined per-thread as the GitHub review whose `commit_id` (the HEAD SHA at the time the review was
  submitted) matches or precedes the commit that introduced the first comment in that thread; comparison MUST use commit OIDs (not timestamps) obtained from the GraphQL `ReviewThread.comments` node
  `commit` field. If the current HEAD OID equals the thread's originating review `commit_id`, the precondition is not met and the thread MUST be skipped.

- **FR-004**: The system MUST expand the `_REVIEW_THREADS_QUERY` GraphQL query to fetch `isOutdated`, `path`, `line`, `startLine`, and for each comment node: `body`, `createdAt`, `author { login }`,
  in addition to the existing `isResolved` and `databaseId` fields.

- **FR-005**: The system MUST resolve any thread where `isOutdated` is `true` without invoking the SDK, posting a structured reply that cites the `isOutdated` signal as the resolution rationale. When
  `isOutdated` is `null` or absent, the system MUST treat this as "unknown" and fall through to subsequent tiers.

- **FR-006**: The system MUST detect and resolve threads whose most recent comment body matches a hardcoded set of automation marker patterns (initially: `["autofix applied", "suggestion applied",
  "fix applied"]`, case-insensitive substring match) without invoking the SDK. The pattern list is defined as a module-level constant to enable future externalization to `.github/agdt-config.json`
  without architectural changes.

- **FR-007**: The system MUST integrate the existing `check_lines_modified` diff heuristic into the resolution pipeline as tier 3, resolving threads where the specific file/line range referenced by
  the comment was modified in the diff between the review commit and HEAD. Any overlap between the modified lines and the comment's line range (`startLine` to `line`) constitutes a positive match.

- **FR-008**: The SDK evaluation tier MUST enforce a structured response format requiring both a `VERDICT` field (one of `COMMENT_RESOLVE`, `COMMENT_UNRESOLVE`, `AMBIGUOUS`) and an `EXPLANATION`
  field. Responses not matching this format MUST be treated as malformed. These SDK-level response tokens map to the internal `ResolutionVerdict` enum as follows: `COMMENT_RESOLVE` → `RESOLVE`;
  `COMMENT_UNRESOLVE` → `UNRESOLVE`; `AMBIGUOUS` triggers the retry/fallback path and, if all fallbacks are exhausted without a confident verdict, results in `TENTATIVE`.

- **FR-009**: On malformed SDK response, the system MUST retry once with a reformulated prompt that explicitly emphasizes the required response format. If the retry also produces a malformed response,
  the system MUST invoke a dedicated CLI fallback agent (`claude-sonnet-4.6` model, using the
  `agentic_devtools/prompts/default-thread-resolution-fallback-prompt.md` template optimized for
  binary `RESOLVE`/`UNRESOLVE` decisions) for evaluation.

- **FR-010**: If all evaluation tiers (including SDK retry and fallback) fail to produce a confident verdict, the system MUST leave the thread unresolved and post a tentative marker reply indicating
  the thread will be re-evaluated on the next iteration. Tentative markers expire after 5 pipeline iterations or 24 hours wall-clock time, whichever comes first.

- **FR-011**: The system MUST post a structured reply on every resolution action (whether resolved, left open, or marked tentative). The reply MUST include: the evaluation tier that produced the
  verdict, the evidence or rationale, and a confidence indicator (high/medium/low).

- **FR-012**: Structured replies MUST contain HTML markers (e.g., `<!-- agdt:resolution-tier:programmatic:outdated -->`) that enable programmatic parsing of resolution metadata by downstream tools or
  future re-evaluation passes.

- **FR-013**: The resolution evaluation engine MUST be defined through platform-agnostic interfaces (`ReviewThread`, `ResolutionVerdict`, `ThreadResolver`) that do not reference GitHub-specific types.
  Provider-specific logic (GraphQL queries, mutations, reply formatting) MUST be isolated in adapter classes.

- **FR-014**: Tentatively-marked threads MUST be re-evaluated on subsequent pipeline iterations. If new evidence is available (e.g., the line is now modified, or the thread became `isOutdated`), the
  system MUST upgrade the tentative marker to a confirmed resolution. After 5 iterations or 24 hours without confident resolution, the tentative marker is updated to "resolution abandoned — manual
  review required" and re-evaluation ceases.

- **FR-015**: The system MUST maintain per-thread resolution state (tier used, verdict, confidence, timestamp, iteration count for tentative threads) in a serializable format within the pipeline's
  state management, enabling audit queries
  and cross-iteration tracking.

### Non-Functional Requirements

- **NFR-001**: The complete tiered evaluation of a single thread (all tiers, including SDK if needed) MUST complete within 45 seconds. Programmatic tiers (1–3) MUST complete within 500 milliseconds
  per thread.

- **NFR-002**: The system MUST reduce SDK/AI invocations by at least 40% compared to the current implementation (where every thread requires an SDK call), measured across a representative sample of
  PRs with ≥5 review threads.

- **NFR-003**: All resolution decisions (including intermediate tier evaluations) MUST be logged at DEBUG level with sufficient context for post-hoc debugging, including the thread ID, comment body
  snippet (first 100 characters), tier evaluated, and verdict produced.

- **NFR-004**: The resolution engine MUST handle GraphQL API rate limiting gracefully, backing off exponentially (initial delay 1s, max delay 60s, max retries 5) and resuming without data loss.
  Partial progress (threads already resolved) MUST be
  preserved across retries.

- **NFR-005**: Reply content posted to threads MUST be human-readable as standalone text (not requiring parsing of HTML markers to understand the resolution rationale). The HTML markers are
  supplementary metadata, not a replacement for prose explanation.

- **NFR-006**: The platform-agnostic interfaces MUST be defined as Python Protocol classes (structural subtyping) rather than abstract base classes, enabling provider implementations without
  inheritance coupling.

### Key Entities

- **ReviewThread**: Platform-agnostic representation of a review comment thread. Contains: thread identifier, file path, line range (`startLine`, `line`), `isOutdated` flag (tri-state:
  `True`/`False`/`None` for unknown), comments (body, author, timestamp), resolution
  state, originating review commit OID.

- **ResolutionVerdict**: The outcome of evaluating a single thread. Contains: verdict enum (`RESOLVE`, `UNRESOLVE`, `TENTATIVE`), tier that produced the verdict, confidence level
  (`high`/`medium`/`low`), explanation text,
  evidence references. Note: these values are the internal representation; the SDK evaluation tier uses raw response tokens (`COMMENT_RESOLVE`, `COMMENT_UNRESOLVE`, `AMBIGUOUS`) that are mapped to
  this enum per FR-008.

- **EvaluationTier**: An ordered evaluation stage in the pipeline. Each tier receives a `ReviewThread` and produces either a `ResolutionVerdict` (short-circuiting further evaluation) or `None`
  (falling through to the next tier). Defined as a Python Protocol with a single `evaluate(thread: ReviewThread) -> ResolutionVerdict | None` method.

- **ResolutionReply**: Structured content posted to a thread after evaluation. Contains: human-readable explanation, HTML metadata markers (e.g., `<!-- agdt:resolution-tier:... -->`), tier
  identification, timestamp, and model identifier (for
  SDK tier).

- **ThreadResolutionState**: Per-thread state persisted across iterations. Contains: thread ID, current verdict, tier used, confidence, timestamp of last evaluation, iteration count (for tentative TTL
  tracking), tentative expiry timestamp.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Programmatic tiers (outdated, pattern, diff heuristic) resolve at least 50% of threads that were previously resolved only via SDK, measured across the next 20 PRs processed by the AI PR
  Loop after deployment.

- **SC-002**: SDK invocation count per PR decreases by at least 40% compared to the 10-PR rolling average prior to deployment, for PRs with 5 or more review threads.

- **SC-003**: Mean time from fix-commit push to thread resolution decreases by at least 30% compared to the pre-deployment baseline, measured as the time delta between the HEAD commit timestamp and
  the thread resolution timestamp.

- **SC-004**: Zero threads are resolved without a structured reply posted. 100% of resolved threads have a reply containing a valid tier identifier and explanation, verified by a post-deployment audit
  script scanning the last 50 resolved threads.

- **SC-005**: The resolution system processes all threads on a PR with ≤10 review threads within 60 seconds total wall-clock time (including all tiers and API calls), verified by pipeline timing logs.

- **SC-006**: Zero regressions in false-resolution rate: the number of threads resolved that are subsequently re-opened by a human reviewer does not increase compared to the pre-deployment 10-PR
  baseline. Target: ≤2% re-open rate.

- **SC-007**: Platform-agnostic interfaces are validated by the existence of at least one non-GitHub mock provider in the test suite that exercises the full evaluation pipeline, confirming no
  GitHub-specific type leakage.

---

## Clarifications (Resolved)

1. ~~**Configurable automation markers**: Should the list of automation marker patterns (FR-006) be hardcoded in source or configurable via a repository-level config file (e.g.,
   `.github/agdt-config.json`)?~~ **RESOLVED**: Hardcoded as a module-level constant for Phase 1, with architecture supporting future externalization to `.github/agdt-config.json`.

2. ~~**Tentative resolution TTL**: How many pipeline iterations should a tentatively-marked thread persist before the system gives up re-evaluation and treats it as permanently unresolved?~~
   **RESOLVED**: 5 pipeline iterations OR 24 hours wall-clock time, whichever comes first.

3. ~~**CLI fallback agent identity**: Which CLI agent model and prompt template should the fallback agent (FR-009) use?~~ **RESOLVED**: `claude-sonnet-4.6` with
   `agentic_devtools/prompts/default-thread-resolution-fallback-prompt.md` template, optimized for binary `RESOLVE`/`UNRESOLVE` decisions.

---
*Generated by Copilot SDK (claude-opus-4.6)*
