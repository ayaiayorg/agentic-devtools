# Feature Specification: Restore Full Resolution Comment Format in AI PR Loop

**Feature Branch**: `speckit/1750/phase-1-specify`  
**Created**: 2026-06-03  
**Status**: Draft  
**Input**: GitHub Issue #1750 — regression in AI PR Loop resolution comment formatting  
**Source Issue**: #1750 (<https://github.com/ayaiayorg/agentic-devtools/issues/1750>)

## Clarifications

### Session 2026-06-03

- Q: In FR-002, when should the HEAD commit SHA be sourced — from the loop's
  current `head_ref_oid` state key, the PR's latest merge-source commit, or a
  parameter passed into `finalize_post_repair()`?
  → A: The HEAD commit SHA should be sourced from the `head_sha` parameter
  passed into `finalize_post_repair()`. No additional API call is required; the
  value is already fetched earlier in the loop iteration.
- Q: Should the `**HEAD**:` commit link line be appended to the output of
  `build_full_reply()` inside `ReplyFormatter`, or should it be concatenated by
  the caller (`finalize_post_repair()`) after invoking the formatter?
  → A: The commit link should be appended by the caller
  (`finalize_post_repair()`) after invoking `build_full_reply()`, since
  `ReplyFormatter` is a pure formatting class that does not have access to
  repository URL or commit context. This keeps the formatter's responsibility
  limited to tier-result formatting.
- Q: For the fallback case where `tier_result` is `None` (FR-003), what static
  message text should precede the HEAD commit link?
  → A: The fallback message should be: `"Addressed on the updated PR branch."`
  followed by the `**HEAD**:` line if available. This preserves backward
  compatibility with the existing static message while adding traceability.
- Q: How should the `owner/repo` value for constructing the commit URL be
  resolved — from the `self._repo` attribute already on the provider, or from
  state?
  → A: Via `self._resolve_repo()`, which returns `self._repo` when set and
  falls back to the `GITHUB_REPOSITORY` environment variable. This is the same
  resolution path used for all other GitHub API calls in the provider and
  requires no additional resolution logic.
- Q: Should the change to always use `build_full_reply()` apply retroactively
  to the `COMMENT_UNRESOLVE` path or only to `COMMENT_RESOLVE`?
  → A: Only to the `COMMENT_RESOLVE` path. The `COMMENT_UNRESOLVE` path
  already has its own distinct formatting logic and is explicitly out of scope
  per FR-005.

## Problem Statement

The AI PR Loop's automated review comment resolution system has suffered a silent regression in
the quality and informativeness of the replies it posts when resolving review threads. When the
system determines that a Copilot review comment has been addressed by code changes on the PR
branch, it posts a reply to the comment thread and resolves it. Previously, these replies
included a verdict emoji (✅ / ❌ / 🔄), a confidence indicator (`[high|medium|low]`), an
explicit textual rationale explaining why the system considered the comment addressed, the
evaluation tier that produced the verdict, and a direct
hyperlink to the HEAD commit that addressed the feedback. This gave reviewers a transparent
audit trail — they could immediately verify whether the automated logic was correct and trace
the resolution to a specific commit.

The current behavior has degraded to posting a generic, uninformative string: "Addressed on the
updated PR branch." This occurs in the `finalize_post_repair()` method of `github_provider.py`
when the code path reaches the `else` branch of the resolution reply logic. Specifically, the
full structured reply (produced by `ReplyFormatter.build_full_reply()`) is only emitted when the
comment is a re-evaluated unconfirmed resolution or when the tier result is explicitly a
fallback. For all other "normal" resolution cases — which constitute the majority of resolved
threads — the system falls back to the static constant `_ADDRESSED_REPLY_BODY`, discarding the
tier result data that is already available in scope.

