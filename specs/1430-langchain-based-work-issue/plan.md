# Implementation Plan: LangChain Work-on-Issue Workflow (`--engine langchain`)

Branch: `speckit/1430/phase-3-plan`
Date: `2026-05-17`
Spec: `specs/1430-langchain-based-work-issue/spec.md`
Input: `Feature scope from specs/1430-langchain-based-work-issue/spec.md for LangChain-based work-on-issue workflow parity`

## Summary

Implement the LangChain-backed `agdt-initiate-work-on-jira-issue-workflow` path behind `--engine langchain` (with `--use-langchain`
alias support) while preserving default workflow behavior when no engine is selected. The plan delivers runner/node integration,
checkpoint/resume safety, git-operation parity, and documentation/test updates needed for Phase 4 task generation.

## 1. Technical Context

| Layer | Technology | Notes |
|-------|-----------|-------|
| Orchestration | LangGraph `StateGraph` + `SqliteSaver` | Already wired in `agentic_devtools/orchestration/` |
| Tool layer | `agentic_devtools/tools/{jira,git,azure_devops}.py` | Stateless, typed functions — ready to call from nodes |
| CLI entry point | `agentic_devtools/cli/workflows/commands.py` | `initiate_work_on_jira_issue_workflow()` via argparse |
| State | JSON file in `.agdt/workflows/{identity}/{worktree_key}/` | Existing state management |
| Checkpointing | SQLite via `langgraph-checkpoint-sqlite` | Currently resolves to wrong path (repo root) |
| Testing | pytest, 1:1:1 structure under `tests/unit/` | 100% coverage required for new modules |

**Key architectural constraint**: Node functions must call `agentic_devtools.tools.*` directly — never CLI entry points that spawn background tasks or call `sys.exit()`.

## 2. Research Summary

The key implementation decisions for this workflow are summarized here:

- **CLI flag design**: add `--engine langchain` as the explicit engine selector and keep `--use-langchain` as a backward-compatible alias that resolves to the same engine value.
- **Checkpoint path resolution**: store LangGraph checkpoints in the existing worktree-scoped workflow area so resume behavior is isolated per identity/worktree instead of resolving
  relative to the repository root.
- **Node function architecture**: implement workflow nodes as direct calls into `agentic_devtools.tools.*` functions, not CLI entry points, to avoid subprocess-style side effects,
  background task spawning, or `sys.exit()` behavior inside orchestration.
- **Resume mechanism**: use the spec-defined deterministic LangGraph thread ID pattern `work-on-issue-{issue_key}` so resume targets the correct checkpoint stream, while
  identity/worktree isolation continues to come from the existing worktree-scoped state directory (`get_state_dir()`).
- **Spec artifact availability**: Phase 0/1 SpecKit artifacts (`research.md`, `data-model.md`, `quickstart.md`, `contracts/*`) are
  required inputs for Phase 4 task generation; this feature directory force-includes the generated artifacts so downstream
  task generation has the full design set.

## 3. Design Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│ CLI Layer: agdt-initiate-work-on-jira-issue-workflow                │
│   --engine langchain  →  LangGraph path                            │
│   (no flag)           →  Existing manager.py state machine          │
│   --resume            →  Resume from SqliteSaver checkpoint          │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ orchestration/runner.py  │  NEW — execution harness
                    │ - resolve checkpointer  │
                    │ - build graph           │
                    │ - invoke / resume       │
                    │ - handle errors         │
                    └────────────┬────────────┘
                                 │
            ┌────────────────────▼─────────────────────┐
            │ orchestration/nodes.py                    │  NEW — real node impls
            │ - initiate_node()  → validate/init state  │
            │ - planning_node()  → fetch context/state │
            │ - commit_node()    → save_work           │
            │ - pull_request_node() → create_pr        │
            │ - etc.                                    │
            └──────────────────────────────────────────┘
                                 │
            ┌────────────────────▼─────────────────────┐
            │ tools/jira.py, tools/azure_devops.py      │  EXISTING — no changes
            │ tools/git.py                              │  MODIFIED — commit parity
            └──────────────────────────────────────────┘
