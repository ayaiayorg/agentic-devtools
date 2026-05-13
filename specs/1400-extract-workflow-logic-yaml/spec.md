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

## Clarifications

### Session 2026-05-11

- Q: Should comment/notification rendering use Jinja2 or Python string formatting (FR-007)? → A: Use the existing `substitute_variables()` function from `agentic_devtools/prompts/loader.py`,
  which renders `{{variable}}` placeholders via Jinja2 (with a regex-based fallback on `TemplateSyntaxError`). This maintains consistency with all other prompt/template rendering in the codebase.
- Q: Who owns event payload parsing — the provider or the orchestrator (EventPayload entity)? → A: The provider owns raw event parsing. Each `CIPlatformProvider` implementation MUST parse its
  platform-specific event format (e.g., GitHub webhook JSON, ADO service hook JSON) and return a normalized `EventPayload` dataclass. The orchestrator only consumes the normalized dataclass.
- Q: How should end-to-end CI behavior equivalence be verified (SC-004) given production event logs may not be available? → A: Use recorded/synthetic webhook payloads committed as test fixtures under
  `tests/fixtures/ci_events/`. Capture representative payloads from each supported event type (`pull_request`, `pull_request_review`, `issues` with `action="labeled"`,
  `workflow_run`) during development. Production event logs are
  NOT required; golden-file fixtures provide deterministic, reproducible verification.
- Q: What should the system do when a CI event payload is malformed or missing expected fields? → A: The provider MUST raise a `MalformedEventError` (custom exception inheriting from `ValueError`)
  with a descriptive message identifying the missing/invalid fields. The orchestrator MUST catch this and exit with a non-zero exit code and structured JSON error output to stderr. The workflow MUST
  NOT silently proceed with partial data.
- Q: How should provider API rate limits be handled during orchestration? → A: Providers MUST implement exponential backoff with jitter, starting at 1 second, capping at 60 seconds, with a maximum of
  5 retries per API call. Rate-limit responses (HTTP 429, 403 with `retry-after`) MUST be detected and the `Retry-After` header honored when present. After max retries, the provider MUST raise a
  `ProviderRateLimitError` with the remaining reset time.

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

**Independent Test**: Run the provider against recorded webhook payloads
(committed as test fixtures under `tests/fixtures/ci_events/`) and assert
identical outputs to current inline JS logic.

**Acceptance Scenarios**:

1. **Given** a `pull_request_review` event payload, **When** the provider
   resolves PR metadata, **Then** it returns the same `pr_number`, `head_branch`,
   and `head_sha` values as the current inline JS.
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
single `agdt-<workflow>` CLI invocation (e.g., `agdt-ai-pr-loop`) so files are
easy to read and maintain.

**Why this priority**: Delivers the ergonomic and maintainability benefit of the
entire refactor.

**Independent Test**: Diff a minimized YAML against the current one and verify
all behavioral paths are preserved via end-to-end smoke tests.

**Acceptance Scenarios**:

1. **Given** the extracted orchestrator and provider exist, **When** the YAML is
   reduced to a CLI invocation, **Then** CI behavior remains identical.
2. **Given** the `agdt-ai-pr-loop` CLI entry point is missing or not installed,
   **When** the minimized YAML workflow runs, **Then** the workflow MUST fail
   with a clear error message indicating the missing binary (non-zero exit code
   within 5s).

### User Story 6 — Azure DevOps provider (Priority: P3)

As a team using Azure DevOps, I want a provider implementation so workflows can
run on ADO pipelines without logic duplication.

**Why this priority**: Stretch goal; validates the abstraction but not required
for MVP.

**Independent Test**: Implement the provider against ADO REST API mocks and run
the same orchestrator integration tests.

**Acceptance Scenarios**:

1. **Given** an ADO pipeline trigger, **When** the provider resolves PR
   metadata, **Then** it returns an `EventPayload` containing the same fields
   as the GitHub provider: `pr_number` (int), `head_branch` (str), `head_sha`
   (str, 40-char hex), `base_branch` (str), `action` (str), `trigger_label`
   (Optional[str]), and `repository_full_name` (str, `owner/repo` format).
   Field names are snake_case per codebase convention; camelCase is strictly
   a JSON serialization/input concern handled by the mapping layer.

### Edge Cases

- **Malformed event payload**: When the CI event payload is malformed or missing
  expected fields, the provider MUST raise a `MalformedEventError` with a
  descriptive message. The orchestrator catches this, emits structured JSON
  error output to stderr, and exits with a non-zero exit code. The workflow
  MUST NOT silently proceed with partial data.
