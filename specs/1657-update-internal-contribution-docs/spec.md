# Feature Specification: Update internal contribution docs and prompts for automated validation (4-tier CI, pre-push hooks)

**Source Issue**: #1657 (<https://github.com/ayaiayorg/agentic-devtools/issues/1657>)

## Problem Statement

With the 4-tier CI pipeline merged (PR #1650) and pre-push hooks now enforcing code quality
automatically, several internal docs and agentic-devtools-only prompts still reference outdated
manual validation instructions or old tooling (e.g., `black`, `isort`, `flake8`). The 4-tier CI
gate names (`Targeted Checks ✅`, `Smart Module Tests ✅`, `Copilot Review ✅`) are not documented
anywhere contributors or agents can easily reference them, and the pre-push hook automation is not
mentioned in contribution guidance at all.

## Clarifications

### Session 2026-05-30

- Q: The spec refers to "4-tier CI" but only lists 3 gate names (`Targeted Checks ✅`, `Smart Module Tests ✅`, `Copilot Review ✅`). What is the 4th tier, and should it be documented in the updated
  files? → A: The 4th tier is `Post-Merge Full Suite` which runs after merge (not as a PR gate). Since only the 3 PR gates appear in the GitHub Actions PR checks UI, docs should list the 3 PR gates
  explicitly and optionally mention the post-merge full suite as a non-blocking 4th tier. The phrase "4-tier CI pipeline" should be used in the overview context, with the 3 PR-blocking gates called
  out individually.

- Q: Should the `bandit -r src/` security check line in `senior-python-developer.md` (line 567) be preserved, removed, or updated? The spec only explicitly calls out removing `black`/`isort`/`flake8`
  but doesn't mention `bandit`. → A: Preserve the `bandit -r src/` line. The spec's scope is limited to replacing outdated formatter/linter references (`black`, `isort`, `flake8`) with `ruff`.
  `bandit` is a security scanner unrelated to the formatting/linting consolidation and remains valid tooling guidance.

- Q: The `copilot-instructions.md` file currently references `cd src` before commands, but the actual project root is used for `ruff` and `pytest`. Should the `cd src` instruction be corrected? → A:
  Yes, correct the `cd src` to reflect the actual project layout. Commands should reference the repository root (where `pyproject.toml` lives). This is a pre-existing inaccuracy that is tightly
  coupled to the commands being updated — fixing it is in-scope as part of making the file accurate.

- Q: For the CI-repair prompts (files 3 and 4), should the updates add a new dedicated section about the 4-tier CI gates, or should the gate names be woven into the existing "For Lint Failures" / "For
  Test Failures" structure? → A: Add a brief introductory note at the top of the CI failure handling phase (Phase 3b / Phase 5) that lists the 3 PR gate names and what each covers. Then within the
  existing sub-sections, reference the relevant gate when applicable. This keeps the existing structure intact while making gate names discoverable.

- Q: Should `copilot-instructions.md` document the `agdt-test` commands (as the canonical way to run tests in this repo) or keep the generic `pytest` reference? → A: Replace the bare `pytest`
  reference with `agdt-test` / `agdt-task-wait` as the canonical test commands for this repo. This aligns with the repo's custom instructions which state "ALWAYS use agdt-test commands, NEVER run
  pytest directly." The `copilot-instructions.md` is repo-specific guidance and should reflect repo-specific tooling.

## Files to Update

### 1. `.github/agents/senior-python-developer.md` (lines 540–568)

**Outdated section** referencing `black`, `isort`, `flake8` instead of `ruff`:

```python
# Format code
black .
isort .

# Type check
mypy src/

# Lint
ruff check .

# Test with coverage
pytest --cov=src --cov-report=html

# Security check
bandit -r src/
```

Also line 545:

```text
**Linting**: ruff (or black + flake8 + isort)
```

**Should become:**

- Remove `black .` / `isort .` — ruff handles all formatting
- Remove `(or black + flake8 + isort)` parenthetical — ruff is the only linter/formatter
- Replace with `ruff format .` for formatting and `ruff check .` for linting
- Preserve `bandit -r src/` (security scanning, not related to formatter consolidation)
- Add a note that pre-push hooks automatically run: `ruff format`, `ruff check`, markdownlint,
  per-file 100% coverage, mypy, and test structure validation
- Add guidance: "If push is rejected by the pre-push hook, fix issues, amend commit, retry"

---

### 2. `.github/agents/copilot-instructions.md` (entire file)

Currently very sparse — only mentions `pytest` and `ruff check .` under Commands:

```bash
cd src
pytest
ruff check .
```

**Should update** (in the `<!-- MANUAL ADDITIONS -->` section or restructured):

- Remove `cd src` — commands run from the repo root (where `pyproject.toml` lives)
- Replace `pytest` with `agdt-test` / `agdt-task-wait` as the canonical test commands
- Mention that pre-push hooks enforce: `ruff format`, `ruff check`, markdownlint, per-file 100%
  test coverage, mypy
- The 4-tier CI pipeline with 3 PR-blocking gates: `Targeted Checks ✅`, `Smart Module Tests ✅`,
  `Copilot Review ✅` (plus `Post-Merge Full Suite` as non-blocking post-merge)
- That `ruff format .` is the formatter (not black)
- That agents working on this repo don't need to manually lint/format before push — the hook
  does it automatically

---

### 3. `.github/prompts/agdt.address-copilot-review.ci-repair.prompt.md`

The CI failure handling section (Phase 3b, lines 133–170) should be updated to:

- Add an introductory note at the top of Phase 3b listing the 3 PR gate names and what each covers:
  - `Targeted Checks ✅` — ruff format, ruff check, markdownlint, per-file coverage, mypy, test structure
  - `Smart Module Tests ✅` — smart module-level test execution
  - `Copilot Review ✅` — automated Copilot code review gate
- Note that most lint/format issues are now caught pre-push (so CI lint failures are less
  common — may indicate the hook was bypassed with `--no-verify`)

---

### 4. `.github/prompts/agdt.address-copilot-review.evaluate-and-respond.prompt.md`

The CI Failures section (Phase 5, lines 186–215) should:

- Add an introductory note at the top of Phase 5 listing the 3 PR gate names and what each covers
  (same structure as file 3 above)
- Note that lint failures reaching CI likely mean the pre-push hook was bypassed with
  `--no-verify`

---

## NOT in scope

- **Jira workflow agents** (`agdt.work-on-jira-issue.*`) — these operate on target repos that
  don't have agentic-devtools' hooks; their existing verification steps are correct
- **Generic `agdt.git-*` agent files** — these are toolkit commands used across repos
- **`agdt.test*` agent files** — generic test-running toolkit, not repo-specific

## User Scenarios & Testing

### User Story 1 - Agent Consulting Contribution Docs (Priority: P1)

As an AI agent (or human contributor) working on a PR in this repository, when I consult the
senior-python-developer guidelines or copilot-instructions.md, I expect to find accurate, current
guidance so that I can format, lint, and push code correctly without manual trial-and-error.

**Acceptance Scenarios**:

1. **Given** I read `senior-python-developer.md`, **When** I follow its tooling guidance,
   **Then** I use only `ruff` (not `black`/`isort`/`flake8`) and know that `ruff format .`
   handles formatting.

2. **Given** my push is rejected by the pre-push hook, **When** I consult the docs,
   **Then** I find explicit guidance to fix the issue, amend my commit, and retry the push.

3. **Given** I read `copilot-instructions.md`, **When** I look for CI gate information,
   **Then** I can identify the 3 PR-blocking CI gate names (`Targeted Checks ✅`,
   `Smart Module Tests ✅`, `Copilot Review ✅`) and know what each gate covers.

4. **Given** I read `copilot-instructions.md`, **When** I look for test commands,
   **Then** I find `agdt-test` / `agdt-task-wait` as the canonical way to run tests (not bare `pytest`).

### User Story 2 - Agent Handling CI Failures (Priority: P1)

As an AI agent repairing a CI failure on a PR, when I consult the ci-repair or
evaluate-and-respond prompt, I expect the gate names referenced there to match what I see in the
GitHub Actions UI so I can correctly identify which tier failed.

**Acceptance Scenarios**:

1. **Given** a CI failure in the `Targeted Checks ✅` gate, **When** I consult the ci-repair
   prompt, **Then** the gate name I read matches the actual CI check name in GitHub Actions.

2. **Given** a lint-related CI failure, **When** I consult the repair prompt, **Then** it
   advises me to check whether the pre-push hook was bypassed with `--no-verify`.

### User Story 3 - Contributor Onboarding (Priority: P2)

As a new contributor to this repository, when I read the contribution docs, I expect them to
describe the automated quality gates accurately so that I understand what will happen when I push
code.

**Acceptance Scenarios**:

1. **Given** I review `copilot-instructions.md`, **When** I push code, **Then** the behaviour
   I experience (pre-push hook running `ruff format`, `ruff check`, markdownlint, mypy,
   per-file coverage) matches what the docs describe.

## Requirements

### Functional Requirements

- **FR-001**: `senior-python-developer.md` MUST reference only `ruff` for formatting and linting,
  removing all mentions of `black`, `isort`, and the `(or black + flake8 + isort)` parenthetical.
  The `bandit -r src/` security check line MUST be preserved.

- **FR-002**: `senior-python-developer.md` MUST document that pre-push hooks automatically run
  `ruff format`, `ruff check`, markdownlint, per-file 100% coverage, mypy, and test structure
  validation, and MUST include the guidance "If push is rejected by the pre-push hook, fix issues,
  amend commit, retry".

- **FR-003**: `copilot-instructions.md` MUST document the 3 PR-blocking CI gate names
  (`Targeted Checks ✅`, `Smart Module Tests ✅`, `Copilot Review ✅`) and the pre-push hook
  automation, MUST state that `ruff format .` is the formatter (not black), MUST replace `pytest`
  with `agdt-test` / `agdt-task-wait` as the canonical test commands, and MUST remove the
  incorrect `cd src` instruction.

- **FR-004**: `agdt.address-copilot-review.ci-repair.prompt.md` MUST include an introductory
  note at the top of Phase 3b listing the 3 CI gate names and what each covers, and MUST note
  that lint failures reaching CI may indicate the pre-push hook was bypassed with `--no-verify`.

- **FR-005**: `agdt.address-copilot-review.evaluate-and-respond.prompt.md` MUST include an
  introductory note at the top of Phase 5 listing the 3 CI gate names and what each covers, and
  MUST note that lint failures reaching CI likely mean the pre-push hook was bypassed.

### Non-Functional Requirements

- **NFR-001**: All updated files MUST remain valid Markdown passing markdownlint rules enforced in
  this repository (zero warnings from `markdownlint-cli2`).

- **NFR-002**: Changes MUST NOT modify any Jira workflow agent files, generic `agdt.git-*` files,
  or `agdt.test*` files (as documented in the "NOT in scope" section above).

## Success Criteria

- **SC-001**: `senior-python-developer.md` contains no references to `black`, `isort`, or `flake8`
  as tooling recommendations after the change, while retaining the `bandit` security check.

- **SC-002**: `copilot-instructions.md` explicitly names all three PR-blocking CI gates, describes
  the pre-push hook automation, uses `agdt-test` as the canonical test command, and does not
  include `cd src`.

- **SC-003**: Both CI-repair prompt files (`ci-repair` and `evaluate-and-respond`) include a
  gate name summary at the top of their CI failure phase and use the correct gate names matching
  the actual GitHub Actions check names (`Targeted Checks ✅`, `Smart Module Tests ✅`,
  `Copilot Review ✅`).

- **SC-004**: All four updated files pass markdownlint without warnings.

---
*Generated by Copilot SDK (claude-opus-4.6) — enriched from issue #1657*
