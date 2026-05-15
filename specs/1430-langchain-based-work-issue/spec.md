# Feature Specification: LangChain-based Work-on-Issue Workflow (`--use-langchain` Flag)

**Feature Branch**: `1430-langchain-work-on-issue-workflow`  
**Created**: 2026-05-15  
**Status**: Draft  
**Input**: User description: "Get the LangChain version of the work-on-issue workflow fully functional so it can be tested alongside the existing implementation"  
**Source Issue**: #1430 (<https://github.com/ayaiayorg/agentic-devtools/issues/1430>)

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

**Independent Test**: Can be tested by triggering individual node functions in isolation (unit tests) and verifying they call the correct underlying services (e.g., `planning_node` posts a Jira
comment, `commit_node` runs git operations, `pull_request_node` creates a PR).

**Acceptance Scenarios**:

1. **Given** the LangGraph workflow reaches the `planning_node`, **When** it executes, **Then** a plan is generated and a Jira comment is posted to the issue.
2. **Given** the LangGraph workflow reaches the `commit_node`, **When** it executes, **Then** changes are staged, committed, and pushed via the existing git operations module.
3. **Given** the LangGraph workflow reaches the `pull_request_node`, **When** it executes, **Then** a pull request is created via the Azure DevOps API.

---

### User Story 4 - Durable Checkpoint Persistence (Priority: P2)

As an operator running long-lived workflows, I want the LangGraph workflow to persist state via `SqliteSaver` so that execution can survive process restarts and be resumed from any checkpoint.

**Why this priority**: Durability is important for production readiness but the workflow can be tested end-to-end without it (using in-memory execution).

**Independent Test**: Can be tested by starting a workflow, killing the process at the planning gate interrupt, restarting the process, and resuming execution from the saved checkpoint.

**Acceptance Scenarios**:

1. **Given** a LangGraph workflow is paused at the planning gate, **When** the process is restarted and resumed with the same thread ID, **Then** execution continues from the checkpoint without
   re-running previous nodes.
2. **Given** the `--use-langchain` flag is provided, **When** the workflow is invoked, **Then** a `SqliteSaver` checkpointer is configured and state is persisted to the `.agdt/` directory.

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

- What happens when `--use-langchain` is provided but LangGraph/LangChain dependencies are not installed? The system MUST produce a clear error message indicating missing dependencies and exit
  gracefully.
- What happens when the LangGraph workflow fails mid-execution (e.g., Jira API timeout at `planning_node`)? The error MUST be recorded in the graph state, the checkpoint MUST be preserved, and the
  workflow MUST be resumable from the failed node.
- What happens when `--use-langchain` is combined with `--interactive` or `--model`? All existing CLI flags MUST continue to function and be forwarded appropriately to the LangGraph execution context.
- What happens when the SQLite checkpoint database becomes corrupted? The system MUST detect the corruption and offer a reset path without losing the ability to start a fresh workflow.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a `--use-langchain` flag on `agdt-initiate-work-on-jira-issue-workflow` that routes execution to the LangGraph-based implementation.
- **FR-002**: When `--use-langchain` is NOT provided, the system MUST execute the existing state-machine workflow in `manager.py` with zero behavioral changes.
- **FR-003**: The LangGraph workflow node functions MUST perform real tool integrations: Jira API calls (fetch issue, post comments), Git operations (stage, commit, push), and Azure DevOps API calls
  (create PR).
- **FR-004**: The LangGraph workflow MUST support human-in-the-loop interruption at the planning gate via LangGraph's `interrupt()` / `Command(resume=...)` mechanism.
- **FR-005**: The LangGraph workflow MUST persist execution state via `SqliteSaver` checkpointing to enable resume after process restart.
- **FR-006**: The LangGraph workflow MUST respect the `dry_run` state key — when set to `true`, no external API calls or git mutations are performed.
- **FR-007**: The LangGraph workflow MUST produce structured audit trail events (appended to the `events` channel) for each node execution.
- **FR-008**: The verification node MUST implement retry logic (routing back to implementation up to MAX_RETRIES times) using the existing conditional edge pattern.
- **FR-009**: The system MUST produce a clear, actionable error message when `--use-langchain` is used but required LangGraph dependencies are not available.
- **FR-010**: The pull request review workflow (`agdt-initiate-pull-request-review-workflow`) MUST NOT be modified by this feature.

### Non-Functional Requirements

- **NFR-001**: The LangGraph workflow execution MUST complete within the same order of magnitude as the existing workflow (no more than 2x slower for equivalent operations, excluding external API
  latency).
- **NFR-002**: CLI output format for `--use-langchain` MUST follow the same conventions as the existing workflow (progress messages, step announcements, error formatting) to maintain UX consistency.
- **NFR-003**: The LangGraph checkpoint SQLite database MUST be stored within the existing `.agdt/workflows/{identity}/{worktree_key}/` directory structure to maintain state isolation across
  worktrees.
- **NFR-004**: All new code MUST have unit tests following the 1:1:1 test structure policy and achieve 100% coverage for new modules.
- **NFR-005**: The feature MUST not introduce breaking changes to the `agentic_devtools` public API or CLI command signatures (beyond the additive `--use-langchain` flag).

### Key Entities

- **WorkOnIssueState**: LangGraph TypedDict representing the full workflow state — issue key, current step, status, plan content, error state, retry count, events audit trail, human approval flag,
  agent context, and affected file paths.
- **WorkOnIssueEvent**: Timestamped event entry in the append-only audit trail channel.
- **CompiledStateGraph**: The compiled LangGraph graph instance configured with node functions and conditional edges, ready for invocation with a checkpointer.
- **SqliteSaver Checkpoint**: Durable per-issue state snapshot enabling resume across process restarts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `agdt-initiate-work-on-jira-issue-workflow --use-langchain --issue-key <KEY>` successfully executes all workflow nodes end-to-end for a real Jira issue, producing a Jira comment, git
  commit, and pull request.
- **SC-002**: The existing workflow (without `--use-langchain`) passes all existing unit and integration tests without modification.
- **SC-003**: The LangGraph workflow can be interrupted at the planning gate and successfully resumed from checkpoint after process restart.
- **SC-004**: All new code achieves 100% test coverage with tests following the 1:1:1 structure policy.
- **SC-005**: No files outside the orchestration module and the `commands.py` entry point are modified (confirming isolation from the existing workflow and PR review workflow).
- **SC-006**: The `--use-langchain` flag is documented in CLI help output and the copilot-instructions.

---
*Generated by Copilot SDK (claude-opus-4.6)*