This regression undermines the core value proposition of automated PR review resolution:
transparency and auditability. Reviewers who see a generic "addressed" message cannot
distinguish between a high-confidence resolution backed by code diff analysis and a tentative
or heuristic resolution. They cannot verify what logic produced the decision, nor can they
click through to the commit that addressed their feedback. This erodes trust in the automation,
increases the likelihood of reviewers re-opening threads unnecessarily, and makes post-hoc
debugging of incorrect resolutions significantly harder. The infrastructure to produce rich,
structured replies already exists and is well-tested — the `ReplyFormatter` class provides
`build_full_reply()`, `format_resolution_reply()`, and `format_unconfirmed_commit_change_reply()`
methods that produce the desired format. The fix is to ensure these formatters are always
invoked when a tier result is available, and to additionally embed a HEAD commit link in the
reply body.

## User Scenarios & Testing

### User Story 1 - Reviewer Auditing Automated Resolution (Priority: P1)

A code reviewer receives a notification that the AI PR Loop has resolved their review
comment. They navigate to the PR thread to verify that the automation correctly identified
their concern as addressed. They expect to see a structured reply that communicates the
system's confidence level, the reasoning behind the resolution decision, and a link to the
specific commit where the fix was applied. This allows them to quickly decide whether to
accept the resolution or reopen the thread for further discussion.

**Why this priority**: This is the primary use case that the regression broke. Every
resolved comment in the AI PR Loop workflow hits this path, making it the highest-impact
scenario. Without this, the entire transparency contract between the automation and human
reviewers is broken.

**Independent Test**: Can be fully tested by triggering a resolution where a `TierResult`
is available (the common case) and verifying the posted reply body contains the verdict
emoji, tier name, rationale text, confidence indicator, and commit link. Delivers immediate
value by restoring reviewer trust.

**Acceptance Scenarios**:

1. **Given** a review comment that has been addressed by code changes and a `TierResult` with
   verdict `RESOLVE` is available, **When** the AI PR Loop resolves the thread, **Then** the
   posted reply contains a verdict emoji (✅), the tier name, a rationale explanation, and a
   link to the current HEAD commit.
2. **Given** a review comment that has been addressed and a non-null `model_id` is provided to
   the reply formatter, **When** the resolution reply is posted, **Then** the reply additionally
   includes a `**Model**:` line identifying the evaluation model.
3. **Given** a review comment being resolved where no `TierResult` is available (edge case),
   **When** the resolution reply is posted, **Then** the system falls back to "Addressed on the
   updated PR branch." followed by the HEAD commit link if the SHA is available in the
   resolution context.

---

### User Story 2 - Reviewer Tracing Resolution to Commit (Priority: P1)

A reviewer wants to verify that a specific commit actually addresses their feedback. They look
at the resolution comment and expect a clickable link to the HEAD commit at the time of
resolution. This link takes them directly to the commit diff where they can confirm the
relevant code change exists.

**Why this priority**: The commit link is the key traceability artifact. Without it, a reviewer
must manually hunt through the commit history to find which change addressed their feedback —
a tedious process that discourages thorough review verification.

**Independent Test**: Can be tested by verifying that the reply body contains a markdown link in
the format `[<short_sha>](https://github.com/<owner>/<repo>/commit/<full_sha>)` when the HEAD
commit OID is available in the resolution context.

**Acceptance Scenarios**:

1. **Given** a resolution context where the HEAD commit SHA is known (sourced
   from the `head_sha` parameter passed into `finalize_post_repair()`), **When**
   the reply is formatted, **Then** the reply body includes a `**HEAD**:` line
   with a markdown hyperlink to the commit on GitHub, appended by the caller
   after `build_full_reply()` output.
2. **Given** a resolution context where the HEAD commit SHA is not available (e.g., due to an
   API error or missing context), **When** the reply is formatted, **Then** the reply is still
   posted without the HEAD line, and no error is raised.

---

### User Story 3 - Distinguishing Confidence Levels Across Resolutions (Priority: P2)

A reviewer scanning multiple resolved threads wants to quickly identify which resolutions are
high-confidence (fully verified by code analysis) versus lower-confidence (heuristic or
fallback). The confidence indicator and tier name in the reply allow them to prioritize which
resolutions to manually verify, focusing their limited review time on uncertain cases.

**Why this priority**: While less critical than having any structured reply at all, the
differentiation between confidence levels is what makes the structured format actionable rather
than merely informative. It enables reviewers to apply triage logic to their verification
workflow.

