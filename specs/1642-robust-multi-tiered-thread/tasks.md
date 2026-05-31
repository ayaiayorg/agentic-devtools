# Tasks: Robust Multi-Tiered Thread Resolution System

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Package scaffolding (no direct plan equivalent) |
| Phase 2: Foundational | Phase 1 | Platform-agnostic protocols & models |
| Phase 3: User Story 2 | Phase 2 | Removal of irrelevant preconditions |
| Phase 4: User Story 1 & Shared | Phase 3 | Expanded GraphQL query + GitHub adapter |
| Phase 5: User Story 1 — Tier 1 | Phase 4 | isOutdated resolution tier |
| Phase 6: User Story 3 — Tier 2 | Phase 5 | Automation marker pattern match tier |
| Phase 7: User Story 4 — Tier 3 | Phase 6 | Diff heuristic integration tier |
| Phase 8: User Story 5 — Tier 4 | Phase 7 | SDK evaluation with retry & fallback |
| Phase 9: User Story 6 | Phase 9 | Structured reply & audit trail |
| Phase 10: User Story 7 | Phase 10 | Tentative resolution state & re-evaluation |
| Phase 11: Engine Orchestration | Phase 8 | TieredResolutionEngine (reordered from plan) |
| Phase 12: User Story 8 | — | Platform-agnostic validation (no direct plan equivalent) |
| Phase 13: Integration | Phase 11 | Wire engine into pipeline |
| Final Phase: Polish | Phase 12 | Cross-cutting: logging, metrics, NFR compliance |

---

## Phase 1: Setup — Package Scaffolding

- [x] T001 Create package directory `agentic_devtools/cli/ci/resolution/` with `__init__.py`
- [x] T002 Create package directory `agentic_devtools/cli/ci/resolution/tiers/` with `__init__.py`
- [x] T003 Create test directories under `tests/unit/cli/ci/resolution/` with `__init__.py` files for `protocols/`, `models/`, `engine/`, `reply_formatter/`, `state_persistence/`, `github_adapter/`,
  and `tiers/outdated/`, `tiers/automation_markers/`, `tiers/diff_heuristic/`, `tiers/sdk_evaluation/`
- [x] T004 Create fallback prompt template file at `agentic_devtools/prompts/default-thread-resolution-fallback-prompt.md` with binary RESOLVE/UNRESOLVE decision prompt structure

## Phase 2: Foundational — Platform-Agnostic Protocols & Models

- [x] T005 Write tests for `ReviewThread`, `ThreadComment`, `ResolutionContext`, `EvaluationTier` Protocol classes in `tests/unit/cli/ci/resolution/protocols/`
- [x] T006 Implement Protocol classes in `agentic_devtools/cli/ci/resolution/protocols.py` — `ThreadComment`, `ResolutionContext`, `ReviewThread`, `EvaluationTier`, `ThreadResolver` using
  `typing.Protocol`
- [x] T007 Write tests for `ResolutionVerdict` enum, `TierResult`, `ResolutionReply`, `ThreadResolutionState` dataclasses in `tests/unit/cli/ci/resolution/models/`
- [x] T008 [P] Implement `agentic_devtools/cli/ci/resolution/models.py` — `ResolutionVerdict` enum (RESOLVE, UNRESOLVE, TENTATIVE), `TierResult` dataclass (verdict, confidence, tier_name,
  explanation), `ResolutionReply` dataclass (HTML markers, human text), `ThreadResolutionState` dataclass (thread_id, verdict, tier, confidence, timestamp, iteration_count, expiry)

## Phase 3: User Story 2 — Removal of Irrelevant Preconditions (P1)

- [x] T009 [US2] Write tests for updated `ResolveThreadsAction.evaluate()` that verifies CI and pending review checks are removed, only `has_unresolved_threads` remains in
  `tests/unit/cli/ci/pipeline/actions/resolve_threads/`
- [x] T010 [US2] Modify `ResolveThreadsAction.evaluate()` in `agentic_devtools/cli/ci/pipeline/actions/resolve_threads.py` — remove `ci_passing` and `no_pending_review` precondition checks; retain
  only `has_unresolved_threads`
- [ ] T011 [US2] Write tests for per-thread `new_commit_since_review` precondition logic (compare thread originating review `commit_id` against current HEAD OID)
- [ ] T012 [US2] Implement per-thread `new_commit_since_review` check in `ResolveThreadsAction.execute()` — skip threads where HEAD OID equals the originating review commit OID

## Phase 4: User Story 1 & Shared — Expanded GraphQL Query + GitHub Adapter (P1)

