# ADR-002: Parameterless Command Pattern

**Status**: Accepted

**Context**: VS Code requires approval for each unique command; parameters make commands unique

**Decision**: Commands read parameters primarily from state file, with optional CLI arguments that seed/override state values

**Rationale**:

- `agdt-set key value` approved once, works for all keys
- `agdt-add-jira-comment` approved once, works for all comments
- AI assistant doesn't need to request approval for each variation

**Consequences**:

- ✅ Excellent UX: ~10 approvals vs 100+
- ✅ Consistent command patterns
- ✅ State inspection via `agdt-show`
- ⚠️ Two-step pattern (set then execute)
- ⚠️ Less discoverable parameters

**Example**:

```bash
# ❌ Bad: Requires approval each time
agdt-add-pull-request-comment --pull-request-id 123 --content "LGTM"
agdt-add-pull-request-comment --pull-request-id 124 --content "Needs work"  # New approval!

# ✅ Good: Approve agdt-set once, reuse forever
agdt-set pull_request_id 123
agdt-set content "LGTM"
agdt-add-pull-request-comment  # Already approved!
```
