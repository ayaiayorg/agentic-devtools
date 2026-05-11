# Spec: Extract workflow logic from YAML to agentic-devtools library with CI-provider abstraction

**Feature Branch**: `speckit/1400/phase-1-specify`
**Created**: 2026-05-11
**Status**: Draft
**Source Issue**: #1400

## Problem Statement

Today ~800 lines of inline JavaScript in `ai-pr-loop.yml` largely duplicate
existing Python functions in `agentic_devtools/cli/github/`, while the adapter
layer only covers issue CRUD — no PR/label/review abstraction exists yet. This
creates several problems:

- **Untestability**: Inline CI logic cannot be unit tested without pushing to CI.
- **Duplication**: Python equivalents already exist but are unused by workflows.
- **Vendor lock-in**: All orchestration is tightly coupled to GitHub Actions.
- **Fragility**: ~800 lines of embedded JS is the most frequently broken code.

## Summary

Extract all complex orchestration, PR/issue/label state management, and
comment/guard logic from workflow YAML files into the agentic-devtools Python
library behind a CI-platform provider abstraction.

## User Scenarios & Testing

### User Story 1 — CI-platform provider interface (Priority: P1)

As a library maintainer, I want a `CIPlatformProvider` interface that abstracts
CI-specific operations (event parsing, PR metadata, check status, comment
posting) so that orchestration logic is decoupled from any single CI system.

**Why this priority**: Foundation for all other stories; nothing can be extracted
without a provider contract.

**Independent Test**: Implement the interface with a mock provider and verify
all method contracts are exercisable in isolation.

**Acceptance Scenarios**:

1. **Given** the `CIPlatformProvider` ABC is defined, **When** a concrete
   provider (GitHub Actions) implements all abstract methods, **Then** the
   implementation passes type-checking and a basic integration smoke test.
2. **Given** the interface exists, **When** an Azure DevOps provider is stubbed,
   **Then** it compiles and satisfies the same ABC contract without changes to
   orchestration code.

### User Story 2 — GitHub Actions provider (Priority: P1)

As an AI agent running in GitHub Actions, I want a GitHub Actions provider
implementation so that existing workflow logic can delegate to it without
changing observable behavior.

**Why this priority**: GitHub Actions is the primary CI system today; the
provider must exist before any orchestration extraction.

**Independent Test**: Run the provider against recorded webhook payloads and
assert identical outputs to current inline JS logic.

**Acceptance Scenarios**:

1. **Given** a `pull_request_review` event payload, **When** the provider
   resolves PR metadata, **Then** it returns the same `prNumber`, `headBranch`,
   and `headSha` as the current inline JS.
2. **Given** a label event, **When** the provider parses the trigger label,
   **Then** it matches the output of the current shell validation script.

### User Story 3 — PR loop orchestrator extraction (Priority: P1)

As a developer, I want the AI PR loop orchestration logic moved into a testable
Python module so that changes to the loop can be validated without pushing to CI.

**Why this priority**: The PR loop is the highest-value extraction target —
largest codebase, most fragile, and most frequently modified.

**Independent Test**: Execute the orchestrator module with mocked provider
responses and verify state transitions, comment posting, and merge-gate logic.

**Acceptance Scenarios**:

1. **Given** a PR in "ready for review" state, **When** the orchestrator runs,
   **Then** it produces the same sequence of API calls as the current YAML.
2. **Given** a PR failing CI checks, **When** the orchestrator evaluates merge
   readiness, **Then** it blocks the merge and posts the correct status comment.

### User Story 4 — SpecKit trigger extraction (Priority: P2)

As a workflow maintainer, I want SpecKit label-trigger and phase-transition logic
extracted to a Python module so it can be unit tested and reused across providers.

**Why this priority**: Second-largest block of embedded logic; high change
frequency.

**Independent Test**: Invoke the trigger module with synthetic label events and
validate phase advancement and error handling.

**Acceptance Scenarios**:

1. **Given** a valid speckit label event, **When** the trigger module processes
   it, **Then** it initiates the correct speckit phase.