- [x] T013 [US1] Write tests for expanded `_REVIEW_THREADS_QUERY` parsing that includes `isOutdated`, `path`, `line`, `startLine`, comment `body`, `createdAt`, `author { login }`, and comment `commit
  { oid }` fields
- [x] T014 [US1] Expand `_REVIEW_THREADS_QUERY` in `agentic_devtools/cli/ci/github_provider.py` to fetch all new fields: `isOutdated`, `path`, `line`, `startLine`, and per-comment `body`, `createdAt`,
  `author { login }`, `commit { oid }`, `databaseId` in a single unified edit (resolves F-01)
- [x] T015 [US1] Write tests for `GitHubThreadAdapter` that converts raw GraphQL response nodes into `ReviewThread` protocol instances in `tests/unit/cli/ci/resolution/github_adapter/`
- [x] T016 [US1] Implement `agentic_devtools/cli/ci/resolution/github_adapter.py` — `GitHubThreadAdapter` class mapping GraphQL thread/comment data to `ReviewThread` protocol, handling `isOutdated:
  null` as `None`

## Phase 5: User Story 1 — Tier 1: isOutdated Resolution (P1)

- [x] T017 [US1] Write tests for `OutdatedTier.evaluate()` in `tests/unit/cli/ci/resolution/tiers/outdated/` — returns `TierResult(RESOLVE, confidence="high")` when `is_outdated=True`, returns `None`
  when `False` or `None`
- [x] T018 [US1] Implement `agentic_devtools/cli/ci/resolution/tiers/outdated.py` — `OutdatedTier` class implementing `EvaluationTier` Protocol

## Phase 6: User Story 3 — Tier 2: Automation Marker Pattern Match (P2)

- [x] T019 [P] [US3] Write tests for `AutomationMarkerTier.evaluate()` in `tests/unit/cli/ci/resolution/tiers/automation_markers/` — case-insensitive substring match on most recent comment body,
  returns `None` on no match
- [x] T020 [P] [US3] Implement `agentic_devtools/cli/ci/resolution/tiers/automation_markers.py` — module-level constant `AUTOMATION_MARKERS = ["autofix applied", "suggestion applied", "fix applied"]`,
  `AutomationMarkerTier` class

## Phase 7: User Story 4 — Tier 3: Diff Heuristic Integration (P2)

- [x] T021 [P] [US4] Write tests for `DiffHeuristicTier.evaluate()` in `tests/unit/cli/ci/resolution/tiers/diff_heuristic/` — wraps `check_lines_modified()`, handles multi-line range overlap, skips
  PR-level comments (no file/line anchor)
- [x] T022 [P] [US4] Implement `agentic_devtools/cli/ci/resolution/tiers/diff_heuristic.py` — `DiffHeuristicTier` class delegating to existing `check_lines_modified()` from
  `evaluator/diff_heuristic.py`

## Phase 8: User Story 5 — Tier 4: SDK Evaluation with Validation, Retry & Fallback (P2)

- [x] T023 [US5] Write tests for structured VERDICT+EXPLANATION response parsing in `tests/unit/cli/ci/resolution/tiers/sdk_evaluation/` — valid format, malformed response detection, mapping
  `COMMENT_RESOLVE`→`RESOLVE`, `COMMENT_UNRESOLVE`→`UNRESOLVE`, `AMBIGUOUS`→retry path
- [x] T024 [US5] Write tests for retry-on-malformed logic — reformulated prompt on first failure, fallback agent invocation on second failure
- [x] T025 [US5] Implement `agentic_devtools/cli/ci/resolution/tiers/sdk_evaluation.py` — `SdkEvaluationTier` class with structured parsing, single retry with reformulated prompt, and CLI fallback
  agent (`claude-sonnet-4.6`) invocation
- [x] T026 [US5] Add `claude-sonnet-4.6` to `_KNOWN_COPILOT_MODELS` in `agentic_devtools/cli/setup/commands.py` if not already present

## Phase 9: User Story 6 — Structured Reply & Audit Trail (P2)

- [x] T027 [P] [US6] Write tests for `ReplyFormatter` in `tests/unit/cli/ci/resolution/reply_formatter/` — generates structured replies with HTML markers (`<!-- agdt:resolution-tier:{tier} -->`),
  confidence indicator, evidence, model ID for SDK tier
- [x] T028 [P] [US6] Implement `agentic_devtools/cli/ci/resolution/reply_formatter.py` — `ReplyFormatter` class producing human-readable replies with embedded HTML metadata markers per FR-011/FR-012

## Phase 10: User Story 7 — Tentative Resolution State & Re-evaluation (P3)

