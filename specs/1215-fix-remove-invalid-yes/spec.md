# Feature Specification: Remove Invalid --yes Flag and Change Default Merge Strategy to Rebase

**Feature Branch**: `fix/1215-remove-yes-flag-rebase-default`  
**Created**: 2026-04-15  
**Status**: Draft  
**Input**: GitHub Issue #1215  
**Source Issue**: #1215 (<https://github.com/ayaiayorg/agentic-devtools/issues/1215>)

## Summary

The `agdt-gh-pr-merge` command passes `--yes` to `gh pr merge`, but this flag does not exist in any version of the GitHub CLI.
This causes every merge attempt to fail with `unknown flag: --yes`. Additionally, the project convention favours rebase merges,
so the default strategy should be changed from `squash` to `rebase`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 – Merge a PR Successfully Without the Invalid Flag (Priority: P1)

As an AI agent or developer, I want `agdt-gh-pr-merge` to execute `gh pr merge` without passing the non-existent `--yes` flag, so that the merge command no longer fails with `unknown flag: --yes`.

**Why this priority**: This is a blocking bug. The command is completely broken — every invocation fails. No other change matters until the command can execute at all.

**Independent Test**: Can be fully tested by running `agdt-gh-pr-merge --pr <N> --repo <owner/repo>` against a mergeable PR
and verifying the command does not emit `unknown flag: --yes`.
In unit tests, verified by asserting `--yes` is absent from the command list passed to `run_safe`.

**Acceptance Scenarios**:

1. **Given** a mergeable PR exists, **When** `agdt-gh-pr-merge --pr 42 --repo o/r` is executed, **Then** the underlying `gh pr merge` command does NOT include `--yes` in its argument list.
2. **Given** a mergeable PR exists, **When** `agdt-gh-pr-merge --pr 42 --repo o/r --strategy squash` is executed,
   **Then** the command succeeds because `--squash` alone is sufficient to skip interactive confirmation.
3. **Given** a mergeable PR exists, **When** `agdt-gh-pr-merge --pr 42 --repo o/r --strategy rebase` is executed,
   **Then** the command succeeds because `--rebase` alone is sufficient to skip interactive confirmation.
4. **Given** a mergeable PR exists, **When** `agdt-gh-pr-merge --pr 42 --repo o/r --strategy merge` is executed,
   **Then** the command succeeds because `--merge` alone is sufficient to skip interactive confirmation.

---

### User Story 2 – Default Merge Strategy Is Rebase (Priority: P2)

As a developer using `agdt-gh-pr-merge`, I want the default merge strategy to be `rebase` (instead of `squash`),
so that PRs merged without an explicit `--strategy` flag produce a linear rebase history by default.

**Why this priority**: This is a behavioural change to a sensible default. It does not block functionality
but aligns the tool with the project's preferred merge convention. It is independent of the bug fix but ships alongside it.

**Independent Test**: Can be tested by invoking `agdt-gh-pr-merge --pr 42` without a `--strategy` flag
and verifying that `--rebase` is the strategy flag in the underlying `gh` command.
In unit tests, verified by checking the strategy argument passed to `_execute_merge` and the `github.pr_merge_strategy` state key.

**Acceptance Scenarios**:

1. **Given** no `--strategy` flag is provided, **When** `agdt-gh-pr-merge --pr 42` is executed, **Then** the merge uses the `rebase` strategy (i.e., `--rebase` is passed to `gh pr merge`).
2. **Given** no `--strategy` flag is provided, **When** the merge succeeds, **Then** the state key `github.pr_merge_strategy` is set to `"rebase"`.
3. **Given** `--strategy squash` is explicitly provided, **When** `agdt-gh-pr-merge --pr 42 --strategy squash` is executed, **Then** the merge uses the `squash` strategy, overriding the new default.
4. **Given** the CLI help is displayed, **When** the user runs `agdt-gh-pr-merge --help`, **Then** the `--strategy` option shows `rebase` as the default value.

---

### User Story 3 – Documentation and Internal References Reflect New Defaults (Priority: P3)

