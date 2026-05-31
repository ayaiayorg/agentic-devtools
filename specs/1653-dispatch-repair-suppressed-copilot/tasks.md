# Tasks: Suppressed Copilot Review Comments in Repair Dispatch (#1653)

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Project scaffolding (no direct plan equivalent) |
| Phase 2: Foundational | — | NFR confirmation (no direct plan equivalent) |
| Phase 3: US1 | Plan Phase 1, 2, 3, 4 | Parser (FR-007), dedup (FR-004), fetch (FR-006), integration (FR-001, FR-003, FR-008) |
| Phase 4: US2 | Plan Phase 4 | Suppressed-only review handling (FR-001, FR-002, FR-003) |
| Phase 5: US3 | Plan Phase 4 | Regression / behavior preservation (FR-005) |
| Phase 6: Downstream Guards | Plan Phase 4 | Evaluator and snapshot guard tasks |
| Final Phase: Polish & Cross-Cutting | Plan Phase 5 | Verification, lint, structure checks |

---

## Phase 1: Setup

- [ ] T001 Verify test directory structure for new test modules, keeping existing `tests/unit/cli/ci/github_provider/` as-is and creating missing `__init__.py` files only if absent in
  `tests/unit/cli/ci/pipeline/snapshot/` and `tests/unit/cli/ci/evaluator/snapshot/`

## Phase 2: Foundational

- [ ] T002 Verify `ReviewCommentInfo` dataclass in `agentic_devtools/cli/ci/models.py` already has `is_suppressed: bool = False` field and requires no changes (NFR-002 confirmation)
- [ ] T003 Verify `_build_repair_comment()` in `agentic_devtools/cli/ci/github_provider.py` already handles `is_suppressed=True` rendering and requires no changes (NFR-002 confirmation)

## Phase 3: US1 — Include Suppressed Review Feedback (P1)

- [ ] T004 [US1] Write failing unit tests for `_parse_suppressed_from_review_body()` (FR-007, FR-002) covering: valid entries with bold/code file paths, entries without file paths producing `(unknown
  file)` marker, HTML entities/escaped markdown readability, markdown bodies with code fences/bullets/quoted text, empty `<details>` block, malformed HTML, absent `<details>` block, and multiple
  entries — at `tests/unit/cli/ci/github_provider/test__parse_suppressed_from_review_body.py`
- [ ] T005 [US1] Implement standalone `_parse_suppressed_from_review_body(review_body: str) -> list[ReviewCommentInfo]` function in `agentic_devtools/cli/ci/github_provider.py` using stdlib `re` to
  parse `<details>` block with "suppressed due to low confidence" summary, extract file paths (bold/code-formatted) and bodies, assign negative sentinel IDs, set `is_suppressed=True`, use `(unknown
  file)` fallback (FR-007, FR-002, FR-003), log warning on malformed HTML (FR-008)
- [ ] T006 [US1] Write failing unit tests for `_deduplicate_review_comments()` (FR-004) covering: no overlap, exact duplicate removal preserving REST entry, whitespace/CRLF normalization, leading `/`
  path normalization, partial substring match preserved — at `tests/unit/cli/ci/github_provider/test__deduplicate_review_comments.py`
- [ ] T007 [US1] Implement `_deduplicate_review_comments(rest_comments, suppressed_comments) -> list[ReviewCommentInfo]` in `agentic_devtools/cli/ci/github_provider.py` with exact-match deduplication
  after normalizing paths (strip whitespace, remove leading `/`) and bodies (CRLF→LF, strip whitespace), preserving non-suppressed entry on collision (FR-004)
- [ ] T008 [US1] Implement review body fetch via `GET /repos/{owner}/{repo}/pulls/{pr_number}/reviews/{review_id}` within `list_review_comments()` in `agentic_devtools/cli/ci/github_provider.py`,
  gated on `review_id > 0`, with try/except that logs a recoverable warning and returns REST-only on failure (FR-006, FR-008)
- [ ] T009 [US1] Integrate suppressed-comment recovery into `list_review_comments()` in `agentic_devtools/cli/ci/github_provider.py`: after REST fetch, wrap review body fetch → parse suppressed →
  deduplicate in a fail-soft try/except that logs a recoverable warning and returns REST-only on any recovery failure; otherwise return merged list (FR-001, FR-003, FR-008)
- [ ] T010 [US1] Write/update integration tests in `tests/unit/cli/ci/github_provider/test_list_review_comments.py` for: success case: mixed REST+suppressed comments merged, review body fetch
  failure returns REST-only (FR-008), suppressed parsing/recovery failure logs a warning and returns REST-only (FR-008), `review_id <= 0` skips body fetch and returns REST-only (FR-006)

