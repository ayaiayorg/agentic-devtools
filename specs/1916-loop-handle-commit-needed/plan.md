# Implementation Plan: AI PR Loop — No-Commit-Needed Detection

## Technical Context

**Stack**: Python 3.10+, GitHub Actions CI (Python 3.12), GitHub REST/GraphQL APIs via `gh` CLI  
**Package**: `agentic-devtools` (pip-installable CLI toolkit for AI agents)  
**Key Dependencies**: Existing tiered resolution engine, post-agent evaluator, orchestrator state machine  
**Branch**: `1916-ai-pr-loop-no-commit-needed`  
**Issue**: [#1916](https://github.com/ayaiayorg/agentic-devtools/issues/1916)

### Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Marker detection location | Post-agent evaluator (`classify_post_agent_state`) | Runs in the existing `workflow_dispatch` polling cycle after agent completion; natural extension point |
| Thread resolution path | New `ThreadEvaluatedTier` in resolution engine | Follows existing tier pattern; short-circuits SDK verification for marked threads |
| Git instruction delivery | Prompt file edit only | No runtime code changes needed; cloud agent environment limitation |
| Copilot reviewer instructions | New `.github/instructions/code-review.instructions.md` with `applyTo:` header | GitHub's path-scoped custom review instructions mechanism |

## Research Summary

See [research.md](research.md) for detailed analysis of:

- Post-agent evaluator integration point vs. orchestrator-level detection
- New tier vs. extending `AutomationMarkerTier`
- `finalize_post_repair()` bypass strategy

## Design Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                    Copilot Cloud Agent                            │
│  1. Evaluates review comments                                    │
│  2. Posts <!-- ai-pr-loop:thread-evaluated --> per thread         │
│  3. Posts <!-- ai-pr-loop:repair-satisfied --> summary            │
│     (only when ALL threads need no changes)                      │
└──────────────────────────────┬──────────────────────────────────┘
                               │ next polling cycle (workflow_dispatch run)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              Post-Agent Evaluator (classifier.py)                 │
│  New classification: repair_satisfied_no_changes                  │
│  Detection: scan Copilot comments since dispatch timestamp for marker │
│  Validation: review-id must match active dispatch                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│         Direct Thread Resolution (bypasses finalize_post_repair)  │
│  1. List review comments for the review_id                       │
│  2. For each unresolved thread, check for thread-evaluated reply  │
│     from COPILOT_COMMENT_LOGINS identity                         │
│  3. Resolve marked threads via ThreadEvaluatedTier (HIGH conf.)  │
│  4. Warn about unmarked threads                                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              Outcome Logging                                      │
│  reason: "agent_no_changes_needed"                               │
│  Structured JSON: pr_number, review_id, threads_evaluated, etc.  │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Thread Evaluation Marker Tier (FR-002, FR-010, US4)

**Deliverables**: New `ThreadEvaluatedTier` class in the resolution engine

**Files**:

- `agentic_devtools/cli/ci/resolution/tiers/thread_evaluated.py` (new)
- `agentic_devtools/cli/ci/resolution/tiers/__init__.py` (export)
- `tests/unit/cli/ci/resolution/tiers/thread_evaluated/__init__.py` (new)
- `tests/unit/cli/ci/resolution/tiers/thread_evaluated/test_threadevaluatedtier.py` (new)

**Implementation**:

1. Create `ThreadEvaluatedTier` following `AutomationMarkerTier` pattern
2. Scan thread comments for `<!-- ai-pr-loop:thread-evaluated -->` marker
3. Validate author is in `COPILOT_COMMENT_LOGINS` (FR-010)
4. Return `TierResult(verdict=RESOLVE, confidence="high", tier_name="thread_evaluated")`
5. Return `None` if marker absent or author unauthorized

**Tier Position**: Insert `ThreadEvaluatedTier()` in the default tier list immediately after `SweAgentReplyTier()` and before `DiffHeuristicTier()`.

---

### Phase 2: Repair-Satisfied Detection in Post-Agent Evaluator (FR-001, FR-005, FR-011, US1)

**Deliverables**: New classification path and action handler for the no-changes-needed scenario

**Files**:

- `agentic_devtools/cli/ci/evaluator/models.py` (extend `PostAgentClassification`, `PostAgentAction`)
- `agentic_devtools/cli/ci/evaluator/classifier.py` (add detection logic)
- `agentic_devtools/cli/ci/evaluator/snapshot.py` (capture marker data in snapshot)
- `agentic_devtools/cli/ci/evaluator/actions.py` (new action handler)
- `agentic_devtools/cli/ci/guards.py` (add marker constants)
- Tests for each modified module

**Implementation**:

1. Add marker constants to `guards.py`:
   - `REPAIR_SATISFIED_MARKER = "<!-- ai-pr-loop:repair-satisfied -->"`
   - `THREAD_EVALUATED_MARKER = "<!-- ai-pr-loop:thread-evaluated -->"`
   - `REVIEW_ID_MARKER_RE = re.compile(r"<!-- review-id:(\d+) -->")`
2. Extend `PostAgentSnapshot` with `has_repair_satisfied_marker: bool` and `repair_satisfied_review_id: int | None`
3. Update `build_snapshot()` to scan Copilot-authored issue comments posted since the current dispatch timestamp, detect `repair-satisfied`, and extract `review-id`
4. Add `PostAgentClassification.repair_satisfied_no_changes` enum value
5. Add classification rule in `classify_post_agent_state()`:
   - Priority between "complete" and "threads_resolved_no_sentinel"
   - Condition: `snapshot.has_repair_satisfied_marker and not snapshot.head_changed_since_review`
6. Add `PostAgentAction.resolve_evaluated_threads` enum value
7. Implement action handler `resolve_evaluated_threads()` that:
   - Validates `repair_satisfied_review_id` matches the tracked review (FR-011)
   - Fetches review comment threads
   - Identifies threads with `thread-evaluated` replies from authorized identities
   - Resolves those threads via the resolution engine with `ThreadEvaluatedTier`
   - Logs warnings for threads without markers
   - Returns structured `EvaluationResult`

---

### Phase 3: Direct Thread Resolution Path (FR-012, US1-AC1)

**Deliverables**: Resolution logic that bypasses `finalize_post_repair()` commit guard

**Files**:

- `agentic_devtools/cli/ci/evaluator/actions.py` (the `resolve_evaluated_threads` function)
- `agentic_devtools/cli/ci/github_provider.py` (helper to list thread replies with author info)

**Implementation**:

1. The action handler from Phase 2 performs resolution directly:
   - Call `provider.list_review_comments(pr_number, review_id)` to get threads
   - For each unresolved thread, fetch replies and check for `thread-evaluated` marker
   - Use existing `provider.resolve_thread()` for actual resolution (idempotent — NFR-002)
   - Do NOT call `finalize_post_repair()` (bypasses commit guard per spec)
2. Add helper method on provider: `list_thread_replies(pr_number, comment_id) -> list[CommentInfo]`
3. Log outcome with `reason="agent_no_changes_needed"` (FR-005)

---

### Phase 4: Mixed Scenario — Thread-Evaluated in finalize_post_repair (US1-AC2)

**Deliverables**: `ThreadEvaluatedTier` automatically handles the mixed scenario

**Files**: No additional code needed beyond Phase 1

**Rationale**: The `ThreadEvaluatedTier` is already in the tiered resolution engine. When `finalize_post_repair()` runs after a commit (normal flow), it evaluates all unresolved threads through the
engine. Threads with `thread-evaluated` markers will be caught by the new tier and resolved with HIGH confidence, without needing SDK verification. This naturally handles US1-AC2.

---

### Phase 5: Agent Prompt Updates — Git Instructions (FR-006, FR-007, FR-008, US2)

**Deliverables**: Updated `.github/prompts/agdt.address-copilot-review.evaluate-and-respond.prompt.md`

**Changes**:

1. **Tooling Priority table** (line 65): Replace `agdt-git-save-work` row with raw git commands
2. **CI Repair Note** (lines 67–71): Remove "Do not fall back to raw `git commit`/`git push`" prohibition
3. **Phase 6 Commit & Push** (lines 314–326): Replace `agdt-set commit_message` + `agdt-git-save-work` with:

   ```bash
   git commit --amend --no-edit
   git push
   ```

4. Add fallback instructions for non-fast-forward rejection aligned with FR-007:

   ```bash
   # If push rejected (non-fast-forward), recover without force-push.
   # This intentionally creates a second commit on the PR branch.
   branch="$(git rev-parse --abbrev-ref HEAD)"
   amended_sha="$(git rev-parse HEAD)"
   git fetch origin
   git reset --hard "origin/${branch}"
   git cherry-pick "${amended_sha}"
   git commit --amend -m "fix([#1916](https://github.com/ayaiayorg/agentic-devtools/issues/1916)): address review feedback" -m "[ai-repair]" -m "[#1916](https://github.com/ayaiayorg/agentic-devtools/issues/1916)"
   git push
   ```

5. Add explicit policy exception note authorizing raw git for cloud agent environment and explicitly documenting that FR-007 intentionally permits this fallback commit path when
   `agdt-git-save-work` is unavailable, including the intentional temporary exception to
   the single-commit policy in `.github/copilot-instructions.md` because the
   non-fast-forward recovery adds one additional commit

---

### Phase 6: Agent Prompt Updates — No-Change-Needed Markers (FR-003, FR-004, US1)

**Deliverables**: New prompt section instructing the agent to post structured markers

**Changes to evaluate-and-respond prompt**:

1. Add new section after Phase 7 (or as Phase 6b alternative path):
   "**If ALL comments are ❌ Declined and there are no CI failures:**"
2. Instruct per-thread reply with `<!-- ai-pr-loop:thread-evaluated -->` marker + explanation
3. Instruct summary comment with:
   - `<!-- ai-pr-loop:repair-satisfied -->`
   - `<!-- review-id:{review_id} -->`
4. Explicit prohibition: "Do NOT post `repair-satisfied` in mixed scenarios"

---

### Phase 7: Copilot Reviewer Custom Instructions (FR-009, US3)

**Deliverables**: New `.github/instructions/code-review.instructions.md` (with `applyTo:` header).  
This intentionally satisfies FR-009/NFR-004 as a supported path-scoped replacement for the spec’s `.github/copilot-review-instructions.md` filename.

**Content** (must be under 1KB per NFR-004):

```markdown
---
applyTo: "**"
---

# Custom Review Instructions

MUST NOT comment on:
- CI check failures (linting, formatting, type errors, test failures)
- Potential markdownlint violations (MD013, line length, etc.)
- Code formatting issues enforced by automated tools (ruff, black, prettier)
- Import ordering (enforced by ruff/isort)

All CI-enforced checks are verified GREEN before review is requested.
Comments about these areas waste compute cycles on false positives.

Focus exclusively on:
- Logic correctness and potential bugs
- Security vulnerabilities
- Architecture and design issues
- Code clarity and maintainability
- Missing edge case handling
- API contract violations
- Race conditions and concurrency issues
```

---

### Phase 8: Structured Logging (FR-005, NFR-003)

**Deliverables**: Structured log entries for the new code paths

**Implementation** (integrated into Phase 2/3 action handler):

```python
logger.info(
    "PR #%d: repair_satisfied detected — review_id=%d, "
    "threads_evaluated=%d, threads_resolved=%d, threads_missing=%d, "
    "outcome=agent_no_changes_needed",
    pr_number, review_id, evaluated, resolved, missing,
)
```

Ensure the decision summary includes:

```python
summary["decision"] = "post_agent_evaluator_completed"
summary["reason"] = "agent_no_changes_needed"
summary["post_agent_evaluator"]["threads_evaluated"] = count
```

---

### Phase 9: Integration Tests and Edge Cases

**Deliverables**: Comprehensive test coverage for all new paths

**Test scenarios**:

1. Happy path: all threads marked → all resolved, clean exit
2. Mixed scenario: some marked, agent pushes commit → marked threads resolved via engine
3. Missing markers: `repair-satisfied` present but some threads lack `thread-evaluated` → partial resolution + warning
4. Review-id mismatch: marker present but wrong review-id → ignored
5. Unauthorized author: marker from non-COPILOT_COMMENT_LOGINS user → not treated as signal
6. Idempotency: resolve already-resolved thread → no error (NFR-002)
7. 20+ threads in single resolution pass (SC-007)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `SweAgentReplyTier` already resolves agent-replied threads before `ThreadEvaluatedTier` runs | Medium | Low | Acceptable — both produce HIGH confidence RESOLVE; redundancy is harmless |
| Agent fails to post all per-thread markers (network issue) | Low | Medium | Only resolve threads with markers; warn about missing ones |
| Copilot reviewer ignores custom instructions | Medium | Low | The `repair-satisfied` path gracefully handles false-positive reviews |
| `finalize_post_repair()` commit guard prevents resolution in mixed scenario | None | N/A | Mixed scenario uses normal commit flow; `ThreadEvaluatedTier` handles marked threads within the engine |
| Rate limiting on 20+ thread resolution | Low | Medium | Existing `resolve_thread()` implementation handles GitHub API rate limits |

## Dependencies

### External

- GitHub REST API: `GET /repos/{owner}/{repo}/pulls/{pr}/reviews/{id}/comments`
- GitHub REST API: `GET /repos/{owner}/{repo}/pulls/{pr}/comments/{id}/replies`
- GitHub GraphQL: `resolveReviewThread` mutation (existing)
- `.github/instructions/code-review.instructions.md` — GitHub's path-scoped custom review instructions feature

### Internal

- `COPILOT_COMMENT_LOGINS` frozenset (`agentic_devtools/cli/ci/models.py:128`)
- `TieredResolutionEngine` (`agentic_devtools/cli/ci/resolution/engine.py`)
- `PostAgentSnapshot` / `classify_post_agent_state` (`agentic_devtools/cli/ci/evaluator/`)
- `CIPlatformProvider.resolve_thread()` (`agentic_devtools/cli/ci/github_provider.py`)
- `CIPlatformProvider.list_review_comments()` (`agentic_devtools/cli/ci/github_provider.py:1097`)

---
*Generated by Copilot SDK (claude-opus-4.6)*
