# Feature Specification: AI PR Loop Orchestrator Log Visibility

**Feature Branch**: `speckit/1577/phase-1-specify`  
**Created**: 2026-05-26  
**Status**: Draft  
**Input**: User description: "Logs not visible in AI PR loop orchestrator workflow"  
**Source Issue**: #1577 (<https://github.com/ayaiayorg/agentic-devtools/issues/1577>)

## Clarifications

### Session 2026-05-26

- Q: Where should the `setup_logging()` function live — in `commands.py` itself or in a dedicated `logging_config.py` module? → A: A dedicated module (`agentic_devtools/cli/ci/logging_config.py`)
  following the existing package structure pattern where concerns are separated into distinct modules (e.g., `config.py`, `auth.py`, `helpers.py`). This allows reuse from both `ai_pr_loop_command()`
  and `speckit_trigger_command()` without duplication.
- Q: Should the `::group::`/`::endgroup::` annotations be emitted via the logging framework (custom formatter/handler) or remain as direct `print()` statements? → A: Via the logging subsystem, but not
  through the normal per-record log format string. Implement an explicit helper/context manager in `agentic_devtools/cli/ci/logging_config.py` that conditionally emits `::group::` and `::endgroup::`
  when `GITHUB_ACTIONS=="true"`, while ordinary log records continue to use the standard formatter. This keeps FR-003/FR-004 logs outside grouped verbose sections unless a caller deliberately wraps them.
- Q: How should subprocess output from `gh` CLI calls be handled — inherited via `subprocess.PIPE` and re-emitted through logging, or left as direct stderr/stdout inheritance? → A: Subprocess stderr
  should be captured and re-emitted through logging rather than inherited directly: use `logger.debug()` when the subprocess exits successfully to preserve diagnostic visibility without adding noise,
  but surface stderr at `logger.warning()` or `logger.error()` when the subprocess exits non-zero so failure details are visible in the step log at the default INFO level. Stdout (which may contain
  structured data) should be captured and processed programmatically. This avoids interleaving raw subprocess output with formatted log lines.
- Q: Should the logging setup be idempotent across multiple calls (e.g., if both a parent script and the entry point try to configure logging)? → A: Yes — the setup function must check
  `logging.root.handlers` before adding handlers. If handlers already exist, skip configuration entirely (as specified in the Edge Cases section). This matches the Python logging best practice of
  "configure once at the application boundary."
- Q: What log format string should be used — should it include the process ID or thread name for future multi-process scenarios? → A: No — use `%(asctime)s %(levelname)-8s %(name)s: %(message)s` with
  `datefmt="%H:%M:%S"`. The orchestrator is single-process/single-thread, so PID/thread adds noise. The `%(name)s` field (which renders as `agentic_devtools.cli.ci.guards` etc.) provides sufficient
  source identification.

## Problem Statement

The AI PR loop orchestrator (`agdt-ai-pr-loop`) uses Python's `logging` module extensively across 18+ modules (`orchestrator.py`, `guards.py`, `pipeline/command.py`, `pipeline/runner.py`, action
modules, evaluator modules, etc.), but the CLI entry point (`ai_pr_loop_command()` in `commands.py`) never configures a logging handler. Without explicit handler configuration, Python's root logger
defaults to WARNING level with no stream handler attached. This means all `logger.info()` calls are filtered out entirely, and any `logger.warning()` or `logger.error()` calls that do pass the level
check rely on the `lastResort` handler (a bare `StreamHandler(stderr)` with no formatter), producing output without timestamps or module names.

Additionally, the orchestrator emits `::group::` / `::endgroup::` annotations that collapse log sections in the GitHub Actions UI, further reducing visibility of diagnostic information during normal
operation.

The result is that developers cannot monitor or debug the orchestrator's decision-making process from the GitHub Actions job view. They must infer outcomes solely from exit codes and the sparse
`print()` statements that bypass the logging framework.

## User Scenarios & Testing

### User Story 1 - Visible Orchestrator Logs in Actions UI (Priority: P1)

As a developer monitoring a PR through the AI PR loop, I want to see structured log output from every orchestrated action (publish, request_review, resolve_threads, dispatch_repair, squash, approve,
merge) in the GitHub Actions job log, so that I can diagnose failures and understand the orchestrator's decisions without additional tooling.

**Why this priority**: This is the core problem. Without log visibility, the orchestrator is a black box in CI. Every other improvement depends on logs being emitted at all.

**Independent Test**: Can be fully tested by triggering the AI PR loop workflow and verifying that Python logging output appears in the Actions step log at INFO level and above.

