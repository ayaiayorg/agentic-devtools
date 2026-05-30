# Implementation Plan: Robust Multi-Tiered Thread Resolution System

## 1. Technical Context

### Technology Stack

- **Language**: Python 3.10+ with type hints
- **Architecture**: CLI-based pipeline (`agentic_devtools/cli/ci/pipeline/`)
- **AI/SDK**: Copilot CLI (prefers standalone `copilot` binary; falls back to `gh copilot` extension via `agentic_devtools/cli/copilot/`, optional runtime dependency) for thread verification
- **API**: GitHub GraphQL API (via `gh api graphql`) for thread mutations
- **Typing**: Python Protocol classes (structural subtyping, PEP 544)
- **Testing**: pytest with 1:1:1 test structure, 100% coverage per file
- **State**: JSON file-based state management (`agentic_devtools/state.py`)

### Key Dependencies

- Existing `check_lines_modified()` in `evaluator/diff_heuristic.py`
- Existing `resolve_review_threads()` in `cli/github/resolve_review_threads.py`
- Existing `_verify_comments_via_sdk()` in `cli/ci/github_provider.py`
- Existing `ResolveThreadsAction` in `cli/ci/pipeline/actions/resolve_threads.py`
- Pipeline `Action` protocol in `cli/ci/pipeline/base.py`
- `CIPlatformProvider` ABC in `cli/ci/provider.py`

### Architecture Decisions

- New resolution engine lives under `agentic_devtools/cli/ci/resolution/` as a new package
- Platform-agnostic interfaces use `Protocol` classes (not ABC) per NFR-006
- The existing `finalize_post_repair()` is refactored to delegate to the tiered engine
- `ResolveThreadsAction.evaluate()` removes `ci_passing` and `no_pending_review` preconditions
- Per-thread resolution state is serialized into the pipeline state directory

## 2. Research Summary

The clarified spec decisions incorporated into this plan are:

- Tier ordering and short-circuit semantics
- Protocol vs ABC for platform interfaces
- SDK response parsing (structured VERDICT format)
- Tentative thread state persistence strategy
- Fallback agent integration pattern

## 3. Design Overview

### Tiered Resolution Pipeline

```text
┌─────────────────────────────────────────────────────────┐
│  Thread Resolution Engine                                │
│                                                          │
│  Per-thread:                                             │
│    ┌──────────────┐    ┌──────────────┐                 │
│    │ Precondition │───▶│  Tier 1:     │                 │
│    │ (new commit  │    │  isOutdated  │                 │
│    │  since review)│    └──────┬───────┘                 │
│    └──────────────┘           │ None                     │
│                        ┌──────▼───────┐                 │
│                        │  Tier 2:     │                 │
│                        │  Automation  │                 │
│                        │  Markers     │                 │
│                        └──────┬───────┘                 │
│                               │ None                     │
│                        ┌──────▼───────┐                 │
│                        │  Tier 3:     │                 │
│                        │  Diff        │                 │
│                        │  Heuristic   │                 │
│                        └──────┬───────┘                 │
│                               │ None                     │
│                        ┌──────▼───────┐                 │
│                        │  Tier 4:     │                 │
│                        │  SDK + Retry │                 │
│                        │  + Fallback  │                 │
│                        └──────┬───────┘                 │
│                               │                          │
│                        ┌──────▼───────┐                 │
│                        │  Verdict:    │                 │
│                        │  RESOLVE /   │                 │
│                        │  UNRESOLVE / │                 │
│                        │  TENTATIVE   │                 │
│                        └──────────────┘                 │
└─────────────────────────────────────────────────────────┘
```

### Package Structure (New)

```text
agentic_devtools/cli/ci/resolution/
├── __init__.py
├── protocols.py          # ReviewThread, ThreadComment, ResolutionContext, EvaluationTier, ThreadResolver
├── models.py             # Enum + dataclasses: ResolutionVerdict, ResolutionReply, ThreadResolutionState, TierResult
├── engine.py             # TieredResolutionEngine — orchestrates tier evaluation
├── tiers/
│   ├── __init__.py
│   ├── outdated.py       # Tier 1: isOutdated check
│   ├── automation_markers.py  # Tier 2: pattern matching
│   ├── diff_heuristic.py      # Tier 3: wraps existing check_lines_modified
│   └── sdk_evaluation.py      # Tier 4: SDK + retry + fallback
├── reply_formatter.py    # Structured reply builder with HTML markers
├── state_persistence.py  # ThreadResolutionState serialization
└── github_adapter.py     # GitHub-specific: GraphQL queries, mutations, reply posting
```

