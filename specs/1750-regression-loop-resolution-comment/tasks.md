# Tasks: Restore Full Resolution Comment Format in AI PR Loop

## Phase 1: Setup

- [ ] T001 Create test directory `tests/unit/cli/ci/github_provider/` `__init__.py` if missing and verify test infrastructure for new test files
- [ ] T002 Create test file `tests/unit/cli/ci/github_provider/test__build_head_commit_line.py` (skeleton with imports)

## Phase 2: Foundational — HEAD Commit Link Helper

- [ ] T003 Write failing tests for `_build_head_commit_line()` static method covering: valid SHA+repo returns formatted link, empty/None `head_sha` returns empty string, SHA shorter than 7 chars
  returns empty string, short SHA is first 7 chars of full SHA — file: `tests/unit/cli/ci/github_provider/test__build_head_commit_line.py`
- [ ] T004 Implement `_build_head_commit_line(head_sha, repo)` as `@staticmethod` on `GitHubPlatformProvider` in `agentic_devtools/cli/ci/github_provider.py` — satisfies FR-002 (HEAD commit link
  format `**HEAD**: [<short_sha>](url)`) and supports FR-003 fallback path
- [ ] T005 Run tests for `test__build_head_commit_line.py` and verify GREEN

## Phase 3: User Story 1 — Reviewer Auditing Automated Resolution (P1)

- [ ] T006 [US1] Write failing tests in `tests/unit/cli/ci/github_provider/test_finalize_post_repair_reply_format.py` for case (a): `tier_result` available with normal resolution →
  `build_full_reply()` is invoked (FR-001: structured format for ALL resolutions with TierResult)
- [ ] T007 [US1] Write failing test for case (c): `tier_result` is None → reply is static fallback text "Addressed on the updated PR branch." + HEAD link (FR-003: graceful None handling)
- [ ] T008 [US1] Write failing test for case (b): `tier_result` with "fallback" in tier_name → `format_unconfirmed_commit_change_reply()` + HEAD link (FR-005: existing fallback/unconfirmed paths
  maintained)
- [ ] T009 [US1] Write failing test asserting `<!-- agdt:resolution-tier:<tier_name> -->` HTML marker is present in all structured replies (FR-006: HTML marker emission)
- [ ] T010 [US1] Write failing test asserting `_has_existing_addressed_reply` recognizes both old static text and new structured format with `_RESOLUTION_TIER_MARKER_PREFIX` (FR-007: duplicate
  detection backward compat; FR-004: old static text still recognized)
- [ ] T011 [US1] Modify `finalize_post_repair()` in `agentic_devtools/cli/ci/github_provider.py` — replace `else: reply_body = _ADDRESSED_REPLY_BODY` with `elif tier_result is not None: reply_body =
  reply_formatter.build_full_reply(...)` then `else: reply_body = _ADDRESSED_REPLY_BODY` (FR-001 implementation)
- [ ] T012 [US1] Append HEAD commit link after reply_body determination in `finalize_post_repair()` via `reply_body += self._build_head_commit_line(head_sha, repo)` for all COMMENT_RESOLVE paths
  (FR-002 integration)
- [ ] T013 [US1] Run tests for `test_finalize_post_repair_reply_format.py` and verify GREEN — covers SC-001, SC-003, SC-005(a)(b)(c)
- [ ] T014 [US1] Write regression test asserting bare `_ADDRESSED_REPLY_BODY` is NEVER the sole reply when `tier_result` is non-null (SC-003 explicit guard)

## Phase 4: User Story 2 — Reviewer Tracing Resolution to Commit (P1)

- [ ] T015 [P] [US2] Write tests in `tests/unit/cli/ci/github_provider/test_finalize_post_repair_reply_format.py` for case (d): HEAD SHA available → `**HEAD**:` line present with correct markdown link
  format (FR-002 verification)
- [ ] T016 [P] [US2] Write tests for case (e): HEAD SHA empty/None → no `**HEAD**:` line appended, no error raised (FR-002 graceful degradation)
- [ ] T017 [US2] Verify tests for T015/T016 pass GREEN with implementation from T004+T012

## Phase 5: User Story 3 — Distinguishing Confidence Levels (P2)

- [ ] T018 [P] [US3] Write tests verifying `build_full_reply()` output contains `[high]` confidence indicator when tier_result.confidence is "high" — file:
  `tests/unit/cli/ci/github_provider/test_finalize_post_repair_reply_format.py`
- [ ] T019 [P] [US3] Write tests verifying `build_full_reply()` output contains `[low]` confidence indicator when tier_result.confidence is "low"
- [ ] T020 [US3] Verify confidence indicator tests pass GREEN (no implementation change expected — `ReplyFormatter` already formats confidence)

## Phase 6: User Story 4 — Documentation of Reply Format Variants (P3)

- [ ] T021 [US4] Add inline documentation block in `finalize_post_repair()` COMMENT_RESOLVE section mapping resolution scenarios to reply formats (decision tree comment) — file:
  `agentic_devtools/cli/ci/github_provider.py`
- [ ] T022 [US4] Add/update module-level or class-level docstring in `agentic_devtools/cli/ci/resolution/reply_formatter.py` describing which method is used per resolution scenario and that HEAD link
  is caller responsibility

## Final Phase: Polish & Cross-Cutting

- [ ] T023 Run `agdt-test-file --source-file agentic_devtools/cli/ci/github_provider.py` — verify 100% branch coverage on modified lines (NFR-002, SC-005)
- [ ] T024 Run `agdt-test` full suite — verify all existing `ReplyFormatter` tests pass unmodified (SC-004, FR-005 confirmation)
- [ ] T025 Run `bash scripts/targeted-checks.sh` — verify ruff, mypy, markdownlint pass
- [ ] T026 Verify `_has_existing_addressed_reply` tests still pass with no modification needed (FR-004, FR-007 confirmation)
- [ ] T027 Write integration-level test confirming end-to-end `finalize_post_repair()` with real `ReplyFormatter` produces complete structured reply with HEAD link (SC-001, SC-002 proxy)

## Dependencies

| Task | Depends On |
|------|-----------|
| T003 | T001, T002 |
| T004 | T003 |
| T005 | T004 |
| T006 | T005 |
| T007 | T005 |
| T008 | T005 |
| T009 | T005 |
| T010 | T001 |
| T011 | T006, T007, T008, T009 |
| T012 | T011 |
| T013 | T012 |
| T014 | T013 |
| T015 | T005 |
| T016 | T005 |
| T017 | T012, T015, T016 |
| T018 | T012 |
| T019 | T012 |
| T020 | T018, T019 |
| T021 | T012 |
| T022 | T012 |
| T023 | T014, T017, T020 |
| T024 | T023 |
| T025 | T024 |
| T026 | T024 |
| T027 | T024 |

## FR Traceability Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T006, T011, T013, T014 |
| FR-002 | T003, T004, T012, T015, T016, T017 |
| FR-003 | T004, T007, T013 |
| FR-004 | T010, T026 |
| FR-005 | T008, T024 |
| FR-006 | T009, T013 |
| FR-007 | T010, T026 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