**Acceptance Scenarios**:

1. **Given** the AI PR loop orchestrator is invoked in a GitHub Actions run, **When** the orchestrator processes an event through its state machine, **Then** all `logger.info()`, `logger.warning()`,
   and `logger.error()` messages from all CI modules are visible in the Actions step output.
2. **Given** the orchestrator is invoked locally (outside GitHub Actions), **When** a developer runs `agdt-ai-pr-loop` with valid event data, **Then** log output is emitted to stderr with
   timestamps and module names in the format `HH:MM:SS LEVEL    module.name: message`.
3. **Given** the logging configuration is applied, **When** the orchestrator encounters an error during metadata resolution or guard evaluation, **Then** the error details are visible in the step log
   without requiring users to download raw logs.

---

### User Story 2 - Expanded Log Groups for Key Actions (Priority: P2)

As a developer reviewing a failed AI PR loop run, I want critical action logs (guard decisions, repair dispatches, merge attempts) to be visible without manually expanding collapsed groups, so that I
can quickly identify the failure point.

**Why this priority**: Even with logging enabled, collapsed `::group::` sections hide important diagnostic details. Reducing unnecessary collapsing improves the out-of-the-box debugging experience.

**Independent Test**: Can be tested by triggering the workflow and verifying that critical action summaries (guard results, final decision) are visible outside of collapsed groups in the Actions UI.

**Acceptance Scenarios**:

1. **Given** the orchestrator evaluates guards (deduplication, exclusion labels, fork detection), **When** a guard blocks execution, **Then** the block reason is logged outside any collapsed group so
   it is immediately visible.
2. **Given** the orchestrator dispatches a repair or performs a merge, **When** the action completes, **Then** the action outcome (success/failure, exit code) is visible without expanding a group.
3. **Given** verbose internal details (full JSON payloads, API responses), **When** they are logged, **Then** they remain inside collapsed groups to avoid log noise.

---

### User Story 3 - Configurable Log Verbosity (Priority: P3)

As a repository maintainer, I want to control the log verbosity of the AI PR loop orchestrator via an environment variable, so that I can increase detail for debugging or reduce noise during normal
operation.

**Why this priority**: Different situations require different verbosity. A configuration knob provides flexibility without code changes, but the default INFO level satisfies most needs.

**Independent Test**: Can be tested by setting an environment variable (e.g., `AGDT_LOG_LEVEL=DEBUG`) in the workflow and verifying that debug-level messages appear in the output.

**Acceptance Scenarios**:

1. **Given** `AGDT_LOG_LEVEL` is set to `DEBUG` in the workflow environment, **When** the orchestrator runs, **Then** debug-level log messages (including internal state transitions) are emitted.
2. **Given** `AGDT_LOG_LEVEL` is not set, **When** the orchestrator runs, **Then** the default level is INFO and only info/warning/error messages appear.
3. **Given** `AGDT_LOG_LEVEL` is set to `WARNING`, **When** the orchestrator runs normally without issues, **Then** only warning and error messages appear, keeping the log minimal.

---

### Edge Cases

- What happens when logging configuration is called multiple times (e.g., if another entry point also configures logging)? The setup function MUST check whether the root logger already has handlers
  before adding a new one. If handlers are already present, it MUST skip configuration to avoid duplicate output. This explicit check serves two purposes: (1) it prevents duplicate handlers from
  being attached (which would cause repeated log lines), and (2) it clearly scopes the FR-002 format guarantee to the case where *this* entry point is the first to configure logging. When
  pre-existing handlers are detected, the setup function defers to them — it does not attempt to override or supplement their format.
- How does the system handle subprocess output (e.g., `gh` CLI calls)? Subprocess stderr is captured and re-emitted through `logger.debug()` for diagnostic visibility, while stdout is captured and
  processed programmatically. This avoids interleaving raw subprocess output with formatted log lines.
- What happens when the orchestrator runs outside GitHub Actions (local development)? Logs must still be emitted to the terminal with a sensible format (no `::group::` annotations). The GitHub
  Actions-aware formatter conditionally omits group annotations when `GITHUB_ACTIONS` is not `"true"`.

## Requirements

### Functional Requirements

- **FR-001**: The `ai_pr_loop_command()` entry point MUST configure Python logging to emit messages at INFO level (or a configured level) to stderr before invoking any orchestrator logic. Logs MUST
  go to stderr (not stdout) to avoid mixing human-readable log lines with the structured JSON decision summary that the orchestrator emits to stdout via `_emit_decision_summary()`. The configuration
  logic MUST reside in a dedicated `agentic_devtools/cli/ci/logging_config.py` module for reuse across entry points.