```

## 4. Constitution Check

- **Constitution gate status**: PASS (documented exception)
- **Why it passes**:
  - Preserves existing workflow behavior as the default path (no-flag path still uses the current state-machine manager).
  - Requires parity for safety-critical behavior before side effects (worktree/branch pre-flight checks, commit/push safeguards, and explicit halt-on-error behavior).
  - Requires test coverage for new flags, resume behavior, checkpoint corruption handling, and alias compatibility.
  - **Documented exception**: the LangGraph path is intentionally synchronous in-process (not background-task wrapped) because
    checkpointed graph execution, human-in-the-loop interrupts, and immediate resume semantics require a single deterministic
    process flow. This exception is limited to this workflow initiation path and does not change existing action-command
    background-task behavior.

## 5. Project Structure

### Documentation (this feature)

```text
specs/1430-langchain-based-work-issue/
├── plan.md              # This file
├── spec.md              # Clarified feature specification (primary task-generation input)
├── research.md          # Decision log consumed as optional Phase 4 context
├── data-model.md        # State/resume contract consumed as optional Phase 4 context
├── quickstart.md        # Manual validation scenarios consumed as optional Phase 4 context
├── checklists/
│   └── requirements.md  # Derived requirements checklist
└── contracts/
    └── .gitkeep         # API contracts placeholder