## Phase 4: US2 — Handle Suppressed-Only Feedback (P1)

- [ ] T011 [US2] Add test case in `tests/unit/cli/ci/github_provider/test_list_review_comments.py` verifying success case: when REST comments endpoint returns empty list but review body contains
  suppressed entries, `list_review_comments()` returns those suppressed entries with `is_suppressed=True` and file context (FR-001, FR-002, FR-003)
- [ ] T012 [US2] Add test in `tests/unit/cli/ci/github_provider/test__build_repair_comment.py` verifying the generated repair comment includes suppressed-only entries with correct `(suppressed
  comment)` label and file path (FR-003)

## Phase 5: US3 — Preserve Existing Dispatch Behavior (P2)

- [ ] T013 [US3] Add regression test in `tests/unit/cli/ci/github_provider/test_list_review_comments.py` verifying that when review body has no `<details>` block, `list_review_comments()` returns only
  REST-sourced comments unchanged with no synthetic suppressed entries (FR-005)
- [ ] T014 [US3] Add regression test in `tests/unit/cli/ci/github_provider/test__build_repair_comment.py` verifying existing regular-inline-comment rendering is unchanged when no suppressed comments
  are present (FR-005)

## Phase 6: Downstream Guards

- [ ] T015 [P] [US1] Write failing test in `tests/unit/cli/ci/evaluator/snapshot/test_build_snapshot.py` verifying that suppressed `ReviewCommentInfo` entries (negative IDs, `is_suppressed=True`)
  are excluded from `ThreadInfo` list in evaluator snapshot
- [ ] T016 [US1] Add `is_suppressed` guard in `agentic_devtools/cli/ci/evaluator/snapshot.py` at line ~132 to skip thread-resolution lookup for entries where `rc.is_suppressed is True` (synthetic
  negative IDs must not be used as GitHub thread IDs)
- [ ] T017 [P] [US1] Write test in `tests/unit/cli/ci/pipeline/snapshot/test_build_pr_state_snapshot.py` verifying `copilot_review_inline_count` correctly counts merged comments (REST +
  suppressed) after recovery
- [ ] T018 [P] [US1] Write failing test in `tests/unit/cli/ci/pipeline/snapshot/test__count_unresolved_prior_threads.py` verifying suppressed synthetic entries are excluded from unresolved prior
  thread counting and are not used as GitHub thread IDs
- [ ] T019 [US1] Implement `is_suppressed` filter in `_count_unresolved_prior_threads()` in `agentic_devtools/cli/ci/pipeline/snapshot.py` to exclude synthetic negative-ID suppressed entries
  (`rc.is_suppressed is True`) from the unresolved-thread count
- [ ] T020 [US1] Write failing test in `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py` verifying `finalize_post_repair()` excludes synthetic suppressed entries
  (`is_suppressed=True`, negative sentinel IDs) from unresolved-thread updates and does not emit `COMMENT_UNRESOLVE` events for them
- [ ] T021 [US1] Implement suppressed-entry filtering in `agentic_devtools/cli/ci/github_provider.py` within `finalize_post_repair()` so only real unresolved prior threads contribute to
  `unresolved_count`/derived state and event emission

## Final Phase: Polish & Cross-Cutting

- [ ] T022 Run timing verification for integrated `list_review_comments()` path (including review-body fetch) under normal conditions to confirm NFR-001 completion remains under 120 seconds
- [ ] T023 Run `agdt-test` full suite to verify all existing tests pass and new tests pass with 100% branch coverage on touched files
- [ ] T024 Run `bash scripts/targeted-checks.sh` to validate ruff format, ruff check, mypy, and markdownlint pass
- [ ] T025 Run `python scripts/validate_test_structure.py` to confirm 1:1:1 test structure compliance for all new test files

## Dependency Graph

```text
T001 → T004, T006
T002, T003 → T005 (confirmation before implementation)
T004 → T005 (RED → GREEN)
T006 → T007 (RED → GREEN)
T005, T007 → T008 → T009 → T010
T009 → T011, T012, T013, T014
T009 → T015
T015 → T016 (RED → GREEN)
T009 → T017, T018
T018 → T019 (RED → GREEN)
T020 → T021 (RED → GREEN)
T010, T011, T012, T013, T014, T015, T016, T017, T019, T021 → T022 → T023 → T024 → T025
```

## FR Coverage Matrix

| FR | Tasks |
|---|---|
| FR-001 | T009, T010, T011, T019, T020, T021 |
| FR-002 | T004, T005, T011 |
| FR-003 | T005, T009, T011, T012, T020, T021 |
| FR-004 | T006, T007 |
| FR-005 | T013, T014 |
| FR-006 | T008, T010 |
| FR-007 | T004, T005 |
| FR-008 | T005, T008, T010 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
