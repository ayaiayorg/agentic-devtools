# Tasks: AI PR Loop — No-Commit-Needed Detection

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Project scaffolding (no direct plan equivalent) |
| Phase 2: Foundational | Plan Phase 2 (partial) | Marker constants and shared models |
| Phase 3: User Story 4 | Plan Phase 1 | ThreadEvaluatedTier implementation |
| Phase 4: User Story 1 | Plan Phases 2, 3, 4, 8 | Detection, resolution, mixed scenario, logging |
| Phase 5: User Story 2 | Plan Phase 5 | Agent git instructions prompt updates |
| Phase 6: User Story 1 (continued) | Plan Phase 6 | No-change marker instructions |
| Phase 7: User Story 3 | Plan Phase 7 | Copilot reviewer custom instructions |
| Phase 8: Final | Plan Phase 9 | Integration tests, edge cases, and polish |

## Phase 1: Setup

- [ ] T001 Create feature branch `1916-ai-pr-loop-no-commit-needed` from `main`
- [ ] T002 [US4] Create test directory structure `tests/unit/cli/ci/resolution/tiers/thread_evaluated/__init__.py` (FR-002, FR-010)
- [ ] T003 [US1] Create test directory structure `tests/unit/cli/ci/evaluator/classifier/__init__.py` (if missing) (FR-001)
- [ ] T004 [US1] Create test directory structure `tests/unit/cli/ci/evaluator/actions/__init__.py` (if missing) (FR-001, FR-012)

## Phase 2: Foundational — Marker Constants and Shared Models

- [ ] T005 Add marker constants (`REPAIR_SATISFIED_MARKER`, `THREAD_EVALUATED_MARKER`, `REVIEW_ID_MARKER_RE`) to `agentic_devtools/cli/ci/guards.py`
- [ ] T006 [US1] Write tests for marker constants and regex extraction in `tests/unit/cli/ci/guards/test_repair_satisfied_marker.py` (FR-001, FR-002)
- [ ] T007 Extend `PostAgentSnapshot` with `has_repair_satisfied_marker: bool` and `repair_satisfied_review_id: int | None` fields in `agentic_devtools/cli/ci/evaluator/models.py`
- [ ] T008 Add `PostAgentClassification.repair_satisfied_no_changes` enum value in `agentic_devtools/cli/ci/evaluator/models.py`
- [ ] T009 Add `PostAgentAction.resolve_evaluated_threads` enum value in `agentic_devtools/cli/ci/evaluator/models.py`
- [ ] T010 [US1] Write tests for new enum values in `tests/unit/cli/ci/evaluator/models/test_postagentclassification.py` and `tests/unit/cli/ci/evaluator/models/test_postagentaction.py` (FR-001, FR-002)

## Phase 3: User Story 4 — Thread Evaluation Marker Tier (P1)

- [ ] T011 [US4] Write failing tests for `ThreadEvaluatedTier.evaluate()` — marker present from authorized identity → HIGH confidence RESOLVE (FR-002) in
  `tests/unit/cli/ci/resolution/tiers/thread_evaluated/test_threadevaluatedtier.py`
- [ ] T012 [US4] Write failing test — marker from unauthorized identity → returns None (FR-010) in `tests/unit/cli/ci/resolution/tiers/thread_evaluated/test_threadevaluatedtier.py`
- [ ] T013 [US4] Write failing test — no marker present → returns None (FR-002) in `tests/unit/cli/ci/resolution/tiers/thread_evaluated/test_threadevaluatedtier.py`
- [ ] T014 [US4] Implement `ThreadEvaluatedTier` class scanning thread comments for `<!-- ai-pr-loop:thread-evaluated -->` marker with author validation against `COPILOT_COMMENT_LOGINS` (FR-002,
  FR-010) in `agentic_devtools/cli/ci/resolution/tiers/thread_evaluated.py`
- [ ] T015 [US4] Export `ThreadEvaluatedTier` from `agentic_devtools/cli/ci/resolution/tiers/__init__.py`
- [ ] T016 [US4] Register `ThreadEvaluatedTier` in the default tier list after `SweAgentReplyTier` and before `DiffHeuristicTier` in `agentic_devtools/cli/ci/resolution/engine.py` (or wherever tiers
  are composed)
- [ ] T017 [US4] Write integration test verifying tier ordering: marked threads resolved before falling through to `DiffHeuristicTier` (FR-002) in
  `tests/unit/cli/ci/resolution/tiers/thread_evaluated/test_threadevaluatedtier_integration.py`

