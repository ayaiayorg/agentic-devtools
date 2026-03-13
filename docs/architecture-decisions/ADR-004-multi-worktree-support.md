# ADR-004: Multi-Worktree Support

**Status**: Accepted

**Context**: Developers use git worktrees for parallel branch development

**Decision**: Use a single global pip/pipx install of agentic-devtools, shared across all worktrees

**Rationale**:

- Simplifies installation and maintenance
- Single source of truth for command versions
- No per-worktree setup required
- No startup overhead from venv detection

**Consequences**:

- ✅ Zero UX impact
- ✅ Simple installation
- ✅ No re-execution complexity
