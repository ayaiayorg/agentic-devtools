# Tasks: Robust Multi-Tiered Thread Resolution System

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Package scaffolding — no direct plan equivalent |
| Phase 2: Foundational | Phase 1: Platform-Agnostic Protocols & Models | Core Protocol classes and data models |
| Phase 3: User Story 1 | Phase 3: Expanded GraphQL Query; Phase 4: Tier 1 — isOutdated Resolution | GraphQL expansion and isOutdated tier |
| Phase 4: User Story 2 | Phase 2: Remove Irrelevant Preconditions; Phase 3: Expanded GraphQL Query | Precondition removal and GraphQL query expansion |
| Phase 5: User Story 3 | Phase 5: Tier 2 — Automation Marker Pattern Match | Automation-marker pattern-based resolution |
| Phase 6: User Story 4 | Phase 6: Tier 3 — Diff Heuristic Integration | Diff heuristic tier |
| Phase 7: User Story 5 | Phase 7: Tier 4 — SDK Evaluation with Structured Validation & Retry | SDK evaluation with retry and fallback |
| Phase 8: User Story 6 | Phase 9: Structured Reply & Audit Trail | Structured reply formatting and audit trail |
| Phase 9: User Story 7 | Phase 10: Tentative Resolution & Re-evaluation | Tentative resolution state and re-evaluation |
| Phase 10: User Story 8 | Phase 8: Resolution Engine Orchestration | Platform-agnostic engine interface and orchestration |
| Phase 11: Integration & Wiring | Phase 11: Integration — Wire Engine into Pipeline | Pipeline wiring and integration |
| Final Phase: Polish & Cross-Cutting | Phase 12: Metrics, Logging & NFR Compliance | Logging, metrics, and NFR polish |

---

## Phase 1: Setup — Package Scaffolding

- [ ] T001 Create package directory structure for `agentic_devtools/cli/ci/resolution/` with `__init__.py`
- [ ] T002 Create `agentic_devtools/cli/ci/resolution/tiers/__init__.py` package
- [ ] T003 Create test directory structure `tests/unit/cli/ci/resolution/` with all `__init__.py` files for protocols, models, engine, tiers, reply_formatter, state_persistence, github_adapter

## Phase 2: Foundational — Platform-Agnostic Interfaces & Models

- [ ] T004 Write tests for `ReviewThread`, `ThreadComment`, `ResolutionContext`, `EvaluationTier`, `ThreadResolver` Protocol classes in `tests/unit/cli/ci/resolution/protocols/` (FR-013)
- [ ] T005 Implement Protocol classes in `agentic_devtools/cli/ci/resolution/protocols.py` — `ReviewThread`, `ThreadComment`, `ResolutionContext`, `EvaluationTier`, `ThreadResolver` using structural
  subtyping (FR-013, NFR-006)
- [ ] T006 Write tests for `ResolutionVerdict` enum, `TierResult`, `ResolutionReply`, `ThreadResolutionState` dataclasses in `tests/unit/cli/ci/resolution/models/`
- [ ] T007 Implement dataclasses and enums in `agentic_devtools/cli/ci/resolution/models.py` — `ResolutionVerdict` (RESOLVE/UNRESOLVE/TENTATIVE), `TierResult`, `ResolutionReply`,
  `ThreadResolutionState` with confidence levels (FR-015)

## Phase 3: User Story 1 — Programmatic Resolution of Outdated Threads (P1)

- [ ] T008 [US1] Write tests for `isOutdated` tier evaluation in `tests/unit/cli/ci/resolution/tiers/outdated/test_evaluate.py` — true resolves, false/None falls through (FR-005)
- [ ] T009 [US1] Implement Tier 1 `OutdatedTier` in `agentic_devtools/cli/ci/resolution/tiers/outdated.py` — returns RESOLVE with high confidence when `is_outdated=True`, None otherwise (FR-005)
- [ ] T010 [US1] Write tests for expanded GraphQL query parsing that maps `isOutdated` field to `ReviewThread.is_outdated` tri-state in
  `tests/unit/cli/ci/resolution/github_adapter/test_parse_threads.py` (FR-004)
- [ ] T011 [US1] Implement `github_adapter.py` — parse expanded GraphQL response into `ReviewThread` instances, handling `isOutdated`, `path`, `line`, `startLine`, comment `body`, `createdAt`, `author
  { login }` (FR-004)
