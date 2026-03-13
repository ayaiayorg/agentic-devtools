# ADR-001: State Management via Single JSON File

**Status**: Superseded by [ADR-013](ADR-013-orchestration-framework-selection.md)

**Context**: Need persistent state across command invocations for AI assistant
workflows.

**Decision**: Originally, we chose to use a single JSON file (`agdt-state.json`)
for all state. This decision has been fully superseded:

1. **File location/naming** — The current implementation stores runtime CLI state
   in per-workflow `state.json` files under
   `.agdt/workflows/{identity}/{worktree_key}/`, resolved via `get_state_dir()` /
   `get_state_file_path()` in `agentic_devtools/state.py`.
2. **Full migration to SQLite** —
   [ADR-013](ADR-013-orchestration-framework-selection.md) adopts LangGraph with
   `SqliteSaver` as the unified state backend. The migration is phased:
   Phase 1 introduces SQLite for orchestration checkpoint state; Phase 2
   migrates all CLI command state (PR IDs, Jira keys, settings, workflow
   tracking, background tasks) from JSON files into the same SQLite store;
   Phase 3 removes the custom file-locking, bootstrap resolution, and
   git-based persistence layers (~3,200 lines of code).

The original "SQLite is overkill" assessment was correct when AGDT was a
simple CLI helper with flat key-value state. With the evolution to a full
orchestration engine where multiple agents need structured, queryable,
persistent state across sessions spanning hours or days, SQLite's
capabilities are no longer overkill — they are essential.

**Rationale** (original, for historical context):

- Simple, human-readable format
- No database dependencies
- Easy to inspect and debug
- Cross-platform compatible
- Fits workflow patterns (sequential commands)

**Consequences** (original):

- ✅ No external dependencies
- ✅ Easy to debug (just open file)
- ✅ Fast read/write (<20ms)
- ⚠️ Not suitable for high-concurrency scenarios
- ⚠️ Manual locking required
- ⚠️ Custom infrastructure accumulated over time (~3,200 lines across
  `state.py`, `file_locking.py`, `task_state.py`, `agdt_branch.py`)

**Alternatives Considered** (original):

| Alternative | Rejected Because |
|-------------|------------------|
| SQLite | Originally rejected as overkill — now adopted via [ADR-013](ADR-013-orchestration-framework-selection.md) as requirements evolved |
| YAML | Parsing issues, not JSON-compatible |
| Environment variables | Not persistent, limited size |
| Redis | External service, complex setup |
