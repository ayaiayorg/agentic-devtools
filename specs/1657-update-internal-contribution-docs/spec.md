# Feature Specification: Update internal contribution docs and prompts for automated validation (4-tier CI, pre-push hooks)

**Source Issue**: #1657 (<https://github.com/ayaiayorg/agentic-devtools/issues/1657>)

## Problem Statement

With the 4-tier CI pipeline merged (PR #1650) and pre-push hooks now enforcing code quality
automatically, several internal docs and agentic-devtools-only prompts still reference outdated
manual validation instructions or old tooling (e.g., `black`, `isort`, `flake8`). The 4-tier CI
gate names (`Targeted Checks ✅`, `Smart Module Tests ✅`, `Copilot Review ✅`) are not documented
anywhere contributors or agents can easily reference them, and the pre-push hook automation is not
mentioned in contribution guidance at all.

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

**Should add** (in the `<!-- MANUAL ADDITIONS -->` section or restructured):

- Mention that pre-push hooks enforce: `ruff format`, `ruff check`, markdownlint, per-file 100%
  test coverage, mypy
- The 4-tier CI gate names: `Targeted Checks ✅`, `Smart Module Tests ✅`, `Copilot Review ✅`
- That `ruff format .` is the formatter (not black)
- That agents working on this repo don't need to manually lint/format before push — the hook
  does it automatically

---

### 3. `.github/prompts/agdt.address-copilot-review.ci-repair.prompt.md`

The CI failure handling section (lines 138–170) should be updated to:

- Reference the new CI gate names (`Targeted Checks ✅`, `Smart Module Tests ✅`,
  `Copilot Review ✅`) instead of generic "check-name"
- Note that most lint/format issues are now caught pre-push (so CI lint failures are less
  common — may indicate the hook was bypassed with `--no-verify`)

---

### 4. `.github/prompts/agdt.address-copilot-review.evaluate-and-respond.prompt.md`

The CI Failures section (Phase 5, lines 188–215) should:

- Reference correct gate names (`Targeted Checks ✅`, `Smart Module Tests ✅`,
  `Copilot Review ✅`)
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
   **Then** I can identify the 4-tier CI gate names (`Targeted Checks ✅`,
   `Smart Module Tests ✅`, `Copilot Review ✅`) and know what each gate covers.

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

- **FR-002**: `senior-python-developer.md` MUST document that pre-push hooks automatically run
  `ruff format`, `ruff check`, markdownlint, per-file 100% coverage, mypy, and test structure
  validation, and MUST include the guidance "If push is rejected by the pre-push hook, fix issues,
  amend commit, retry".

- **FR-003**: `copilot-instructions.md` MUST document the 4-tier CI gate names
  (`Targeted Checks ✅`, `Smart Module Tests ✅`, `Copilot Review ✅`) and the pre-push hook
  automation, and MUST state that `ruff format .` is the formatter (not black).

- **FR-004**: `agdt.address-copilot-review.ci-repair.prompt.md` MUST reference the correct CI
  gate names and MUST note that lint failures reaching CI may indicate the pre-push hook was
  bypassed with `--no-verify`.

- **FR-005**: `agdt.address-copilot-review.evaluate-and-respond.prompt.md` MUST reference the
  correct CI gate names and MUST note that lint failures reaching CI likely mean the pre-push hook
  was bypassed.

### Non-Functional Requirements

- **NFR-001**: All updated files MUST remain valid Markdown passing markdownlint rules enforced in
  this repository.

- **NFR-002**: Changes MUST NOT modify any Jira workflow agent files, generic `agdt.git-*` files,
  or `agdt.test*` files (as documented in the "NOT in scope" section above).

## Success Criteria

- **SC-001**: `senior-python-developer.md` contains no references to `black`, `isort`, or `flake8`
  as tooling recommendations after the change.

- **SC-002**: `copilot-instructions.md` explicitly names all three CI gates and describes the
  pre-push hook automation.

- **SC-003**: Both CI-repair prompt files (`ci-repair` and `evaluate-and-respond`) use the correct
  gate names matching the actual GitHub Actions check names.

- **SC-004**: All four updated files pass markdownlint without warnings.

---
*Generated by Copilot SDK (claude-opus-4.6) — enriched from issue #1657*