- [ ] T012 [P] [US1] Write tests for structured reply formatting for outdated tier in `tests/unit/cli/ci/resolution/reply_formatter/test_format_outdated_reply.py` — verify HTML marker `<!-- 
  agdt:resolution-tier:programmatic:outdated -->` (FR-011, FR-012)
- [ ] T013 [P] [US1] Implement reply formatting for outdated tier in `agentic_devtools/cli/ci/resolution/reply_formatter.py` — human-readable text + HTML metadata markers (FR-011, FR-012, NFR-005)

## Phase 4: User Story 2 — Removal of Irrelevant Preconditions (P1)

- [ ] T014 [US2] Write tests verifying `ResolveThreadsAction.evaluate()` no longer requires `ci_passing` in `tests/unit/cli/ci/pipeline/actions/resolve_threads/test_evaluate_no_ci_gate.py` (FR-002)
- [ ] T015 [US2] Write tests verifying `ResolveThreadsAction.evaluate()` no longer requires `no_pending_review` in `tests/unit/cli/ci/pipeline/actions/resolve_threads/test_evaluate_no_review_gate.py`
  (FR-002, FR-003)
- [ ] T016 [US2] Modify `ResolveThreadsAction.evaluate()` in `agentic_devtools/cli/ci/pipeline/actions/resolve_threads.py` — remove `ci_passing` and `no_pending_review` precondition checks (FR-002,
  FR-003)
- [ ] T017 [US2] Write tests for per-thread `new_commit_since_review` precondition using commit OIDs in `tests/unit/cli/ci/pipeline/actions/resolve_threads/test_per_thread_precondition.py` (FR-003)
- [ ] T018 [US2] Implement per-thread precondition check — compare current HEAD OID against thread's originating review `commit_id`; skip thread if OIDs match (FR-003)
- [ ] T019 [US2] Expand `_REVIEW_THREADS_QUERY` in `agentic_devtools/cli/ci/github_provider.py` to fetch comment `commit` OID field for per-thread comparison (FR-003, FR-004)
- [ ] T020 [US2] Expand `_REVIEW_THREADS_QUERY` to include `isOutdated`, `path`, `line`, `startLine`, comment `body`, `createdAt`, `author { login }` (FR-004)

## Phase 5: User Story 3 — Pattern-Based Resolution for Automation Markers (P2)

- [ ] T021 [P] [US3] Write tests for automation marker tier in `tests/unit/cli/ci/resolution/tiers/automation_markers/test_evaluate.py` — matching/non-matching patterns, case-insensitivity (FR-006)
- [ ] T022 [P] [US3] Implement Tier 2 `AutomationMarkerTier` in `agentic_devtools/cli/ci/resolution/tiers/automation_markers.py` — module-level constant `AUTOMATION_MARKERS = ["autofix applied",
  "suggestion applied", "fix applied"]`, case-insensitive substring match on most recent comment body (FR-006)
- [ ] T023 [P] [US3] Write tests for reply formatting for automation marker tier in `tests/unit/cli/ci/resolution/reply_formatter/test_format_marker_reply.py` (FR-011, FR-012)
- [ ] T024 [P] [US3] Implement reply formatting for marker tier — cite matched pattern in structured reply with HTML marker `<!-- agdt:resolution-tier:programmatic:automation-marker -->` (FR-011,
  FR-012)

## Phase 6: User Story 4 — Diff Heuristic Integration (P2)

- [ ] T025 [P] [US4] Write tests for diff heuristic tier in `tests/unit/cli/ci/resolution/tiers/diff_heuristic/test_evaluate.py` — line modified resolves, no modification falls through, PR-level
  comment skipped, multi-line overlap (FR-007)
- [ ] T026 [P] [US4] Implement Tier 3 `DiffHeuristicTier` in `agentic_devtools/cli/ci/resolution/tiers/diff_heuristic.py` — wrap existing `check_lines_modified()`, handle `startLine`-to-`line` range
  overlap, skip threads without file/line anchor (FR-007)
- [ ] T027 [P] [US4] Write tests for reply formatting for diff heuristic tier in `tests/unit/cli/ci/resolution/reply_formatter/test_format_diff_reply.py` (FR-011)
- [ ] T028 [P] [US4] Implement reply formatting for diff tier — cite file path and modified line range with HTML marker `<!-- agdt:resolution-tier:programmatic:diff-heuristic -->` (FR-011, FR-012)