**Independent Test**: Can be tested by generating replies for tier results with different
confidence values (e.g., `high`, `medium`, `low`) and verifying the confidence indicator appears
in the formatted output in brackets.

**Acceptance Scenarios**:

1. **Given** a `TierResult` with confidence value `high`, **When** the reply is formatted,
   **Then** the reply contains `[high]` as the confidence indicator.
2. **Given** a `TierResult` with confidence value `low`, **When** the reply is formatted,
   **Then** the reply contains `[low]` as the confidence indicator, signaling to the reviewer
   that manual verification is recommended.

---

### User Story 4 - Documentation of Reply Format Variants (Priority: P3)

A developer maintaining the AI PR Loop system needs to understand which reply format is used
in each resolution scenario. They consult inline documentation or a reference table that maps
resolution situations (normal resolve, fallback resolve, unconfirmed commit change, abandoned,
unresolve) to their respective reply formats. This ensures future changes maintain format
consistency and don't inadvertently regress again.

**Why this priority**: Documentation prevents future regressions of the same class. While not
user-facing, it protects the long-term quality of the system.

**Independent Test**: Can be verified by checking that inline code comments or a module-level
docstring in the reply formatter or github_provider module describe the mapping between
resolution scenarios and reply formats.

**Acceptance Scenarios**:

1. **Given** the `reply_formatter.py` or `github_provider.py` module, **When** a developer reads
   the module docstrings or inline comments, **Then** they find a clear description of which
   reply format is used for each resolution scenario type.

---

### Edge Cases

- What happens when `tier_result` is `None` but the verdict is `COMMENT_RESOLVE`? The system
  posts the static fallback message "Addressed on the updated PR branch." with the HEAD commit
  link appended (if the SHA is available), without crashing.
- How does the system handle a `tier_result` with an empty or `None` explanation field? The
  formatter should handle this gracefully by producing a valid reply and using
  `**Rationale**: (no explanation provided)` as the placeholder text.
- What happens when the HEAD commit SHA is available but the repository cannot be resolved into
  `owner/repo` format? Repository resolution is a precondition for appending the HEAD link:
  `finalize_post_repair()` calls `self._resolve_repo()` before reply formatting, so an invalid
  repository value currently raises instead of silently omitting the `**HEAD**:` line.
- How does the existing "has_existing_addressed_reply" detection interact with the new format?
  The detection logic must recognize both the old static text and the new structured format
  (via the HTML marker prefix) as valid existing replies to avoid duplicate posting. The
  existing `_has_existing_addressed_reply` implementation already checks for
  `_RESOLUTION_TIER_MARKER_PREFIX`, so no change is needed for this detection path.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST use the full structured reply format (verdict emoji, tier
  name, rationale, and confidence indicator) for ALL resolution replies where a `TierResult` is
  available, regardless of whether the resolution is a post-confirmation re-evaluation or a
  first-time resolution. Specifically, the `else` branch in `finalize_post_repair()` that
  currently assigns `_ADDRESSED_REPLY_BODY` MUST instead invoke
  `reply_formatter.build_full_reply(tier_result, model_id=self._model_id_for_tier_result(tier_result))`.

- **FR-002**: The system MUST include a HEAD commit link in resolution replies when the commit
  SHA is available via the `head_sha` parameter passed into `finalize_post_repair()`.
  The link format MUST be
  `**HEAD**: [<short_sha>](https://github.com/<owner>/<repo>/commit/<full_sha>)` where
  `<short_sha>` is the first 7 characters of the commit SHA. The link MUST be appended by the
  caller (`finalize_post_repair()`) after the formatted reply body, separated by a blank line.
  The `<owner>/<repo>` value MUST be resolved via `self._resolve_repo()`.

- **FR-003**: The system MUST gracefully handle the case where `tier_result` is `None` by
  falling back to a reply consisting of the static text "Addressed on the updated PR branch."
  followed by the HEAD commit link (if available), maintaining backward compatibility while
  adding traceability.

