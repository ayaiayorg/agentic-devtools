# Research: LangChain Work-on-Issue Workflow (`--engine langchain`)

## Topic 1: Engine Flag Compatibility

- **Decision**: Use `--engine langchain` as the canonical selector and keep `--use-langchain` as a backward-compatible
  alias that resolves to the same engine value before validation.
- **Rationale**: This preserves the original issue contract while aligning with the newer engine-based CLI pattern.
  Treating the alias as an early normalization step keeps `--resume`, help text, and downstream runner logic behaviorally
  equivalent.
- **Alternatives considered**:
  - Keep only `--use-langchain` — rejected because it does not scale to multiple engines.
  - Accept both flags independently through the full stack — rejected because duplicated validation paths would drift.

## Topic 2: Tool-Layer Node Execution

- **Decision**: Real LangGraph nodes call synchronous `agentic_devtools.tools.*` functions directly instead of CLI
  wrappers.
- **Rationale**: CLI wrappers spawn background tasks, depend on global CLI state, and can terminate the process, which
  conflicts with deterministic graph execution and checkpoint safety. Direct tool calls keep node side effects explicit
  and testable.
- **Alternatives considered**:
  - Reuse CLI entry points inside nodes — rejected because background-task behavior would break sequential orchestration.
  - Keep stub nodes and only validate graph wiring — rejected because the feature requires real parity testing.

## Topic 3: Checkpoint Storage and Reset Semantics

- **Decision**: Store `SqliteSaver` checkpoints at `get_state_dir() / "orchestration.db"` and reset fresh starts by
  selectively removing only the current `thread_id`.
- **Rationale**: Worktree-scoped storage matches the repository's existing state isolation model. Selective reset avoids
  corrupting or deleting paused workflows for other issues that share the same worktree database.
- **Alternatives considered**:
  - Keep the repo-root `.agdt/orchestration.db` path — rejected because it breaks worktree isolation.
  - Delete and recreate the whole database on fresh runs — rejected because it destroys unrelated checkpoints.

## Topic 4: Resume and Human Interrupt Design

- **Decision**: Preserve explicit planning and implementation interrupts, using `Command(resume=True)` for the planning
  gate and structured `Command(resume=<dict>)` payloads for the implementation gate.
  Implementation-gate payload schema is fixed to:
  - `completed: bool` (required, must be `true`)
  - `summary: str` (required, non-empty)
  - `affected_paths: list[str]` (optional, non-empty repo-relative paths)
- **Rationale**: The planning gate only needs approval, while the implementation gate needs structured completion data
  before downstream review and verification can proceed. Keeping the payload contract explicit avoids ambiguous boolean
  resumes.
- **Alternatives considered**:
  - Use boolean resume values for every gate — rejected because the implementation handoff needs validated data.
  - Remove human interrupts from the LangGraph path — rejected because human approval is a core workflow requirement.

## Topic 5: Dependency Guard and Import Boundaries

- **Decision**: Move LangGraph imports behind lazy boundaries so the runner can surface the FR-009 dependency guard
  message before any import-time crash.
- **Rationale**: The package currently declares LangGraph dependencies, but defensive runtime guidance is still needed
  for partial/vendored installs. Lazy imports preserve the public orchestration API while making failure handling
  deterministic and testable.
- **Alternatives considered**:
  - Let import errors bubble from module import time — rejected because users receive stack traces instead of the
    required install guidance.
  - Move LangGraph into an optional extras group — rejected because the clarified spec keeps it in core dependencies.
