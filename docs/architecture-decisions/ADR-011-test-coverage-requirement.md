# ADR-011: Test Coverage 100% Requirement

**Status**: Accepted

**Context**: Package reliability is critical for AI assistant automation

**Decision**: Require 100% test coverage for all code

**Rationale**:

- High confidence in automation
- Catch bugs before production
- Enables safe refactoring
- Forces testable design

**Consequences**:

- ✅ High reliability
- ✅ Safe refactoring
- ✅ Better design
- ⚠️ Slower development
- ⚠️ More test code

**Enforcement**:

```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = "--cov=agentic_devtools --cov-report=term-missing --cov-fail-under=100"
```

> **Note**: Some earlier documentation (`docs/02-architecture-constraints.md`,
> `docs/10-quality-requirements.md`) still references a 95%+ coverage target.
> This ADR and the `pyproject.toml` enforcement (`--cov-fail-under=100`) are
> the authoritative source. Those docs should be updated in a follow-up PR.