## 4. Implementation Phases

### Phase 1: Platform-Agnostic Protocols & Models (FR-013, FR-015)

**Deliverables:**

- `resolution/protocols.py` — `ReviewThread`, `EvaluationTier`, `ThreadResolver` Protocols
- `resolution/models.py` — `ResolutionVerdict` enum, `ResolutionReply`, `ThreadResolutionState`, `TierResult` dataclasses

**Key Design:**

```python
class ThreadComment(Protocol):
    body: str
    created_at: str
    author_login: str | None

class ResolutionContext(Protocol):
    diff_text: str
    head_commit_oid: str

class ReviewThread(Protocol):
    thread_id: str
    file_path: str | None
    start_line: int | None
    end_line: int | None
    is_outdated: bool | None  # tri-state
    comments: list[ThreadComment]
    originating_review_commit_oid: str

class EvaluationTier(Protocol):
    @property
    def name(self) -> str: ...
    def evaluate(self, thread: ReviewThread, context: ResolutionContext) -> TierResult | None: ...
```

**Tests:** `tests/unit/cli/ci/resolution/protocols/`, `tests/unit/cli/ci/resolution/models/`

---

### Phase 2: Remove Irrelevant Preconditions (FR-002, FR-003)

**Deliverables:**

- Modify `ResolveThreadsAction.evaluate()` — remove `ci_passing` and `no_pending_review` checks
- Keep only `has_unresolved_threads` and add per-thread `new_commit_since_review` check in execute
- Update `_REVIEW_THREADS_QUERY` in `github_provider.py` to include comment `commit` OID field

**Changes to:**

- `cli/ci/pipeline/actions/resolve_threads.py` — simplify `evaluate()`
- `cli/ci/github_provider.py` — update GraphQL query, pass per-thread commit OID data

**Tests:** Update `tests/unit/cli/ci/pipeline/actions/resolve_threads/test_resolvethreadsaction.py`

---

### Phase 3: Expanded GraphQL Query (FR-004)

**Deliverables:**

- Expand `_REVIEW_THREADS_QUERY` in both `github_provider.py` and `resolve_review_threads.py`
- New fields: `isOutdated`, `path`, `line`, `startLine`, and per-comment `body`, `createdAt`, `author { login }`
- Map expanded data to `ReviewThread` protocol instances

**Changes to:**

- `cli/ci/github_provider.py` — update query + thread parsing
- `cli/github/resolve_review_threads.py` — update query (used by CLI command)
- New `resolution/github_adapter.py` — adapter converting raw GraphQL to `ReviewThread`

**Tests:** `tests/unit/cli/ci/resolution/github_adapter/`

---

### Phase 4: Tier 1 — `isOutdated` Resolution (FR-005)

**Deliverables:**

- `resolution/tiers/outdated.py` — evaluates `thread.is_outdated`
- Returns `TierResult(verdict=RESOLVE, confidence="high")` when `True`
- Returns `None` when `False` or `None` (fall-through)

**Tests:** `tests/unit/cli/ci/resolution/tiers/outdated/`

---

### Phase 5: Tier 2 — Automation Marker Pattern Match (FR-006)

**Deliverables:**

- `resolution/tiers/automation_markers.py` — module-level constant list, case-insensitive substring match on most recent comment body
- Initial patterns: `["autofix applied", "suggestion applied", "fix applied"]`

**Tests:** `tests/unit/cli/ci/resolution/tiers/automation_markers/`

---

### Phase 6: Tier 3 — Diff Heuristic Integration (FR-007)

**Deliverables:**

- `resolution/tiers/diff_heuristic.py` — wraps existing `check_lines_modified()`, handles multi-line range overlap
- Requires `ResolutionContext.diff_text` (the diff between review commit and HEAD)
- Skips PR-level comments (no file/line anchor)

**Tests:** `tests/unit/cli/ci/resolution/tiers/diff_heuristic/`

---

### Phase 7: Tier 4 — SDK Evaluation with Structured Validation & Retry (FR-008, FR-009)

**Deliverables:**

- `resolution/tiers/sdk_evaluation.py` — structured VERDICT+EXPLANATION parsing
- Retry logic: on malformed response, retry once with reformulated prompt
- Fallback: invoke CLI agent via `claude-sonnet-4.6` with dedicated prompt template
  (and add `claude-sonnet-4.6` to `agentic_devtools/cli/setup/commands.py:_KNOWN_COPILOT_MODELS`
  so setup still works when model discovery fails)
