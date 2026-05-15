# Feature Specification: LangChain-based Work-on-Issue Workflow (`--use-langchain` Flag)

**Feature Branch**: `1430-langchain-work-on-issue-workflow`  
**Created**: 2026-05-15  
**Status**: Draft  
**Input**: User description: "Get the LangChain version of the work-on-issue workflow fully functional so it can be tested alongside the existing implementation"  
**Source Issue**: #1430 (<https://github.com/ayaiayorg/agentic-devtools/issues/1430>)
**Artifacts**: `spec.md`, `checklists/requirements.md`, `checklists/`, `contracts/`

## Problem Statement

The `agentic_devtools` orchestration module (`agentic_devtools/orchestration/`) already contains a fully wired LangGraph `StateGraph` with stub node functions (`pilot_workflow.py`), a compiled graph
builder (`graph_builder.py`), a state schema (`state_schema.py`), and a `SqliteSaver` checkpointer (`checkpointing.py`). However, all node functions are stubs that manipulate state dictionaries
without calling real Jira, Git, or Azure DevOps systems. Additionally, no CLI flag (`--use-langchain`) currently exists to route execution from `agdt-initiate-work-on-jira-issue-workflow` to the
LangGraph code path.

This feature replaces the stub node functions with real tool integrations (reusing existing modules: `cli/jira/`, `cli/git/`, `cli/azure_devops/`) and adds the `--use-langchain` CLI flag to allow
side-by-side comparison testing with the existing state-machine workflow in `cli/workflows/manager.py`.

## Clarifications

### Session 2026-05-15

- Q: Should LangGraph dependencies remain in the core `dependencies` list (as they are today in `pyproject.toml`) or be moved to an optional extras group `[langchain]` for conditional installation? →
  A: LangGraph dependencies (`langgraph>=0.2.0`, `langgraph-checkpoint-sqlite>=3.0.1`) remain in core `dependencies` since they are already there. The error handling for missing dependencies (FR-009)
  becomes a defensive guard for downstream consumers who may vendor a subset of the package, but the standard install path always includes LangGraph. The error message should still reference `pip
  install agentic-devtools` (not an extras group).
- Q: Should the SQLite checkpoint database be stored at `.agdt/orchestration.db` (current `checkpointing.py` behavior, relative to repo root) or inside `.agdt/workflows/{identity}/{worktree_key}/` (as
  stated in NFR-003) for full worktree isolation? → A: The checkpoint database MUST be stored inside `.agdt/workflows/{identity}/{worktree_key}/orchestration.db` to maintain worktree isolation. The
  existing `checkpointing.py` `get_checkpointer()` function must be updated to resolve the path via `get_state_dir()` instead of `_get_git_repo_root()`.
- Q: How should the `--resume` flag interact with the command when no interrupted workflow exists for the given issue key — should it fail loudly, fall back to a fresh start, or prompt the user? → A:
  The system MUST fail with a clear error message (exit code 1) stating "No interrupted workflow found for issue key `<KEY>`. Use --use-langchain without --resume to start a fresh workflow." It must NOT
  silently start a new workflow, as that could lead to duplicate artifacts.
- Q: Should real node functions call the existing CLI entry points (e.g., `agdt-add-jira-comment` which spawns background tasks) or call the underlying synchronous implementation functions directly to
  maintain graph execution flow? → A: Node functions MUST call real synchronous implementation functions directly (for example
  `agentic_devtools.cli.jira.comment_commands.add_comment()`, git helpers in `agentic_devtools.cli.git.operations` such as
  `stage_changes()` / `create_commit()` / `amend_commit()` / `push()`, and `agentic_devtools.tools.azure_devops.create_pull_request()`).
  Spawning background tasks would break the graph's sequential execution model and make checkpointing unreliable.
- Q: Should the `--use-langchain` flag be mutually exclusive with `--resume` flag validation (i.e., `--resume` requires `--use-langchain`), or should `--resume` work independently? → A: `--resume`
  MUST require `--use-langchain` — it is only meaningful for LangGraph workflows. If `--resume` is provided without `--use-langchain`, the CLI MUST exit with an error: "--resume requires
  --use-langchain".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Invoke LangGraph Workflow via CLI Flag (Priority: P1)