- [x] T029 [US7] Write tests for `ThreadResolutionState` serialization/deserialization in `tests/unit/cli/ci/resolution/state_persistence/` — JSON round-trip, TTL calculation (5 iterations OR 24h),
  expiry detection
- [x] T030 [US7] Implement `agentic_devtools/cli/ci/resolution/state_persistence.py` — `save_resolution_state()`, `load_resolution_state()`, `is_tentative_expired()`, `increment_iteration()`,
  `mark_abandoned()`
- [ ] T031 [US7] Write tests for tentative re-evaluation flow — thread re-enters tier pipeline, upgrades on new evidence, abandons after TTL expiry with updated reply
- [ ] T032 [US7] Implement tentative re-evaluation logic in `state_persistence.py` — expiry reply update to "resolution abandoned — manual review required", exclusion from further evaluation

## Phase 11: Engine Orchestration (FR-001, FR-010)

- [x] T033 [US1] Write tests for `TieredResolutionEngine` in `tests/unit/cli/ci/resolution/engine/` — tier ordering, short-circuit on first non-None result, TENTATIVE when all tiers fail, per-thread
  error isolation, batch processing
- [x] T034 [US1] Implement `agentic_devtools/cli/ci/resolution/engine.py` — `TieredResolutionEngine` class orchestrating tiers 1–4 in strict order, returning final `ResolutionVerdict`

## Phase 12: User Story 8 — Platform-Agnostic Validation (P3)

- [x] T035 [P] [US8] Write tests with a mock `MockProvider` (non-GitHub) that drives the full resolution pipeline through `TieredResolutionEngine`, confirming no GitHub-specific type leakage in
  `tests/unit/cli/ci/resolution/engine/`
- [x] T036 [P] [US8] Verify and document that `protocols.py` types are fully platform-agnostic — add a mock `AzureDevOpsProvider` test fixture confirming identical evaluation behavior

## Phase 13: Integration — Wire Engine into Pipeline

- [ ] T037 Write tests for refactored `GitHubProvider.finalize_post_repair()` delegation to `TieredResolutionEngine` in existing test files
- [ ] T038 Refactor `GitHubProvider.finalize_post_repair()` in `agentic_devtools/cli/ci/github_provider.py` to delegate thread resolution to `TieredResolutionEngine`, preserving `FinalizationResult`
  contract
- [ ] T039 Update `ResolveThreadsAction.execute()` in `agentic_devtools/cli/ci/pipeline/actions/resolve_threads.py` to pass expanded thread data and `ResolutionContext` to the engine
- [ ] T040 Implement reply posting and GraphQL `resolveReviewThread` mutations in `github_adapter.py` — post structured reply then resolve via mutation, handle already-resolved threads gracefully

## Final Phase: Polish & Cross-Cutting

- [x] T041 Add DEBUG-level logging to every tier evaluation in all tier modules (NFR-003) — thread ID, comment snippet (100 chars), tier name, verdict
- [x] T042 Add timing instrumentation to `engine.py` — 500ms budget warning for programmatic tiers, 45s total timeout per thread (NFR-001)
- [ ] T043 Implement exponential backoff in `github_adapter.py` for GraphQL rate limiting — initial 1s, max 60s, max 5 retries, preserve partial progress (NFR-004)
- [x] T044 Update `agentic_devtools/cli/ci/resolution/__init__.py` to export public API: `TieredResolutionEngine`, `ReviewThread`, `ResolutionVerdict`, `EvaluationTier`, `GitHubThreadAdapter`
- [ ] T045 Run full test suite (`agdt-test`) and validate 100% coverage for all new files under `agentic_devtools/cli/ci/resolution/`
- [ ] T046 Run `python scripts/validate_test_structure.py` to confirm 1:1:1 test structure compliance

## Dependency Graph

```text
T001–T004 → T005–T008 (setup before foundational)
T006, T008 → T009–T012 (protocols/models before precondition work)
T006, T008 → T013–T016 (protocols/models before GraphQL/adapter)
T014, T016 → T017–T018 (expanded query before tier 1)
T016 → T019–T022 (adapter before tiers 2–3, parallelizable)
T016, T018 → T023–T026 (adapter + tier 1 patterns before tier 4)
T008 → T027–T028 (models before reply formatter, parallelizable)
T008, T028 → T029–T032 (models + formatter before state persistence)
T018, T020, T022, T025, T028, T030 → T033–T034 (all tiers + formatter + state before engine)
T034 → T035–T036 (engine before platform-agnostic validation)
T034, T010, T012, T040 → T037–T040 (engine + preconditions before integration)
T040 → T041–T046 (integration before polish)
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