- New prompt: `agentic_devtools/prompts/default-thread-resolution-fallback-prompt.md`
  (deliberate prompts-root file; load via direct path read rather than `load_prompt_template()`
  since it is not workflow-scoped)

**Tests:** `tests/unit/cli/ci/resolution/tiers/sdk_evaluation/`

---

### Phase 8: Resolution Engine Orchestration (FR-001, FR-010)

**Deliverables:**

- `resolution/engine.py` — `TieredResolutionEngine` that iterates tiers in order
- Short-circuits on first non-None result
- Handles tentative (FR-010): if all tiers fail → `TENTATIVE` verdict
- Batch processing with per-thread error isolation

**Tests:** `tests/unit/cli/ci/resolution/engine/`

---

### Phase 9: Structured Reply & Audit Trail (FR-011, FR-012)

**Deliverables:**

- `resolution/reply_formatter.py` — builds replies with HTML markers
- Format: `<!-- agdt:resolution-tier:{tier_name} -->` + human-readable explanation
- Includes confidence indicator, tier ID, evidence, model ID (for SDK tier)

**Tests:** `tests/unit/cli/ci/resolution/reply_formatter/`

---

### Phase 10: Tentative Resolution & Re-evaluation (FR-010, FR-014)

**Deliverables:**

- `resolution/state_persistence.py` — serialize/deserialize `ThreadResolutionState` per thread
- TTL logic: 5 iterations OR 24 hours
- On expiry: update reply to "resolution abandoned — manual review required"
- Re-evaluation: tentative threads re-enter the tier pipeline on next iteration

**Tests:** `tests/unit/cli/ci/resolution/state_persistence/`

---

### Phase 11: Integration — Wire Engine into Pipeline

**Deliverables:**

- Refactor `GitHubProvider.finalize_post_repair()` to delegate to `TieredResolutionEngine`
- `ResolveThreadsAction.execute()` passes expanded thread data to engine
- Reply posting and GraphQL mutations go through `github_adapter.py`
- Preserve backward compatibility: `FinalizationResult` contract unchanged

**Changes to:**

- `cli/ci/github_provider.py` — delegate to engine
- `cli/ci/pipeline/actions/resolve_threads.py` — pass expanded context

**Tests:** Integration tests in `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py`

---

### Phase 12: Metrics, Logging & NFR Compliance

**Deliverables:**

- DEBUG-level logging on every tier evaluation (NFR-003)
- Timing instrumentation: 500ms budget for programmatic tiers, 45s total (NFR-001)
- Rate-limit backoff in `github_adapter.py` (NFR-004)
- Metrics: SDK invocation count tracking for SC-002 validation

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `isOutdated` not available on GHES | Medium | Low | Tri-state handling (None = fall-through) |
| SDK response format changes break parsing | Low | High | Strict validation + retry + fallback agent |
| GraphQL rate limiting during batch resolution | Medium | Medium | Exponential backoff, partial progress preservation |
| Tentative state file corruption across iterations | Low | Medium | Atomic writes, validation on load |
| Breaking existing `finalize_post_repair` consumers | Medium | High | Preserve return type contract, feature flag for rollback |
| Fallback agent (`claude-sonnet-4.6`) unavailable | Low | Medium | Graceful degradation → leave thread unresolved |
| Performance regression (programmatic tiers >500ms) | Low | Medium | Early profiling, avoid unnecessary I/O in hot path |

## 6. Dependencies

### External

- GitHub GraphQL API — `isOutdated` field availability (GA on github.com)
- Copilot SDK — for tier 4 verification
- `claude-sonnet-4.6` model — for fallback agent

### Internal

- `check_lines_modified()` — reused in tier 3
- `resolve_review_threads()` — reused for GraphQL mutations
- `_build_verification_context_diff()` — reused for diff fetching
- Pipeline `Action` protocol — unchanged, engine integrates within existing action
- State management (`agentic_devtools/state.py`) — for tentative state persistence

### Sequencing Constraints

- Phase 1 (protocols) must complete before any tier implementation
- Phase 2 (precondition removal) is independently deployable
- Phase 3 (expanded query) is required by phases 4, 5, 6
- Phases 4–7 (individual tiers) can be developed in parallel after phase 3
- Phase 8 (engine) requires all tiers
- Phase 11 (integration) requires phases 8, 9, 10

---
*Generated by Copilot SDK (claude-opus-4.6)*