As an AI agent operator, I want to run `agdt-initiate-work-on-jira-issue-workflow --use-langchain --issue-key PROJECT-1234` and have the LangGraph-based orchestration execute end-to-end (from initiate
through completion), using real Jira, Git, and Azure DevOps tool integrations instead of stub node functions.

**Why this priority**: This is the core deliverable — without a working `--use-langchain` flag routing to the LangGraph graph with real tool calls, nothing else in this feature is testable.

**Independent Test**: Can be fully tested by running the command with a valid Jira issue key and observing that the workflow progresses through all nodes (initiate → setup → planning →
checklist_creation → implementation → verification → commit → pull_request → completion) with real side effects (Jira comments posted, git commits created, PR created).

**Acceptance Scenarios**:

1. **Given** the CLI is installed and a valid Jira issue key exists, **When** I run `agdt-initiate-work-on-jira-issue-workflow --use-langchain --issue-key PROJECT-1234`, **Then** the LangGraph
   `build_work_on_issue_graph()` is invoked with real tool integrations and the workflow executes through all nodes.
2. **Given** the `--use-langchain` flag is provided, **When** the workflow reaches the planning gate, **Then** execution pauses via `interrupt()` and can be resumed with a `Command(resume=...)` to
   continue to checklist creation.
3. **Given** the LangGraph workflow is running, **When** verification fails with a retryable error, **Then** the workflow routes back to the implementation node (up to MAX_RETRIES times) before
   proceeding to commit.
4. **Given** `dry_run=true` is set in state, **When** LangGraph nodes that normally call Jira, Git, or Azure DevOps execute, **Then** no external side effects occur and each node records a dry-run event
   describing the skipped action.
5. **Given** the LangGraph workflow executes any node, **When** the node starts and completes, **Then** structured audit-trail events are appended to the `events` channel with node name and timestamp.

---

### User Story 2 - Existing Workflow Remains Unchanged (Priority: P1)

As a user of the existing work-on-jira-issue workflow, I want the default behavior (without `--use-langchain`) to remain completely unmodified so that my current workflows are not disrupted.

**Why this priority**: Non-regression is equally critical — the existing workflow is production-proven and must not be broken by this change.

**Independent Test**: Can be fully tested by running `agdt-initiate-work-on-jira-issue-workflow --issue-key PROJECT-1234` (without `--use-langchain`) and verifying that the existing state-machine in
`manager.py` drives execution exactly as before.

**Acceptance Scenarios**:

1. **Given** no `--use-langchain` flag is provided, **When** I run `agdt-initiate-work-on-jira-issue-workflow --issue-key PROJECT-1234`, **Then** the existing workflow state machine in `manager.py` is
   used and the LangGraph code path is not entered.
2. **Given** the existing workflow is active, **When** I use `agdt-advance-workflow`, `agdt-add-jira-comment`, or any other workflow command, **Then** behavior is identical to before this feature was
   added.
3. **Given** the pull request review workflow code, **When** this feature is implemented, **Then** no files in the pull request review workflow are modified.

---

### User Story 3 - Real Tool Integration in Node Functions (Priority: P1)

As a developer testing the LangGraph workflow, I want the stub node functions in `pilot_workflow.py` to be replaced with real tool integrations (Jira API, Git operations, Azure DevOps PR creation) so
that the workflow produces actual artifacts.

**Why this priority**: Without real tool calls, the LangGraph path cannot be validated against the existing implementation — stubs are not testable in an end-to-end sense.

**Independent Test**: Can be tested by triggering individual node functions in isolation (unit tests) and verifying they call real synchronous implementation targets (e.g.,
`planning_node` calls `agentic_devtools.cli.jira.comment_commands.add_comment()`, `commit_node` uses the existing helpers in `agentic_devtools.cli.git.operations`, and `pull_request_node` calls `agentic_devtools.tools.azure_devops.create_pull_request()`).

**Acceptance Scenarios**:

1. **Given** the LangGraph workflow reaches the `planning_node`, **When** it executes, **Then** a plan is generated and a Jira comment is posted to the issue via the synchronous
   `agentic_devtools.cli.jira.comment_commands.add_comment()` function.
2. **Given** the LangGraph workflow reaches the `commit_node`, **When** it executes, **Then** changes are staged, committed, and pushed via the existing synchronous git helpers in
   `agentic_devtools.cli.git.operations` (for example `stage_changes()`, `create_commit()` / `amend_commit()`, and `push()` / `force_push()`).
