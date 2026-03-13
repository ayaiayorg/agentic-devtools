# ADR-009: Dynamic Versioning from Git Tags

**Status**: Accepted

**Context**: Manual version updates in `pyproject.toml` caused PyPI upload failures

**Decision**: Use `hatch-vcs` to derive version from Git tags

**Rationale**:

- Single source of truth (Git tags)
- No manual version updates
- Prevents duplicate version uploads
- Standard practice

**Consequences**:

- ✅ No version sync issues
- ✅ Automatic dev versions
- ✅ Prevents duplicates
- ⚠️ Requires Git tags
- ⚠️ Build-time dependency

**Version Flow**:

```text
Git Tag v0.3.0 → hatch-vcs → Package version 0.3.0
No tag → hatch-vcs → Package version 0.2.9.dev1+g1234abc
```