- **FR-002**: When this entry point configures logging (i.e., no pre-existing root handlers are detected), all log messages MUST include a timestamp, log level, and module/logger name so that
  developers can correlate log lines with source modules. The format string MUST be `%(asctime)s %(levelname)-8s %(name)s: %(message)s` with `datefmt="%H:%M:%S"`. If a pre-existing handler is present,
  the existing configuration is respected and this format guarantee does not apply.
- **FR-003**: Guard evaluation outcomes (blocked/allowed) MUST be logged at INFO level outside any collapsed group.
- **FR-004**: Action outcomes (repair dispatched, merge attempted, approval posted) MUST be logged at INFO level outside any collapsed group.
- **FR-005**: Verbose details (full JSON payloads, API response bodies, internal state dumps) MUST remain inside `::group::` collapsed sections to avoid excessive noise.
- **FR-006**: The system MUST support an `AGDT_LOG_LEVEL` environment variable to override the default INFO level (accepting standard Python level names: DEBUG, INFO, WARNING, ERROR). Invalid values
  MUST be ignored with a warning, falling back to INFO.
- **FR-007**: The `speckit_trigger_command()` entry point MUST also configure logging using the same mechanism (calling the shared `setup_logging()` from `logging_config.py`) for consistency.
- **FR-008**: When running outside GitHub Actions (`GITHUB_ACTIONS` is not `"true"`), the system MUST omit `::group::` / `::endgroup::` annotations from log output. This is achieved via the GitHub
  Actions-aware formatter that conditionally includes or omits group annotations based on environment detection.

### Non-Functional Requirements

- **NFR-001**: Logging configuration MUST add less than 10ms overhead to orchestrator startup.
- **NFR-002**: Log format MUST be consistent with GitHub Actions' line-by-line rendering (no multiline log records that break the UI).
- **NFR-003**: The fix MUST NOT change any existing exit codes or orchestrator decision logic — it is purely additive (observability improvement).
- **NFR-004**: The fix MUST be backward compatible — existing workflows that rely on stdout JSON output (decision summaries) MUST continue to function unchanged. Logs go to stderr; stdout
  remains reserved for machine-readable JSON.

### Key Entities

- **Log Handler**: The configured `logging.StreamHandler(sys.stderr)` attached to the root logger, directing output to stderr.
- **Log Format**: The format string `%(asctime)s %(levelname)-8s %(name)s: %(message)s` with `datefmt="%H:%M:%S"` defining how each log record is rendered.
- **Group Annotations**: GitHub Actions `::group::` / `::endgroup::` markers that collapse log sections in the UI, conditionally emitted only when `GITHUB_ACTIONS == "true"`.
- **`setup_logging()` Function**: The idempotent configuration function in `agentic_devtools/cli/ci/logging_config.py` that checks for existing handlers before adding new ones.

## Success Criteria

### Measurable Outcomes

- **SC-001**: After the fix, 100% of `logger.info()` and above calls in the `agentic_devtools.cli.ci` package tree are emitted to stderr (verified by triggering a workflow run and confirming that 0
  log messages are silently discarded).
- **SC-002**: A developer can identify the orchestrator's final decision (guard blocked, repair dispatched, merged, etc.) within the first 50 lines of the step log without expanding any collapsed
  group — measurable by counting visible lines before the decision summary appears, target ≤ 50 lines.
- **SC-003**: The existing test suite passes with 0 new test failures introduced by the change (verified by running `agdt-test` before and after the change and confirming identical pass/fail counts ±
  0).
- **SC-004**: Local invocation of `agdt-ai-pr-loop` with a valid event payload produces ≥ 10 log lines containing both a timestamp (ISO-8601 or HH:MM:SS format) and a module name, confirming the
  logging pipeline is active end-to-end.
- **SC-005**: Setting `AGDT_LOG_LEVEL=DEBUG` causes at least one known debug-only message (e.g., an internal state-transition log from the orchestrator) to appear in the output, and that same
  message is absent when the default INFO level is used — confirming that the verbosity control selectively enables debug-level output without relying on fragile line-count ratios.
- **SC-006**: Logging configuration startup overhead is < 5ms (measured by timing the `setup_logging()` function in isolation across 100 invocations and averaging).
- **SC-007**: When `GITHUB_ACTIONS` environment variable is not set to `"true"`, the orchestrator output contains exactly 0 occurrences of `::group::` or `::endgroup::` annotation strings.

---
*Generated by Copilot SDK (claude-opus-4.6)*