3. **Given** the LangGraph workflow reaches the `pull_request_node`, **When** it executes, **Then** a pull request is created via the synchronous
   `agentic_devtools.tools.azure_devops.create_pull_request()` function (or the synchronous wrapper in `agentic_devtools.cli.azure_devops.commands`).

---

### User Story 4 - Durable Checkpoint Persistence (Priority: P2)

As an operator running long-lived workflows, I want the LangGraph workflow to persist state via `SqliteSaver` so that execution can survive process restarts and be resumed from any checkpoint.

**Why this priority**: Durability is important for production readiness but the workflow can be tested end-to-end without it (using in-memory execution).

**Independent Test**: Can be tested by starting a workflow, killing the process at the planning gate interrupt, restarting the process, and resuming execution from the saved checkpoint using
`--use-langchain --resume --issue-key PROJECT-1234`.

**Acceptance Scenarios**:

1. **Given** a LangGraph workflow is paused at the planning gate, **When** the process is restarted and resumed with `--use-langchain --resume --issue-key PROJECT-1234`, **Then** execution continues
   from the checkpoint without
   re-running previous nodes.
2. **Given** the `--use-langchain` flag is provided, **When** the workflow is invoked, **Then** a `SqliteSaver` checkpointer is configured and state is persisted to
   `.agdt/workflows/{identity}/{worktree_key}/orchestration.db`.

---

### User Story 5 - Side-by-Side Comparison Testing (Priority: P3)

As a project maintainer, I want to run both the existing and LangGraph workflows against the same Jira issue to compare outcomes and verify functional equivalence before deprecating the old
implementation.

**Why this priority**: Comparative testing is the eventual validation gate for removing the legacy workflow, but it is not blocking for initial delivery.

**Independent Test**: Can be tested by running both workflow variants for the same issue (sequentially) and comparing the resulting artifacts (Jira comments, PR content, commit messages).

**Acceptance Scenarios**:

1. **Given** a Jira issue exists, **When** I run the workflow without `--use-langchain` and then separately with `--use-langchain`, **Then** both produce equivalent artifacts (PR created, Jira
   comments posted, same workflow steps completed).

---

### Edge Cases

- What happens when `--use-langchain` is provided but LangGraph/LangChain dependencies are not installed (e.g., a vendored subset)? The system MUST produce a clear error message indicating missing
  dependencies and the install command (`pip install agentic-devtools`) and exit gracefully with exit code 1.
- What happens when the LangGraph workflow fails mid-execution (e.g., Jira API timeout at `planning_node`)? The error MUST be recorded in the graph state (`error` field), the checkpoint MUST be
  preserved, and the workflow MUST be resumable from the failed node via `--use-langchain --resume`.
- What happens when `--use-langchain` is combined with `--interactive` or `--model`? All existing CLI flags MUST continue to function and be forwarded appropriately to the LangGraph execution context
  via the `agent_context` field in `WorkOnIssueState`.
- What happens when the SQLite checkpoint database becomes corrupted? The system MUST detect the corruption (SQLite `DatabaseError`) and offer a reset path (delete and recreate the database file)
  without losing the ability to start a fresh workflow.
- What happens when `--resume` is provided without `--use-langchain`? The system MUST exit with error code 1 and message: "--resume requires --use-langchain".
- What happens when `--resume` is provided but no interrupted workflow exists for the given issue key? The system MUST exit with error code 1 and message: "No interrupted workflow found for issue key
  `<KEY>`. Use --use-langchain without --resume to start a fresh workflow."

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a `--use-langchain` flag on `agdt-initiate-work-on-jira-issue-workflow` that routes execution to the LangGraph-based implementation.
- **FR-002**: When `--use-langchain` is NOT provided, the system MUST execute the existing state-machine workflow in `manager.py` with zero behavioral changes.
- **FR-003**: The LangGraph workflow node functions MUST perform real tool integrations by calling underlying synchronous implementation functions directly (not CLI entry points that spawn background
  tasks): Jira API calls (fetch issue, post comments), Git operations (stage, commit, push), and Azure DevOps API calls (create PR).
- **FR-004**: The LangGraph workflow MUST support human-in-the-loop interruption at the planning gate via LangGraph's `interrupt()` / `Command(resume=...)` mechanism. Resume is triggered via
  `--use-langchain --resume --issue-key <KEY>`, using a deterministic thread ID (`work-on-issue-{issue_key}`).
