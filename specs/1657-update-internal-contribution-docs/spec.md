# Feature Specification: Update internal contribution docs and prompts for automated validation (4-tier CI, pre-push hooks)

> ⚠️ **FALLBACK SKELETON** — This specification was generated via deterministic fallback after all LLM retry attempts were exhausted. It requires manual enrichment. Review each section and replace
> placeholder content with detailed, issue-specific information.

**Source Issue**: #1657 (<https://github.com/ayaiayorg/agentic-devtools/issues/1657>)

## Problem Statement

## Context

With the 4-tier CI pipeline merged (PR #1650) and pre-push hooks now enforcing code quality automatically, several internal docs and agentic-devtools-only prompts still reference outdated manual
validation instructions or old tooling.

---

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
Remove `black .` / `isort .` — ruff handles all formatting
Remove `(or black + flake8 + isort)` parenthetical — ruff is the only linter/formatter
Add a note that pre-push hooks automatically run: `ruff format`, `ruff check`, markdownlint, per-file 100% coverage, mypy, and test structure validation
Add guidance: "If push is rejected by the pre-push hook, fix issues, amend commit, retry"

---

### 2. `.github/agents/copilot-instructions.md` (entire file)

Currently very sparse — only mentions `pytest` and `ruff check .` under Commands:

```bash
cd src
pytest
ruff check .
```

**Should add** (in the `<!-- MANUAL ADDITIONS -->` section or restructured):
Mention that pre-push hooks enforce: ruff format, ruff check, markdownlint, per-file 100% test coverage, mypy
The 4-tier CI gate n

The implementation of this feature will improve the overall system reliability and reduce the operational burden on development teams. Without this change, the existing workarounds will continue to
consume developer time and introduce potential for human error.

## User Scenarios & Testing

### User Story 1 - Primary Workflow (Priority: P1)

As a developer working with the system, I expect the update internal contribution docs and prompts for automated validation (4-tier ci, pre-push hooks) feature to work correctly on standard inputs
without requiring manual intervention.

**Acceptance Scenarios**:

1. **Given** a standard input meeting all preconditions, **When** the system processes it, **Then** the output meets all quality checks and completes within the expected time bounds.

2. **Given** an input that previously caused failures, **When** processed with the improved logic, **Then** the success rate exceeds 90% over repeated runs.

### User Story 2 - Error Recovery (Priority: P1)

As a developer whose operation encounters a transient failure, I expect the system to recover gracefully and complete the operation without manual intervention.

**Acceptance Scenarios**:

1. **Given** a first attempt that fails due to a transient issue, **When** the retry mechanism activates, **Then** the second attempt succeeds with enriched context.

2. **Given** a specific validation failure reason, **When** retry feedback is generated, **Then** the feedback addresses the exact failure with actionable guidance.

### User Story 3 - Graceful Degradation (Priority: P2)

As a developer whose operation has exhausted all retry attempts, I expect the system to provide a usable fallback output rather than failing completely.

**Acceptance Scenarios**:

1. **Given** all retry attempts have been exhausted, **When** the fallback mechanism activates, **Then** a structurally valid output is produced that allows the workflow to proceed.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST implement acceptance capability as described in the feature requirements, ensuring correct behavior under normal operating conditions and providing appropriate error
  handling for edge cases.

- **FR-002**: The system MUST implement additions capability as described in the feature requirements, ensuring correct behavior under normal operating conditions and providing appropriate error
  handling for edge cases.

- **FR-003**: The system MUST implement address capability as described in the feature requirements, ensuring correct behavior under normal operating conditions and providing appropriate error
  handling for edge cases.

- **FR-004**: The system MUST implement agent capability as described in the feature requirements, ensuring correct behavior under normal operating conditions and providing appropriate error handling
  for edge cases.

- **FR-005**: The system MUST implement agentic capability as described in the feature requirements, ensuring correct behavior under normal operating conditions and providing appropriate error
  handling for edge cases.

### Non-Functional Requirements

- **NFR-001**: The implementation must complete all operations within 120 seconds under normal conditions.

- **NFR-002**: The implementation must maintain backward compatibility with existing interfaces and contracts.

## Success Criteria

- **SC-001**: The feature achieves at least 90% success rate on standard inputs measured over a representative sample of 20+ test cases.

- **SC-002**: Zero critical failures occur during the first 2 weeks of deployment, measured by monitoring error rates in CI logs.

- **SC-003**: Average processing time remains under 30 seconds for standard inputs, with worst-case time under 120 seconds including retries.

---
*Generated via fallback skeleton — manual enrichment required*

---
*Generated by Copilot SDK (claude-opus-4.6)*