## Phase 7: User Story 5 — SDK Evaluation with Retry & Fallback (P2)

- [ ] T029 [US5] Write tests for structured VERDICT+EXPLANATION parsing in `tests/unit/cli/ci/resolution/tiers/sdk_evaluation/test_parse_response.py` — valid, malformed, AMBIGUOUS mapping (FR-008)
- [ ] T030 [US5] Write tests for retry on malformed response in `tests/unit/cli/ci/resolution/tiers/sdk_evaluation/test_retry.py` (FR-009)
- [ ] T031 [US5] Write tests for CLI fallback agent invocation in `tests/unit/cli/ci/resolution/tiers/sdk_evaluation/test_fallback.py` (FR-009)
- [ ] T032 [US5] Implement Tier 4 `SdkEvaluationTier` in `agentic_devtools/cli/ci/resolution/tiers/sdk_evaluation.py` — structured parsing of VERDICT (COMMENT_RESOLVE→RESOLVE,
  COMMENT_UNRESOLVE→UNRESOLVE, AMBIGUOUS→retry), retry once with reformulated prompt (FR-008, FR-009)
- [ ] T033 [US5] Implement fallback agent invocation logic — invoke `claude-sonnet-4.6` with dedicated prompt template when retries exhausted (FR-009)
- [ ] T034 [US5] Create prompt template `agentic_devtools/prompts/default-thread-resolution-fallback-prompt.md` — optimized for binary RESOLVE/UNRESOLVE decision given comment body, diff context, file
  path (FR-009)
- [ ] T035 [P] [US5] Write tests for reply formatting for SDK tier in `tests/unit/cli/ci/resolution/reply_formatter/test_format_sdk_reply.py` — includes model identifier (FR-011, FR-012)
- [ ] T036 [P] [US5] Implement reply formatting for SDK tier — include model ID, explanation text, HTML marker `<!-- agdt:resolution-tier:sdk:copilot -->` (FR-011, FR-012)

## Phase 8: User Story 6 — Structured Reply & Audit Trail (P2)

- [ ] T037 [US6] Write tests for confidence indicator inclusion in all reply formats in `tests/unit/cli/ci/resolution/reply_formatter/test_confidence_indicator.py` (FR-011)
- [ ] T038 [US6] Write tests for HTML marker programmatic parsability in `tests/unit/cli/ci/resolution/reply_formatter/test_html_markers.py` (FR-012)
- [ ] T039 [US6] Ensure `reply_formatter.py` includes confidence (high/medium/low), tier identification, and evidence in every reply format — consolidate all tier reply builders (FR-011, FR-012,
  NFR-005)
- [ ] T040 [US6] Write tests for tentative reply format in `tests/unit/cli/ci/resolution/reply_formatter/test_format_tentative_reply.py` — verify "tentative" marker and re-evaluation notice (FR-011)
- [ ] T041 [US6] Implement tentative reply formatting — structured explanation that resolution will be re-evaluated (FR-011, FR-012)

## Phase 9: User Story 7 — Tentative Resolution with Re-evaluation (P3)

- [ ] T042 [US7] Write tests for `ThreadResolutionState` serialization/deserialization in `tests/unit/cli/ci/resolution/state_persistence/test_serialize.py` (FR-015)
- [ ] T043 [US7] Implement `state_persistence.py` — serialize/deserialize `ThreadResolutionState` per thread to pipeline state directory, including iteration count and tentative expiry timestamp
  (FR-015)
- [ ] T044 [US7] Write tests for tentative thread marking (no GraphQL mutation, reply posted) in `tests/unit/cli/ci/resolution/engine/test_tentative_marking.py` (FR-010)
- [ ] T045 [US7] Write tests for re-evaluation on subsequent iteration with new evidence in `tests/unit/cli/ci/resolution/engine/test_reevaluation.py` (FR-014)
- [ ] T046 [US7] Write tests for TTL expiry (5 iterations or 24h) updating reply to "resolution abandoned" in `tests/unit/cli/ci/resolution/state_persistence/test_ttl_expiry.py` (FR-014)
- [ ] T047 [US7] Implement tentative TTL logic in `state_persistence.py` — track iteration count, wall-clock expiry, mark abandoned after 5 iterations or 24 hours (FR-010, FR-014)
- [ ] T048 [US7] Implement re-evaluation flow in engine — tentative threads re-enter tier pipeline, upgrade to confirmed on resolution, abandon on expiry (FR-014)