- **FR-004**: The system MUST continue to recognize the old static reply text ("Addressed on
  the updated PR branch.") as a valid existing addressed reply for the purposes of duplicate
  detection, ensuring backward compatibility with threads resolved before this fix.

- **FR-005**: The system MUST maintain the existing behavior for
  `format_unconfirmed_commit_change_reply()` and `format_abandoned_reply()` — those code paths
  are unaffected by this change and should continue to produce their specialized reply formats.
  The `COMMENT_UNRESOLVE` path is explicitly out of scope.

- **FR-006**: The system MUST emit the `<!-- agdt:resolution-tier:<tier_name> -->` HTML marker
  in all structured replies, enabling programmatic identification and filtering of resolution
  comments by downstream tools.

- **FR-007**: The existing `_has_existing_addressed_reply` detection logic MUST recognize
  replies containing the `_RESOLUTION_TIER_MARKER_PREFIX` HTML comment (which it already does)
  to avoid duplicate replies when re-processing previously resolved threads.

### Non-Functional Requirements

- **NFR-001**: The change MUST NOT increase the latency of the `finalize_post_repair()` method
  by more than 50ms per resolved comment, as the reply formatting is purely string manipulation
  with no additional API calls. Measurement: no new network calls introduced; string formatting
  operations are O(n) with respect to reply content length.

- **NFR-002**: All new and modified code paths MUST have 100% branch coverage in unit tests,
  consistent with the repository's existing coverage policy. This applies to the modified
  conditional logic in `finalize_post_repair()` and any new HEAD-link-appending helper.

- **NFR-003**: The reply format MUST remain stable across minor version bumps — the HTML marker
  format and human-readable structure constitute a contract that external tools (e.g.,
  notification parsers, dashboard scrapers) may depend upon. Breaking changes to the format
  require a major version bump and changelog entry.

### Key Entities

- **TierResult**: Represents the outcome of a resolution tier evaluation, containing
  `tier_name`, `verdict`, `confidence`, and `explanation` fields. This is the primary data
  source for structured replies. Located in `agentic_devtools/cli/ci/resolution/models.py`.
- **ReplyFormatter**: The service responsible for converting a `TierResult` into a formatted
  reply string. Already exists and is well-tested; the fix involves ensuring it is invoked
  consistently. Located in `agentic_devtools/cli/ci/resolution/reply_formatter.py`. Does NOT
  handle commit link formatting — that responsibility belongs to the caller.
- **ResolutionReply**: A structured object containing `html_marker`, `human_text`, and
  `model_id` — the decomposed parts of a formatted reply. Located in
  `agentic_devtools/cli/ci/resolution/models.py`.
- **GitHubPlatformProvider**: The provider class containing `finalize_post_repair()` where the
  regression exists. Has access to `self._repo` (owner/repo string, resolved via
  `self._resolve_repo()` which falls back to `GITHUB_REPOSITORY`) and the `head_sha` parameter
  (the current HEAD commit SHA, passed explicitly into `finalize_post_repair()`). Located in
  `agentic_devtools/cli/ci/github_provider.py`.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of resolution replies posted by `finalize_post_repair()` where a
  `TierResult` is available MUST use the structured format (containing HTML marker, verdict
  emoji, tier name, rationale, and confidence indicator) — verified by unit tests asserting
  reply body structure for all code paths.

- **SC-002**: At least 95% of resolution replies include a HEAD commit link — the remaining 5%
  accounts for edge cases where commit SHA is unavailable. Verified by integration test
  assertions and log-based monitoring of the `**HEAD**:` line presence.

- **SC-003**: Zero instances of the bare "Addressed on the updated PR branch." string appearing
  as the sole reply body when a `TierResult` is non-null — verified by a dedicated regression
  test that asserts this combination is impossible.

- **SC-004**: Existing tests for `format_unconfirmed_commit_change_reply()`,
  `format_abandoned_reply()`, and `build_full_reply()` continue to pass without modification —
  verified by the full test suite passing after the change.

- **SC-005**: New unit tests achieve 100% branch coverage of the modified `finalize_post_repair()`
  resolution reply logic, covering: (a) tier_result available with normal resolution,
  (b) tier_result available with fallback tier, (c) tier_result is None,
  (d) HEAD commit SHA available, (e) HEAD commit SHA unavailable.

---
*Generated by Copilot SDK (claude-opus-4.6)*