## Phase 4: User Story 1 — Repair-Satisfied Detection and Direct Resolution (P1)

- [ ] T018 [US1] Write failing tests for snapshot marker detection of `repair-satisfied` comments since dispatch timestamp in `tests/unit/cli/ci/evaluator/snapshot/` (FR-001)
- [ ] T019 [US1] Implement `build_snapshot()` extension to scan issue comments for `repair-satisfied` marker and extract `review-id` in `agentic_devtools/cli/ci/evaluator/snapshot.py`
- [ ] T020 [US1] Write failing tests for `classify_post_agent_state()` returning `repair_satisfied_no_changes` when marker present and no head change in `tests/unit/cli/ci/evaluator/classifier/` (FR-001)
- [ ] T021 [US1] Implement classification rule for `repair_satisfied_no_changes` (priority between `complete` and `threads_resolved_no_sentinel`, condition: `snapshot.has_repair_satisfied_marker and
  not snapshot.head_changed_since_review`) — satisfies FR-001 detection in `agentic_devtools/cli/ci/evaluator/classifier.py`
- [ ] T022 [US1] Write failing tests for review-id mismatch validation (FR-011) — marker with wrong review-id is ignored in `tests/unit/cli/ci/evaluator/actions/`
- [ ] T023 [US1] Write failing tests for `resolve_evaluated_threads()` action handler — resolves only threads with `thread-evaluated` markers from authorized identities (FR-012 direct resolution path)
  in `tests/unit/cli/ci/evaluator/actions/`
- [ ] T024 [US1] Write failing test for partial resolution — `repair-satisfied` present but some threads missing `thread-evaluated` reply → partial resolution + warning logged (FR-012)
- [ ] T025 [US1] Implement `resolve_evaluated_threads()` action handler that checks review-id match (FR-011), fetches review threads, identifies threads with `thread-evaluated` replies from
  `COPILOT_COMMENT_LOGINS`, resolves via resolution engine bypassing `finalize_post_repair()` (FR-001, FR-012), and logs warnings for unmarked threads in `agentic_devtools/cli/ci/evaluator/actions.py`
- [ ] T026 [US1] Add helper method `list_thread_replies(pr_number, comment_id) -> list[CommentInfo]` to `agentic_devtools/cli/ci/github_provider.py`
- [ ] T027 [US1] Write tests for `list_thread_replies` in `tests/unit/cli/ci/github_provider/` (FR-012)
- [ ] T028 [US1] Wire `resolve_evaluated_threads` action into the evaluator dispatch (action mapping for `PostAgentAction.resolve_evaluated_threads`) in `agentic_devtools/cli/ci/evaluator/command.py`
  or equivalent dispatcher
- [ ] T029 [US1] Write failing test for structured logging — reason `"agent_no_changes_needed"` logged with pr_number, review_id, threads_evaluated, threads_resolved (FR-005, NFR-003)
- [ ] T030 [US1] Implement structured INFO-level logging in the action handler per FR-005 and NFR-003
- [ ] T031 [US1] Write failing test for idempotency — resolving already-resolved thread produces no error (FR-012, NFR-002)
- [ ] T032 [US1] Write test for mixed scenario (US1-AC2) — agent pushes commit, `thread-evaluated` markers on no-change threads resolved via `ThreadEvaluatedTier` during normal (FR-001, FR-002)
  `finalize_post_repair()` flow

## Phase 5: User Story 2 — Agent Git Instructions for Cloud Environment (P2)

- [ ] T033 [P] [US2] Remove `agdt-git-save-work` from Tooling Priority table in `.github/prompts/agdt.address-copilot-review.evaluate-and-respond.prompt.md` (FR-006)
- [ ] T034 [P] [US2] Remove CI Repair Note prohibiting raw `git commit`/`git push` and replace with cloud agent exception authorization (FR-008) in
  `.github/prompts/agdt.address-copilot-review.evaluate-and-respond.prompt.md`
- [ ] T035 [US2] Replace Phase 6 Commit & Push section with `git commit --amend --no-edit` + `git push` instructions and explicit policy exception note (FR-006) in
  `.github/prompts/agdt.address-copilot-review.evaluate-and-respond.prompt.md`
- [ ] T036 [US2] Add non-fast-forward fallback instructions: new commit with `[ai-repair]` tag and conventional commit message (FR-007) in
  `.github/prompts/agdt.address-copilot-review.evaluate-and-respond.prompt.md`
- [ ] T049 [US2] Write test asserting `agdt-git-save-work` no longer appears in Tooling Priority table or Commit & Push section (FR-006) in
  `tests/unit/prompts/test_evaluate_and_respond_prompt.py`