2. **Given** a duplicate trigger event, **When** the deduplication guard runs,
   **Then** it skips processing and logs the reason.

### User Story 5 — YAML minimization (Priority: P2)

As a CI engineer, I want workflow YAML reduced to triggers, permissions, and a
single `agdt <command>` CLI invocation so files are easy to read and maintain.

**Why this priority**: Delivers the ergonomic and maintainability benefit of the
entire refactor.

**Independent Test**: Diff a minimized YAML against the current one and verify
all behavioral paths are preserved via end-to-end smoke tests.

**Acceptance Scenarios**:

1. **Given** the extracted orchestrator and provider exist, **When** the YAML is
   reduced to a CLI invocation, **Then** CI behavior remains identical.

### User Story 6 — Azure DevOps provider (Priority: P3)

As a team using Azure DevOps, I want a provider implementation so workflows can
run on ADO pipelines without logic duplication.

**Why this priority**: Stretch goal; validates the abstraction but not required
for MVP.

**Independent Test**: Implement the provider against ADO REST API mocks and run
the same orchestrator integration tests.

**Acceptance Scenarios**:

1. **Given** an ADO pipeline trigger, **When** the provider resolves PR
   metadata, **Then** it returns equivalent data to the GitHub provider.

### Edge Cases

- What happens when the CI event payload is malformed or missing expected fields?
- How does the system handle provider API rate limits during orchestration?
- What if a PR has no linked issue (required for commit conventions)?

## Requirements

### Functional Requirements

- **FR-001**: System MUST define a `CIPlatformProvider` abstract interface
  covering event parsing, PR metadata, check-status queries, and comment posting.
- **FR-002**: System MUST implement a GitHub Actions provider satisfying the
  `CIPlatformProvider` contract.
- **FR-003**: System MUST extract the AI PR loop orchestration logic into a
  testable Python module that delegates to a provider instance.
- **FR-004**: System MUST preserve all existing safety/security semantics
  (privileged-path guards, deduplication, review/merge conditions).
- **FR-005**: System MUST expose a CLI entry point (e.g., `agdt-ai-pr-loop`)
  for invoking the orchestrator.
- **FR-006**: System MUST extract SpecKit trigger logic into a reusable module.
- **FR-007**: System MUST use [NEEDS CLARIFICATION] (template engine — Jinja2
  vs. Python string formatting) for comment/notification rendering.
- **FR-008**: Minimized workflow YAML files MUST contain only triggers,
  permissions, and a single CLI invocation.

### Non-Functional Requirements

- **NFR-001**: Extracted modules MUST achieve ≥95% unit test coverage.
- **NFR-002**: Orchestration latency MUST NOT increase by more than 500ms
  compared to current inline execution.
- **NFR-003**: All provider implementations MUST handle API errors gracefully
  with retry-after logic.
- **NFR-004**: CLI commands MUST follow existing `agdt-*` naming and background
  task conventions.

### Key Entities

- **CIPlatformProvider**: Abstract interface for CI system interactions.
- **GitHubActionsProvider**: Concrete implementation for GitHub Actions.
- **Orchestrator**: Stateless module coordinating provider calls for a workflow.
- **EventPayload**: Normalized event data parsed by [NEEDS CLARIFICATION]
  (event payload parsing ownership — provider vs. orchestrator).

## Success Criteria

### Measurable Outcomes

- **SC-001**: All orchestration logic currently in `ai-pr-loop.yml` inline JS
  is covered by unit tests in the Python library.
- **SC-002**: `ai-pr-loop.yml` is reduced to ≤50 lines (triggers, permissions,
  CLI call).
- **SC-003**: A new provider implementation (e.g., Azure DevOps) can be added
  without modifying orchestration modules.
- **SC-004**: End-to-end CI behavior remains identical as verified by
  [NEEDS CLARIFICATION] (availability of production event logs for integration
  test scenarios).

---

*Generated by Copilot SDK (claude-opus-4.6)*
