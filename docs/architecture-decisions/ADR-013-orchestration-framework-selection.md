# ADR-013: Orchestration Framework Selection

**Status**: Accepted

**Context**: AGDT is evolving from a CLI helper tool into a full workflow
orchestration layer for AI-assisted development. The target architecture requires
multiple AI agents working on the same issue across hours or days, a deliberative
multi-reviewer consensus pattern with sequential reviewers and boss escalation,
configurable human-in-the-loop gates, deterministic application-controlled
routing, persistent shared state per issue, and structured audit trails. A
framework decision is needed before implementation can begin. See the
[full evaluation](../analysis/001-orchestration-framework-evaluation.md) for the
detailed analysis of all candidates.

**Decision**: Use **LangGraph** (from the LangChain ecosystem) as AGDT's core orchestration framework.

**Rationale**:

- LangGraph's graph-based execution model with application-controlled conditional edges maps directly to AGDT's deterministic orchestration requirement — AI agents never decide routing
- Native support for cyclic graphs enables the deliberative review loop pattern without workarounds
- Built-in `SqliteSaver` checkpointing provides durable, per-issue state persistence that survives across sessions (hours/days apart) without requiring a separate server
- The `interrupt()` / `Command(resume=...)` primitive directly supports configurable human-in-the-loop gates
- Lightweight dependency footprint (~6 direct dependencies, ~10–30 MB install) compatible with pipx/pip local CLI installation
- MIT license with active maintenance (200+ contributors, regular releases)
- Plain Python functions as graph nodes means AI agents are focused function nodes receiving prepared context — no autonomous routing
- Checkpoint state at every step provides a structured, timestamped audit trail per issue

**Relationship to ADR-001 — Phased State Unification**:
[ADR-001](ADR-001-state-management-single-json-file.md) originally rejected
SQLite as "overkill" for state storage. With LangGraph's adoption, SQLite
will become the primary long-term state backend for AGDT. There will be a
transitional period with two parallel storage systems, but this ADR supersedes
ADR-001 and establishes a phased migration plan to consolidate all state into
SQLite over time:

- **Phase 1 — Orchestration state** (immediate): LangGraph's `SqliteSaver`
  manages per-issue graph execution state — step snapshots, interrupt/resume
  data, and the structured audit trail. The existing JSON-based CLI state
  (`state.py`, `file_locking.py`, `task_state.py`, `agdt_branch.py` — ~3,200
  lines of custom state management) continues to operate during this phase.
- **Phase 2 — CLI command state migration** (planned): Migrate CLI command
  state (PR IDs, Jira keys, settings, workflow step tracking) from
  JSON files under `.agdt/workflows/` into the same SQLite store. This
  eliminates the custom file-locking layer, bootstrap resolution logic,
  and git-based state persistence (`-agdt` branch commits), replacing
  ~3,200 lines of bespoke state infrastructure with LangGraph's built-in
  persistence. Background task state (`task_state.py`) also migrates.
- **Phase 3 — Cleanup** (post-migration): Remove `file_locking.py`, simplify
  `state.py` to a thin wrapper over LangGraph's store API, retire the
  `-agdt` branch persistence mechanism, and remove
  `_update_bootstrap_worktree_key` / bootstrap resolution logic.

**Why unify?** The current state system spans 4 modules with custom file
locking, bootstrap identity resolution, git plumbing for branch-based
persistence, and separate background task tracking — all of which SQLite
handles natively. Maintaining two persistence systems increases the testing
and debugging surface. Once LangGraph's `SqliteSaver` is proven in Phase 1,
extending it to CLI state is a natural simplification that reduces
maintenance burden significantly.

**Consequences**:

- ✅ Persistent shared state per issue via SQLite checkpoints — no custom persistence layer needed
- ✅ Deterministic orchestration with application-controlled routing via conditional edges
- ✅ Native cycle support for the deliberative review loop pattern
- ✅ Human-in-the-loop gates via interrupt/resume, configurable per repository
- ✅ Local CLI execution with no server infrastructure required
- ✅ Structured audit trail with full state snapshots at every step
- ✅ Workflow visualization via built-in Mermaid graph export
- ✅ Phased elimination of ~3,200 lines of custom state management code (file locking, bootstrap resolution, git-based persistence, background task tracking)
- ⚠️ Introduces dependency on `langchain-core` (lightweight but couples to LangChain serialization)
- ⚠️ Contributors must learn StateGraph, channels, and reducer concepts (moderate learning curve)
- ⚠️ Checkpoint schema evolution needs consideration for long-running workflows across LangGraph version upgrades
- ⚠️ Phase 2 migration requires careful backwards-compatibility handling for existing `.agdt/workflows/` state files

**Alternatives Considered**:

| Alternative | Rejected Because |
|-------------|------------------|
| CrewAI | Agent-autonomous design conflicts with deterministic orchestration; AI controls routing by default |
| Microsoft AutoGen | Conversation-centric distributed architecture adds complexity; CLI-only use underutilizes the framework |
| Semantic Kernel | Planner-driven execution conflicts with deterministic orchestration; C#-ported Python SDK is non-idiomatic |
| Prefect | DAG-based (no native cycles); heavy dependency footprint (>100 MB); data pipeline focus, not agent workflows |
| Temporalio | Requires a separate Temporal server (Docker); disqualified by local CLI execution requirement |
| Custom + SQLite | Maximum control but significant implementation cost for checkpointing, graph execution, and interrupt/resume; LangGraph provides these battle-tested |

See the [full evaluation](../analysis/001-orchestration-framework-evaluation.md) for detailed per-framework assessments, integration pseudocode, and comparison matrix.