- [ ] T050 [US2] Write test asserting Commit & Push section contains `git commit --amend --no-edit` and `git push` instructions, and non-fast-forward fallback block is present (FR-006, FR-007) in
  `tests/unit/prompts/test_evaluate_and_respond_prompt.py`
- [ ] T051 [US2] Write test asserting raw-git prohibition text ("Do not fall back to raw `git commit`/`git push`") is absent from prompt (FR-008) in
  `tests/unit/prompts/test_evaluate_and_respond_prompt.py`

## Phase 6: User Story 1 (continued) — Agent No-Change Marker Instructions (P1)

- [ ] T037 [US1] Add prompt section instructing agent to post `<!-- ai-pr-loop:thread-evaluated -->` per-thread reply with explanation when no code changes needed (FR-003) in
  `.github/prompts/agdt.address-copilot-review.evaluate-and-respond.prompt.md`
- [ ] T038 [US1] Add prompt section instructing agent to post summary comment with `<!-- ai-pr-loop:repair-satisfied -->` and `<!-- review-id:{review_id} -->` when ALL threads need no changes (FR-004)
  in `.github/prompts/agdt.address-copilot-review.evaluate-and-respond.prompt.md`
- [ ] T039 [US1] Add explicit prohibition in prompt: "Do NOT post `repair-satisfied` in mixed scenarios" (FR-004) in `.github/prompts/agdt.address-copilot-review.evaluate-and-respond.prompt.md`
- [ ] T052 [US1] Write test asserting prompt contains per-thread `<!-- ai-pr-loop:thread-evaluated -->` marker instruction with required explanation guidance (FR-003) in
  `tests/unit/prompts/test_evaluate_and_respond_prompt.py`
- [ ] T053 [US1] Write test asserting prompt contains `<!-- ai-pr-loop:repair-satisfied -->` and `<!-- review-id:{review_id} -->` summary comment instruction for all-declined scenario, and
  prohibits posting in mixed scenarios (FR-004) in `tests/unit/prompts/test_evaluate_and_respond_prompt.py`

## Phase 7: User Story 3 — Copilot Reviewer Custom Instructions (P2)

- [ ] T040 [P] [US3] Create `.github/instructions/code-review.instructions.md` with `applyTo: "**"` header, CI-comment prohibitions, and positive focus directives (FR-009, NFR-004) — must be under 1KB
- [ ] T054 [US3] Write test asserting `.github/instructions/code-review.instructions.md` exists, contains `applyTo: "**"` front-matter header, includes MUST NOT prohibitions for CI/lint comments, and
  file size is under 1KB (FR-009, NFR-004) in `tests/unit/test_code_review_instructions.py`

## Phase 8: Final — Integration Tests, Edge Cases, and Polish

- [ ] T041 Write integration test: happy path — all threads marked → all resolved, clean exit with `agent_no_changes_needed` reason (FR-001, FR-005, FR-012)
- [ ] T042 Write integration test: review-id mismatch — marker present but wrong review-id → marker ignored, no resolution (FR-011)
- [ ] T043 Write integration test: 20+ concurrent threads resolved in single pass without timeout (FR-012, SC-007)
- [ ] T044 Write integration test: duplicate dispatch — resolving already-resolved threads is idempotent (FR-012, NFR-002)
- [ ] T045 Run full test suite (`agdt-test`) and verify 100% branch coverage on all new/modified source files
  (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-012, SC-005)
- [ ] T046 Run `scripts/validate_test_structure.py` to confirm 1:1:1 test structure compliance (FR-001)
- [ ] T047 Run `bash scripts/targeted-checks.sh` to confirm linting, formatting, and type checks pass (FR-001)
- [ ] T048 Verify `.github/instructions/code-review.instructions.md` is under 1KB (FR-009, NFR-004)

## Dependency Graph

```text
T001 → T002–T004 (setup)
T005–T006 → T007–T010 (foundational models)
T007–T010 → T011–T017 (US4: ThreadEvaluatedTier)
T007–T010 → T018–T032 (US1: detection + resolution)
T014–T016 → T025 (action handler uses ThreadEvaluatedTier)
T025–T026 → T028 (wire action into dispatcher)
T033–T036, T049–T051 are parallelizable (US2: prompt edits + verification, no code deps)
T037–T039, T052–T053 depend on T021 (classification must exist before prompting for it)
T040, T054 are independent (US3: new file + verification, no code deps)
T041–T044 depend on T028 (all integration paths wired)
T045–T048 depend on T041–T044 (final validation)
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