As a contributor reading the codebase, copilot-instructions, or workflow prompts, I want the documented default
strategy for `agdt-gh-pr-merge` to say `rebase` (not `squash`), so that documentation matches
runtime behaviour.

**Why this priority**: Documentation accuracy is important but not functionally blocking. It should be updated alongside the code change.

**Independent Test**: Can be verified by searching the codebase, copilot-instructions, and prompt/agent files for references to the default merge strategy and confirming they all say `rebase`.

**Documentation Scope**: The following files reference the squash default and must be updated:

- `.github/copilot-instructions.md` — command mapping table (`gh pr merge --squash`) and `agdt-gh-pr-merge` parameter documentation (`default squash`)
- `.github/prompts/agdt.pr-merge-manager.prompt.md` — tooling priority table (`gh pr merge --squash`)

**Acceptance Scenarios**:

1. **Given** the `merge_pr` function signature, **When** a developer reads the default value of the `strategy` parameter, **Then** it reads `"rebase"`.
2. **Given** the CLI argparse definition, **When** a developer reads the `--strategy` help text, **Then** it states the default is `rebase`.
3. **Given** the copilot-instructions documentation for `agdt-gh-pr-merge`, **When** a reader checks the documented default strategy, **Then** it says `rebase`.
4. **Given** the `.github/prompts/agdt.pr-merge-manager.prompt.md` file, **When** a reader checks the fallback command for `agdt-gh-pr-merge`, **Then** the example uses `--rebase` (not `--squash`).
5. **Given** the `.github/copilot-instructions.md` command mapping table, **When** a reader checks the raw equivalent for `agdt-gh-pr-merge`, **Then** the example uses `gh pr merge --rebase --delete-branch`.

---

### Edge Cases

- What happens when `gh pr merge` is invoked with `--rebase` on a PR that has merge conflicts? → The command should return a classified `merge_conflict` error, same as before.
- What happens when an explicit `--strategy squash` is passed? → The explicit flag overrides the new default; squash merges must still work.
- What happens when `--strategy merge` is passed? → Regular merge strategy must still work; only the *default* changes.
- What happens if a downstream script or prompt hard-codes `"squash"` as the expected default strategy in an assertion? → Such tests must be updated to expect `"rebase"`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `_execute_merge` function MUST NOT include `--yes` in the command list passed to `gh pr merge`.
- **FR-002**: The module-level constant `_DEFAULT_STRATEGY` MUST be `"rebase"`.
- **FR-003**: The `merge_pr` function signature MUST use `strategy="rebase"` as the default parameter value.
- **FR-004**: The CLI `--strategy` argument MUST default to `"rebase"` and its help text MUST reflect this.
- **FR-005**: All three merge strategies (`squash`, `merge`, `rebase`) MUST remain valid and selectable via `--strategy`.
- **FR-006**: All existing merge verification, retry, and state-writing behaviour MUST remain unchanged.
- **FR-007**: Unit tests that previously asserted the presence of `--yes` in the command list MUST be updated to assert its absence.
- **FR-008**: Unit tests that previously asserted a default strategy of `"squash"` MUST be updated to assert `"rebase"`.

### Non-Functional Requirements

- **NFR-001**: The fix MUST NOT change the public CLI interface beyond the default strategy value (all existing flags and options remain).
- **NFR-002**: The fix MUST NOT introduce any new dependencies.
- **NFR-003**: All existing tests MUST pass after the changes, with no reduction in coverage.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `agdt-gh-pr-merge --pr <N>` no longer fails with `unknown flag: --yes` when run against a real GitHub repository.
- **SC-002**: Running `agdt-gh-pr-merge --pr <N>` without `--strategy` results in `github.pr_merge_strategy` being set to `"rebase"` in state.
- **SC-003**: The full test suite passes with zero failures (`agdt-test` / `bash scripts/run-pr-checks.sh`).
- **SC-004**: No test asserts the presence of `--yes` in any `gh pr merge` command list.
- **SC-005**: The `_DEFAULT_STRATEGY` constant equals `"rebase"` at module level.

---
*Generated by Copilot SDK (claude-opus-4.6)*