## Phase 10: User Story 8 — Platform-Agnostic Resolution Engine Interface (P3)

- [ ] T049 [US8] Write tests for `TieredResolutionEngine` orchestration in `tests/unit/cli/ci/resolution/engine/test_tiered_resolution_engine.py` — tier ordering, short-circuit, batch processing
  (FR-001, FR-013)
- [ ] T050 [US8] Implement `TieredResolutionEngine` in `agentic_devtools/cli/ci/resolution/engine.py` — iterate tiers in strict order (outdated→markers→diff→SDK), short-circuit on first verdict,
  per-thread error isolation (FR-001)
- [ ] T051 [US8] Write tests verifying no GitHub-specific types in engine evaluation path in `tests/unit/cli/ci/resolution/engine/test_platform_agnostic.py` (FR-013)
- [ ] T052 [P] [US8] Write mock provider test exercising full pipeline with non-GitHub `ReviewThread` instances in `tests/unit/cli/ci/resolution/engine/test_mock_provider.py` (FR-013)

## Phase 11: Integration & Wiring

- [ ] T053 Write integration tests for `GitHubProvider.finalize_post_repair()` delegating to `TieredResolutionEngine` in `tests/unit/cli/ci/github_provider/test_finalize_post_repair_tiered.py`
- [ ] T054 Refactor `GitHubProvider.finalize_post_repair()` in `agentic_devtools/cli/ci/github_provider.py` to delegate thread resolution to `TieredResolutionEngine`
- [ ] T055 Update `ResolveThreadsAction.execute()` in `agentic_devtools/cli/ci/pipeline/actions/resolve_threads.py` to pass expanded thread data and `ResolutionContext` to the engine
- [ ] T056 Implement reply posting and GraphQL mutation calls through `github_adapter.py` — `resolve_thread()`, `post_reply()` methods with rate-limit backoff (NFR-004)
- [ ] T057 Write tests for GraphQL rate-limit exponential backoff (initial 1s, max 60s, 5 retries) in `tests/unit/cli/ci/resolution/github_adapter/test_rate_limit_backoff.py` (NFR-004)
- [ ] T058 Verify `FinalizationResult` contract is preserved — no breaking changes to return type of `finalize_post_repair()`

## Final Phase: Polish & Cross-Cutting

- [ ] T059 Add DEBUG-level logging on every tier evaluation — thread ID, comment body snippet (first 100 chars), tier name, verdict (NFR-003)
- [ ] T060 Add timing instrumentation — assert programmatic tiers complete within 500ms per thread, total evaluation within 45s (NFR-001)
- [ ] T061 Add SDK invocation count metric tracking for SC-002 validation (NFR-002)
- [ ] T062 Update `agentic_devtools/cli/ci/resolution/__init__.py` to export public API: `TieredResolutionEngine`, protocols, models
- [ ] T063 Add `claude-sonnet-4.6` to `agentic_devtools/cli/setup/commands.py:_KNOWN_COPILOT_MODELS` list
- [ ] T064 Run full test suite (`agdt-test`) and validate 100% coverage on all new files
- [ ] T065 Run `python scripts/validate_test_structure.py` to confirm 1:1:1 compliance
- [ ] T066 Run `ruff check` and `ruff format` on all new and modified files

## Dependency Graph

```text
T001–T003 → T004–T007 (setup before foundational)
T004–T007 → T008–T052 (protocols/models before all tiers and engine)
T011 (github_adapter) → T008–T009 (outdated tier needs parsed threads)
T019–T020 (expanded query) → T010–T011 (adapter needs expanded data)
T008–T013 (tier 1) ─┐
T021–T024 (tier 2) ──┼→ T049–T050 (engine requires all tiers)
T025–T028 (tier 3) ──┤
T029–T036 (tier 4) ──┘
T042–T048 (tentative state) → T049–T050 (engine uses tentative logic)
T049–T052 (engine) → T053–T058 (integration after engine)
T053–T058 → T059–T066 (polish after integration)
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