- **API rate limits**: Providers MUST implement exponential backoff with jitter
  (1s initial, 60s cap, 5 retries max). Rate-limit responses (HTTP 429, 403
  with `retry-after`) are detected and the `Retry-After` header is honored.
  After max retries, a `ProviderRateLimitError` is raised with the remaining
  reset time.
- **PR with no linked issue**: When a PR has no linked issue (required for
  commit conventions), the orchestrator MUST log a warning and continue
  processing. The missing issue link MUST be surfaced in the PR status comment
  as a non-blocking advisory, since the CI workflow itself does not enforce
  commit conventions — that is a separate pre-merge check.

## Requirements

### Functional Requirements

- **FR-001**: System MUST define a `CIPlatformProvider` abstract interface
  covering event parsing, PR metadata, check-status queries, and comment posting.
  The interface MUST include a
  `parse_event(raw_payload: dict, event_name: str) -> EventPayload` method
  that accepts the raw platform-specific payload and the event type name
  (e.g., `"pull_request"`, `"pull_request_review"`, `"issues"`), returns a
  normalized `EventPayload` dataclass on success, or raises
  `MalformedEventError` when the payload is missing required fields or
  structurally invalid.
- **FR-002**: System MUST implement a GitHub Actions provider satisfying the
  `CIPlatformProvider` contract.
- **FR-003**: System MUST extract the AI PR loop orchestration logic into a
  testable Python module that delegates to a provider instance.
- **FR-004**: System MUST preserve all existing safety/security semantics.
  Specifically, the following guards MUST be retained:
  - **Privileged-path guard**: Reject automated PR merges when diffs touch
    protected paths — specifically `.github/workflows/`, `.github/actions/`,
    and `.github/scripts/` (excluding `*.md` files within those directories).
    Changes to these paths require explicit human approval.
  - **Docker-file guard**: Force human intervention when diffs modify
    `Dockerfile`, `Dockerfile.*` (multi-stage variants), `docker-compose.yml`,
    `docker-compose.yaml`, or `.dockerignore` files, since container definition
    and build-context changes carry deployment risk that automated review
    cannot fully assess. **Note**: The `Dockerfile.*` and `.dockerignore`
    patterns are an intentional safety hardening beyond the current
    `ai-pr-loop.yml` guard scope; this is a documented exception to SC-004's
    "identical behavior" criterion (see SC-004 exception clause below).
  - **Exclusion-label guard**: Skip PR processing entirely when the PR carries
    the `ai-pr-loop-ignore` label. When the `do-not-auto-merge` label is
    present, continue review but block the automated merge step.
  - **Fork-PR guard**: Skip automated processing when the PR head repository
    differs from the base repository (fork PRs), since fork PRs do not have
    access to repository secrets required for CI operations.
  - **Cycle-limit guard**: Halt automated processing when the PR loop iteration
    count (tracked via a `<!-- ai-pr-loop-cycle-tracker -->` marker comment)
    exceeds `MAX_CYCLE_LIMIT` (default: 50) to prevent runaway automation.
  - **Deduplication guard**: Skip processing when the same PR head SHA has
    already been processed up to `MAX_DISPATCHES_PER_SHA` times (default: 3).
    Deduplication is tracked via a marker comment posted per `head_sha` on the
    PR — there is no time-based expiry window.
  - **Review condition**: Block merge unless the required number of approving
    reviews is met and no "changes requested" reviews are outstanding.
  - **Merge condition**: Block merge unless all required status checks report
    success and the branch is up-to-date with the base branch.
- **FR-005**: System MUST expose a CLI entry point (e.g., `agdt-ai-pr-loop`)
  for invoking the orchestrator.
- **FR-006**: System MUST extract SpecKit trigger logic into a reusable module.
- **FR-007**: System MUST use the existing `substitute_variables()` function
  (from `agentic_devtools/prompts/loader.py`) for comment/notification rendering.
  This renders `{{variable}}` placeholders via Jinja2 with a regex-based fallback
  on `TemplateSyntaxError`.
- **FR-008**: Minimized workflow YAML files MUST contain only triggers,
  permissions, and a single `agdt-<workflow>` CLI invocation (e.g.,
  `agdt-ai-pr-loop`). Line-count targets:
  - `ai-pr-loop.yml`: ≤50 lines (see SC-002).
  - All other affected workflow YAMLs (e.g., SpecKit trigger workflows): ≤30
    lines each, since they have fewer trigger/permission combinations.
- **FR-009**: System MUST extract lint patch handling into a reusable module
  (`patch_handler.py`) that downloads, validates, and applies lint-fix patches
  generated by CI check annotations. The module MUST:
  - Download patch content from check-run annotation URLs via the provider.
  - Validate patch integrity (non-empty, applies cleanly to the working tree).
  - Apply the patch and stage the resulting changes.
  - Raise a descriptive error if download fails or the patch does not apply
    cleanly.