- **FR-005**: The LangGraph workflow MUST persist execution state via `SqliteSaver` checkpointing to `.agdt/workflows/{identity}/{worktree_key}/orchestration.db` to enable resume after process
  restart.
- **FR-006**: The LangGraph workflow MUST respect the `dry_run` state key — when set to `true`, no external API calls or git mutations are performed.
- **FR-007**: The LangGraph workflow MUST produce structured audit trail events (appended to the `events` channel) for each node execution.
- **FR-008**: The verification node MUST implement retry logic (routing back to implementation up to MAX_RETRIES=3 times) using the existing conditional edge pattern in `route_after_verify`.
- **FR-009**: The system MUST produce a clear, actionable error message when `--use-langchain` is used but required LangGraph dependencies are not available. The message MUST include the install
  command: `pip install agentic-devtools`.
- **FR-010**: The pull request review workflow (`agdt-initiate-pull-request-review-workflow`) MUST NOT be modified by this feature.
- **FR-011**: The `--resume` flag MUST require `--use-langchain`. If provided without it, the CLI MUST exit with error code 1 and message: "--resume requires --use-langchain".
- **FR-012**: When `--resume` is provided but no interrupted workflow checkpoint exists for the given issue key, the system MUST exit with error code 1 and a descriptive error message.

### Non-Functional Requirements

- **NFR-001**: The LangGraph workflow execution MUST complete within the same order of magnitude as the existing workflow (no more than 2x slower for equivalent operations, excluding external API
  latency).
- **NFR-002**: CLI output format for `--use-langchain` MUST follow the same conventions as the existing workflow (progress messages, step announcements, error formatting) to maintain UX consistency.
- **NFR-003**: The LangGraph checkpoint SQLite database MUST be stored within the existing `.agdt/workflows/{identity}/{worktree_key}/` directory structure (as `orchestration.db`) to maintain state
  isolation across worktrees. The `get_checkpointer()` function must resolve the path via `get_state_dir()`.
- **NFR-004**: All new code MUST have unit tests following the 1:1:1 test structure policy and achieve 100% coverage for new modules.
- **NFR-005**: The feature MUST not introduce breaking changes to the `agentic_devtools` public API or CLI command signatures (beyond the additive `--use-langchain` and `--resume` flags).

### Key Entities

- **WorkOnIssueState**: LangGraph TypedDict (defined in `agentic_devtools/orchestration/state_schema.py`) representing the full workflow state — issue key, current step, status, plan content, error
  state, retry count, events audit trail (append-only via `operator.add` reducer), human approval flag, agent context, and affected file paths.
- **WorkOnIssueEvent**: Timestamped event entry (`event: str`, `timestamp: str`) in the append-only audit trail channel.
- **CompiledStateGraph**: The compiled LangGraph graph instance (from `build_work_on_issue_graph()` in `graph_builder.py`) configured with node functions and conditional edges, ready for invocation
  with a checkpointer.
- **SqliteSaver Checkpoint**: Durable per-issue state snapshot (stored in `orchestration.db`) enabling resume across process restarts, using deterministic thread ID `work-on-issue-{issue_key}`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `agdt-initiate-work-on-jira-issue-workflow --use-langchain --issue-key <KEY>` successfully executes all workflow nodes end-to-end for a real Jira issue, producing a Jira comment, git
  commit, and pull request.
- **SC-002**: The existing workflow (without `--use-langchain`) passes all existing unit and integration tests without modification.
- **SC-003**: The LangGraph workflow can be interrupted at the planning gate and successfully resumed from checkpoint after process restart via `--use-langchain --resume --issue-key <KEY>`.
- **SC-004**: All new code achieves 100% test coverage with tests following the 1:1:1 structure policy.
- **SC-005**: Production/runtime code changes are limited to the orchestration module (`agentic_devtools/orchestration/`) and the `commands.py` entry point
  (`agentic_devtools/cli/workflows/commands.py`); test files, documentation, and spec artifacts may be updated as needed.
- **SC-006**: The `--use-langchain` and `--resume` flags are documented in CLI help output and the copilot-instructions.

---
*Generated by Copilot SDK (claude-opus-4.6)*