```

*Note: this feature path force-includes `research.md`, `data-model.md`, and `quickstart.md` despite the
global `specs/*` gitignore defaults so Phase 4 has the complete artifact set available in-repo.*

### Source Code Layout

```text
agentic_devtools/
├── orchestration/
│   ├── __init__.py        MODIFIED — lazy exports (preserve public API, enable FR-009 guard)
│   ├── checkpointing.py   MODIFIED — worktree-scoped path via get_state_dir()
│   ├── graph_builder.py   MODIFIED — node_set parameter, implementation_gate_node routing
│   ├── state_schema.py    MODIFIED — new typed fields for commit/branch/PR/resume/idempotency
│   ├── nodes.py           NEW      — real node implementations
│   └── runner.py          NEW      — execution harness
├── tools/
│   └── git.py             MODIFIED — orchestration-safe adapter (commit parity)
└── cli/workflows/
    └── commands.py        MODIFIED — --engine, --use-langchain, --resume flags

tests/unit/
├── orchestration/
│   ├── nodes/             NEW — one test file per node function
│   ├── graph_builder/     MODIFIED — extend existing test_build_work_on_issue_graph.py
│   └── runner/            NEW — test_run_langchain_workflow.py
├── tools/git/             MODIFIED — extend existing adapter behavior coverage at 1:1:1 symbol paths
└── cli/workflows/commands/ MODIFIED — extend existing flag-routing tests with engine/alias/resume coverage
```

## 6. Implementation Phases

### Phase 1: CLI Flag Routing (FR-001, FR-002, FR-011, FR-013)

**Deliverables**: `--engine langchain`, `--use-langchain` alias, `--resume` flag on the workflow command, and parity forwarding for existing `--interactive`/`--model` options.

1. Add `--engine` argument to `initiate_work_on_jira_issue_workflow()` argparse with choices `["langchain"]`.
2. Add `--use-langchain` as a boolean alias that sets `engine="langchain"`.
3. Add `--resume` flag (requires the LangChain engine to be selected via `--engine langchain` or the equivalent `--use-langchain` alias).
4. Add `--resume-data` optional argument (JSON string) for supplying structured resume payloads to gate nodes
   (e.g., `--resume-data '{"completed": true, "summary": "..."}'`). When `--resume` targets an
   `implementation_gate` pause, this payload is passed as the `Command(resume=...)` value. If `--resume`
   targets a `planning_gate` pause, `--resume-data` is ignored (approval is implicit). If `--resume` is
   provided without `--resume-data` and the checkpoint is paused at `implementation_gate`, the runner MUST
   exit with error code 1 and message: "--resume-data is required when resuming from the implementation gate".
   Required `implementation_gate` schema: `completed: bool` (MUST be `true`), `summary: str` (non-empty), and optional
   `affected_paths: list[str]` where entries are non-empty repository-relative paths.
5. Validate mutual constraints:
    - `--resume` without LangChain engine selection (`--engine langchain` or `--use-langchain`) → exit code 1.
    - `--resume-data` without `--resume` → exit code 1 with message: "--resume-data requires --resume".
    - `--resume-data` for `implementation_gate` must parse as valid JSON object input; invalid JSON (syntax errors) and
      non-object JSON values (string/number/boolean/array/null) MUST exit code 1 with actionable validation messages.
    - When `implementation_gate` resume validation fails (missing/invalid `--resume-data`), the runner MUST stop before
      graph invocation so checkpoint state does not advance.
    - `--use-langchain` and `--engine` both present → deduplicate to `langchain`.
6. Route: when `engine == "langchain"`, call the new `orchestration/runner.py`; otherwise existing path.
7. Preserve existing CLI behavior by forwarding `--interactive` and `--model` values into the LangGraph runner context (in addition to existing `dry_run` behavior).

**Files modified**: `agentic_devtools/cli/workflows/commands.py`

### Phase 2: Checkpoint Path Fix (FR-005, NFR-003)

**Deliverables**: `get_checkpointer()` resolves to worktree-scoped path.

1. Update `checkpointing.py` to import `get_state_dir()` instead of `_get_git_repo_root()`.
2. Default path becomes `get_state_dir() / "orchestration.db"`.
3. Add corruption detection: catch `sqlite3.DatabaseError`, offer reset.

**Files modified**: `agentic_devtools/orchestration/checkpointing.py`

### Phase 3: Real Node Functions (FR-003, FR-006, FR-007)

**Deliverables**: Replace stubs with real tool integrations in a new `nodes.py` module.

1. Create `agentic_devtools/orchestration/nodes.py` with real implementations:
   - `initiate_node` — validate issue key, set initial state
   - `setup_node` — consumes explicit pre-flight results from runner startup; if pre-flight has not passed, this node must fail fast and prevent git/PR mutations
   - `planning_node` — call `tools.jira.fetch_issue_context()` to prepare plan content and record it in the
     existing `state["plan"]` field; do NOT post the Jira comment yet
   - `planning_gate_node` — `interrupt()` for human-in-the-loop approval; after the interrupt resumes, call
     `tools.jira.add_comment(comment=state["plan"])` using the plan text stored in state by `planning_node`,
      so the comment body is fully derived from state and published only after explicit approval
   - `checklist_creation_node` — create checklist from plan
   - `implementation_node` — prepare and record the implementation assignment/state that must be completed before downstream review/verification
   - `implementation_gate_node` — `interrupt()` for explicit agent handoff to edit code; resume must provide implementation results/confirmation before the graph can continue
   - `implementation_review_node` — validate resumed implementation output and mark review complete
   - `verification_node` — run verification only after the implementation handoff has resumed successfully, track retries
   - `commit_node` — execute commit/push through an orchestration-safe git tool/adapter that provides full `agdt-git-save-work` parity (sync/rebase with main,
     publish-on-first-push, force-push-on-amend), then treat any failed structured result as a hard-stop error
   - `pull_request_node` — call `tools.azure_devops.create_pull_request()` with fully derived inputs from state/runner context
   - `completion_node` — call `tools.jira.add_comment()` for final comment
2. Implement `commit_node` with full `agdt-git-save-work` parity:
   - Extend `agentic_devtools/tools/git.py` with an orchestration-safe adapter that provides main-sync/rebase behavior,
     publish-on-first-push, and amend/force-push semantics matching the CLI save-work path (now permitted by SC-005).
   - Keep structured result contracts so node failures hard-stop the graph (no CLI entry-point invocation from nodes).
3. Each node:
   - Checks `state.get("agent_context", {}).get("dry_run")` → skip mutations if true.
   - Appends structured event to `events` channel.
   - Explicitly inspects structured tool results; when a tool reports failure via a return value (for example `SaveWorkResult(success=False)`), record details in state and raise to
     stop execution (no best-effort continuation).
   - Returns partial state dict per LangGraph convention.
4. Add explicit state contract fields for node inputs:
   - `commit_message` (required for commit node)
   - `source_branch` (derived from current branch for PR creation)
   - `pr_title` and `pr_description` (derived from issue context/plan output)
   - `jira_config_id` (a non-secret Jira config identifier/profile name stored in `agent_context`; `planning_node`/`completion_node`
     must resolve the full auth-bearing Jira config only at the tool-call boundary)
   - `azure_devops_config_id` (a non-secret Azure DevOps config identifier/profile name stored in `agent_context`; nodes must
     resolve the full auth-bearing config only at the tool-call boundary)
   - `failed_node` and `resume_target_node` (runner-managed identifiers for failed-but-resumable checkpoints)
   - `idempotency_keys` and `artifact_references` (runner-managed metadata for Jira comment IDs, commit SHAs, and PR IDs used to
     reconcile external side effects before retry/resume)
5. Keep `pilot_workflow.py` unchanged (stubs remain for diagram generation and existing tests).

**Files created**: `agentic_devtools/orchestration/nodes.py`

**Files modified**: `agentic_devtools/orchestration/state_schema.py` (add `commit_message`, `source_branch`, `pr_title`,
`pr_description`, `failed_node`, `resume_target_node`, `idempotency_keys`, `artifact_references`, `implementation_result`; extend
`WorkOnIssueEvent` with optional `node`/`details` keys (`typing_extensions.NotRequired` for stub compatibility and Python 3.10
support); extend `agent_context` to carry only non-secret Jira/ADO config identifiers, not resolved
configs or auth headers), `agentic_devtools/tools/git.py`

### Phase 4: Graph Builder Integration

**Deliverables**: `--engine langchain` invokes `build_work_on_issue_graph()` with real node integrations.

1. Update `agentic_devtools/orchestration/graph_builder.py`:
   - `build_work_on_issue_graph(checkpointer=None, node_set: Literal["stub", "real"] = "stub")`.
   - `node_set="real"` wires `nodes.py` implementations and is used by `--engine langchain`.
   - `node_set="stub"` remains available for diagram/unit-test scenarios that depend on pure stubs.
2. Add `implementation_gate_node` to the real-node graph topology:
   - Insert `implementation_gate_node` between `implementation_node` and `implementation_review_node` with an
     explicit edge so the interrupt/resume handoff is reachable in the compiled graph.
   - Ensure the stub graph does NOT include `implementation_gate_node` so existing stub-based tests are unaffected.
3. Add explicit error routing in graph topology:
   - commit/pull_request/completion nodes raise on failure.
   - verification failures after `MAX_RETRIES` route to a failure/paused-for-resume end-state (no fall-through to
     commit/pull_request on persistent verification errors).
   - raised errors terminate at a failure end-state (no unconditional continuation to downstream side effects).

**Files modified**: `agentic_devtools/orchestration/graph_builder.py`

### Phase 5: Execution Runner (FR-004, FR-008, FR-009, FR-012, FR-013)

**Deliverables**: Orchestration harness that the CLI calls.

1. Create `agentic_devtools/orchestration/runner.py`:
   - `run_langchain_workflow(issue_key, resume=False, resume_data=None, agent_context=None)` — main entry point.
     `resume_data` accepts an optional dict (parsed from the `--resume-data` CLI JSON argument) for gate-node payloads.
   - Ensure FR-009 dependency-guard reachability without breaking the existing `agentic_devtools.orchestration` public API: replace eager
     LangGraph imports in `agentic_devtools/orchestration/__init__.py` with lazy package exports (for example `__getattr__` plus `__all__`) so
     callers can still import `build_work_on_issue_graph`, `get_checkpointer`, and `get_mermaid_diagram` from
     `agentic_devtools.orchestration`, and move LangGraph imports in orchestration modules (for example `graph_builder.py` /
     `checkpointing.py`) behind lazy import boundaries so missing dependencies are reported by runner guard logic instead of import-time
     crashes.
   - Dependency guard: try importing both `langgraph` and the SQLite checkpoint module required by `get_checkpointer()`; if either import fails, print the FR-009 install
     message and `sys.exit(1)`.
   - Run the existing worktree/branch pre-flight logic before graph start and explicitly execute the current scoping/bootstrap step that initializes the issue/worktree
     scope (including the bootstrap worktree key) before any call that depends on `get_state_dir()`.
   - On pre-flight failure, run the same auto-setup flow used by the current workflow, but when that flow rebuilds the explicit command to execute inside the new
      worktree it must preserve the LangGraph routing flags by including `--engine langchain`, for resume invocations
      `--resume` plus `--resume-data` when provided, and `--skip-copilot-session` (matching the existing auto-setup
      convention to prevent duplicate Copilot session launch before VS Code opens) so continuation stays on the
      LangGraph workflow instead of falling back to the legacy state-machine path.
   - After the scope/bootstrap step has completed, resolve the checkpointer via `get_checkpointer()` so `orchestration.db` is created in the worktree-scoped state
     directory rather than the `_unscoped` fallback.
   - Build graph via `build_work_on_issue_graph(checkpointer=..., node_set="real")`.
   - Thread ID: `f"work-on-issue-{issue_key}"`.
   - Build a LangGraph config for every invocation: `config = {"configurable": {"thread_id": thread_id}}`.
   - If `resume=True`: verify a checkpoint exists for that `thread_id` and classify it as resumable only when it is either:
     - paused at a human interrupt boundary, or
     - preserved after a node failure with runner-recorded error metadata indicating the failed node can be retried from the checkpoint.
     Otherwise exit code 1 with resume guidance.
   - If `resume=True` and the checkpoint is paused at an interrupt boundary: determine which gate node is paused,
     then invoke with the appropriate `Command(resume=...)` payload and the same `config`:
      - `planning_gate` pause: `Command(resume=True)` (approval signal; comment body comes from state).
      - `implementation_gate` pause: `Command(resume=<results>)` where `<results>` is a structured dict
         (e.g., `{"completed": true, "summary": "..."}`) parsed from the `--resume-data` CLI argument (JSON string).
          The runner MUST validate that `--resume-data` was provided when the checkpoint is paused at this gate;
          if absent, exit with code 1 and message: "--resume-data is required when resuming from the implementation gate".
          It MUST validate payload schema (`completed: bool` and `summary: str` required, `completed` must be `true`,
          `summary` non-empty; optional `affected_paths: list[str]` with non-empty entries), and reject invalid JSON,
          non-object JSON values, or schema violations with exit code 1 before invoking the graph so no checkpoint
          advancement occurs on bad payloads.
   - If `resume=True` and the checkpoint represents a failed-but-resumable node execution: resume from the failed node using the preserved checkpoint/state for the
     same `thread_id` (do not reject solely because `error` is populated), but do not simply clear retry/error markers and rerun non-idempotent side effects.
     Persist runner-managed idempotency metadata for side-effecting nodes (for example Jira comment/create-commit/create-PR operations), and on resume first
     reconcile whether the external artifact was already created for the prior attempt; only re-execute the node when reconciliation proves no side effect was
     accepted, otherwise record the existing artifact in state, clear transient retry/error markers, and continue from the reconciled checkpoint.
   - If `resume=False`: invoke fresh with initial state and pass the same `config`.
      Before invoking, check whether a checkpoint already exists for the `thread_id`. If a prior checkpoint exists:
       - Print a warning: "Existing checkpoint found for issue `<KEY>`. Resetting to start a fresh workflow."
       - Delete only the existing checkpoint rows for that `thread_id` from the SQLite database so the fresh
         invocation starts from a clean slate and does not merge with stale state.
       - If the checkpointer API cannot selectively delete rows, archive the existing database file and create a
         replacement database that omits the targeted `thread_id`, preserving checkpoints for unrelated issues in the
         same worktree-scoped database.
       - This ensures deterministic behavior: `--engine langchain` without `--resume` always starts fresh.
   - Handle human-in-the-loop pauses from both paths: inspect invoke return values for interrupt/paused markers and print the pause message there, and also keep
     `GraphInterrupt` handling as a compatibility fallback.
   - Handle node exceptions — record in state `error` field, preserve checkpoint, and persist enough metadata to identify the failed node/resume target and the
     idempotency/reconciliation data needed for a later `--resume`.
   - Print progress messages matching existing workflow UX (step announcements).
   - Derive and pass required non-secret node inputs (`commit_message`, `source_branch`, `pr_title`, `pr_description`) plus only non-sensitive Azure DevOps
     configuration (for example organization/project/repository identifiers). Do not store or pass Azure DevOps PAT/auth secrets in `agent_context`, graph state,
     LangGraph `config`, or checkpoints; instead, resolve the PAT immediately before the `tools.azure_devops.create_pull_request()` call inside the node/tool path.

**Files created**: `agentic_devtools/orchestration/runner.py`

**Files modified**: `agentic_devtools/orchestration/__init__.py`, `agentic_devtools/orchestration/graph_builder.py`,
`agentic_devtools/orchestration/checkpointing.py`

### Phase 6: Agent Context Parity (`dry_run`, `interactive`, `model`) (FR-006)

**Deliverables**: All nodes respect `dry_run` and runner carries forward existing workflow context (`interactive`, `model`).

1. In `nodes.py`, each node that would call an external tool checks:

   ```python
   dry_run = state.get("agent_context", {}).get("dry_run", False)
   ```

2. When `dry_run=True`: skip the actual call, append a `"dry_run_skipped"` event instead.
3. The runner reads `dry_run`, `interactive`, and `model` from existing workflow inputs/state and passes them via `agent_context` so the LangGraph path does not drop existing CLI semantics.

**Files modified**: `agentic_devtools/orchestration/nodes.py`, `agentic_devtools/orchestration/runner.py`

### Phase 7: Testing (NFR-004)

> **TDD Integration**: Per the repository's red/green/refactor policy (`.github/copilot-instructions.md`),
> tests MUST be written **before** the corresponding implementation code in each phase. The test deliverables
> listed below are grouped by phase for clarity, but during task generation (Phase 4), each implementation
> task MUST be preceded by its corresponding test task so the TDD cycle is preserved.

**Deliverables**: 100% coverage for all new modules following 1:1:1 structure, plus explicit integration/manual
validation tasks for end-to-end parity and NFR-001 performance checks.

**Phase 1 tests** (written before Phase 1 implementation):

1. `tests/unit/cli/workflows/commands/` — tests for `--engine`, `--resume`, `--resume-data`, `--use-langchain` alias parity,
   the "both alias + engine provided" case, `--resume-data` without `--resume` rejection, invalid/non-object resume JSON
   rejection, and implementation-gate validation failures that must not advance checkpoints.

**Phase 2 tests** (written before Phase 2 implementation):

1. Update existing `test_get_checkpointer.py` for new path resolution and `sqlite3.DatabaseError` corruption/reset handling.

**Phase 3 tests** (written before Phase 3 implementation):

1. `tests/unit/orchestration/nodes/` — one test file per node function.
2. Add direct adapter coverage at the adapter module's matching 1:1:1 path (for this scoped plan, under
   `tests/unit/tools/git/`), including mocked tool-boundary tests for `_run_op()`/`SystemExit` safety and any new
   adapter behavior used by LangGraph nodes.

**Phase 4 tests** (written before Phase 4 implementation):

1. Extend the existing `tests/unit/orchestration/graph_builder/test_build_work_on_issue_graph.py` coverage for
   `node_set="real"` routing and `implementation_gate_node` reachability.

**Phase 5 tests** (written before Phase 5 implementation):

1. `tests/unit/orchestration/runner/test_run_langchain_workflow.py`
2. Add explicit FR-009 dependency-guard coverage in `test_run_langchain_workflow.py` by mocking
   `importlib.import_module` to simulate missing `langgraph` and missing `langgraph.checkpoint.sqlite` (the actual
   import path for `langgraph-checkpoint-sqlite`); assert the FR-009 install message is printed and `sys.exit(1)` is
   called in each case before any graph code runs.
3. Add resume-start isolation coverage for selective checkpoint reset by `thread_id`, proving fresh runs do not wipe
   unrelated paused workflows stored in the same worktree-scoped database.
4. Add integration/manual validation tasks for:
   - the real Jira → git → PR path (including both planning-gate and implementation-gate resume flows),
   - side-by-side comparison of legacy vs `--engine langchain` output artifacts for the same issue, and
   - NFR-001 timing verification that orchestration overhead stays within 2x of the legacy workflow, excluding
     external API latency.
5. Add explicit pre-flight auto-setup command reconstruction coverage (CLI/runner) proving the re-executed command
   preserves `--engine langchain`, `--resume`, `--resume-data` (when provided), and `--skip-copilot-session`.

**Files created**: ~15-20 new test files under `tests/unit/orchestration/`, CLI coverage files under
`tests/unit/cli/workflows/commands/`, and matching adapter coverage under `tests/unit/tools/git/`

### Phase 8: Documentation & CLI Help

**Deliverables**: Updated help text, user-facing docs, copilot-instructions.

1. Update argparse help strings for `--engine`, `--use-langchain`, `--resume`, `--resume-data`.
2. Update `README.md` anywhere `agdt-initiate-work-on-jira-issue-workflow` is documented so the new `--engine langchain`
   invocation, `--resume` usage, and deprecated `--use-langchain` alias are described consistently.
3. Update `docs/workflow-prompts.md` to keep workflow prompt and invocation guidance aligned with the new flags, engine selection, and alias behavior.
4. Update `.github/copilot-instructions.md` with new flags and command mapping.
5. Update `CHANGELOG.md` with feature entry.

**Files modified**: `agentic_devtools/cli/workflows/commands.py`, `README.md`, `docs/workflow-prompts.md`, `.github/copilot-instructions.md`, `CHANGELOG.md`

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Git tool functions call `sys.exit()` on failure | Medium | High | The `tools/git.py` adapter already wraps with `_run_op()` catching `SystemExit` — verified safe |
| LangGraph `interrupt()` behavior changes across versions | Low | Medium | Enforce compatibility via interrupt/resume integration tests and treat lower-bound dependencies as non-pin |
| SQLite corruption in multi-process scenarios | Low | Medium | Use `check_same_thread=False` + catch `DatabaseError` with reset path |
| Checkpoint thread ID collision across worktrees | Low | Low | Thread ID includes issue key; state dir is per-worktree |
| Stale checkpoint on fresh run | Medium | Medium | Runner detects and resets existing checkpoints on non-resume invocations (Phase 5 policy) |
| Existing tests break due to import side effects | Low | High | New modules use lazy imports for LangGraph; stubs remain untouched |

## 8. Dependencies

### External

- `langgraph>=0.2.0` — already in `pyproject.toml` core dependencies
- `langgraph-checkpoint-sqlite>=3.0.1` — already in `pyproject.toml` core dependencies

### Internal

- `agentic_devtools.tools.jira` — `add_comment()`, `fetch_issue_context()`
- `agentic_devtools.tools.git` — `save_work()`, `stage_changes()`, `create_commit()`, `force_push()`
- `agentic_devtools.tools.azure_devops` — `create_pull_request()`
- `agentic_devtools.state` — `get_state_dir()`, `get_value()`, `set_value()`
- `agentic_devtools.cli.azure_devops.config` — `AzureDevOpsConfig`
- `agentic_devtools.cli.jira.config` — Jira auth configuration

---
*Generated by Copilot SDK (claude-opus-4.6)*