### Non-Functional Requirements

- **NFR-001**: Extracted modules MUST achieve 100% unit test coverage.
- **NFR-002**: Orchestration latency MUST NOT increase by more than 500ms
  compared to current inline execution. Measurement methodology:
  - **Baseline**: Record wall-clock time from workflow step start to first
    provider API call in the current inline JS implementation, averaged over
    10 consecutive runs on the same runner class.
  - **Measurement**: Record the same interval in the Python orchestrator using
    `time.perf_counter()` around the orchestrator entry point, averaged over
    10 runs with identical fixture payloads.
  - **Tooling**: A `scripts/measure-orchestrator-latency.py` benchmark script
    MUST be provided that runs both measurements and reports the delta.
  - **Threshold**: The average delta (Python − baseline) MUST be ≤500ms.
- **NFR-003**: All provider implementations MUST handle API errors gracefully
  with exponential backoff and jitter (1s initial delay, 60s cap, max 5
  retries). Rate-limit responses (HTTP 429, 403 with `Retry-After`) MUST
  honor the `Retry-After` header. After max retries, providers MUST raise
  `ProviderRateLimitError`.
- **NFR-004**: CLI commands MUST follow existing `agdt-*` naming and background
  task conventions. **Exception**: CLI commands invoked as CI workflow steps
  (e.g., `agdt-ai-pr-loop`) MUST execute synchronously (not as background
  tasks) so that the CI step blocks until completion and returns the correct
  exit code to the workflow runner.

### Key Entities

- **CIPlatformProvider**: Abstract interface for CI system interactions.
- **GitHubActionsProvider**: Concrete implementation for GitHub Actions.
- **Orchestrator**: Stateless module coordinating provider calls for a workflow.
- **EventPayload**: Normalized event dataclass produced exclusively by the
  provider's `parse_event()` method. The orchestrator consumes this dataclass
  but never parses raw platform-specific event data directly.
- **MalformedEventError**: Custom exception (inherits `ValueError`) raised by
  providers when event payloads are missing required fields or structurally
  invalid.
- **ProviderRateLimitError**: Custom exception raised after exhausting retry
  attempts due to API rate limiting.

### Implementation Dependencies

- **FR-001 → FR-002, FR-003**: The provider interface (FR-001) MUST be
  implemented and stabilized before the GitHub Actions provider (FR-002) and
  orchestrator extraction (FR-003) can begin, since both depend on the abstract
  contract.
- **FR-002 → FR-003**: The GitHub Actions provider MUST be complete before
  orchestrator extraction, since the orchestrator's integration tests require
  a concrete provider.
- **FR-003 → FR-005, FR-008**: The orchestrator module MUST exist before the
  CLI entry point (FR-005) and YAML minimization (FR-008) can be implemented.
- **FR-006** (SpecKit trigger): Independent of FR-001–FR-003; can proceed in
  parallel once the provider interface shape is agreed.

### Migration & Rollback Strategy

- **Parallel operation**: During migration, both the inline JS and the Python
  orchestrator will coexist. A feature flag (`AGDT_USE_PYTHON_ORCHESTRATOR=1`)
  in the workflow YAML selects which path executes.
- **Incremental migration**: Individual workflow concerns (event parsing,
  comment posting, merge-gate evaluation) are migrated one at a time, each
  behind the feature flag, with CI verification at each step.
- **Rollback**: Removing or unsetting the feature flag immediately reverts to
  the inline JS path. No data migration is required since the orchestrator is
  stateless.
- **Cutover**: Once all integration tests pass with the Python path for 2
  consecutive weeks on the default branch, the inline JS is removed and the
  feature flag is deleted.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All orchestration logic currently in `ai-pr-loop.yml` inline JS
  is covered by unit tests in the Python library.
- **SC-002**: `ai-pr-loop.yml` is reduced to ≤50 lines (triggers, permissions,
  CLI call).
- **SC-003**: A new provider implementation (e.g., Azure DevOps) can be added
  without modifying orchestration modules.
- **SC-004**: End-to-end CI behavior remains identical as verified by golden-file
  test fixtures (recorded/synthetic webhook payloads committed under
  `tests/fixtures/ci_events/`) covering all supported event types
  (`pull_request`, `pull_request_review`, `issues` with `action="labeled"`, `workflow_run`).
  **Exception**: The Docker-file guard expansion (`Dockerfile.*`,
  `.dockerignore`) is an intentional safety hardening that constitutes a
  documented, net-positive deviation from the current inline JS behavior.
  Golden-file tests for PRs touching these additional patterns MUST verify
  the new (stricter) guard behavior rather than replicating the old (narrower)
  scope.

---

*Generated by Copilot SDK (claude-opus-4.6)*
