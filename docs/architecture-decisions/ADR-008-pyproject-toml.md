# ADR-008: pyproject.toml for Package Configuration

**Status**: Accepted

**Context**: Need modern Python packaging configuration

**Decision**: Use `pyproject.toml` with PEP 517/518 standards

**Rationale**:

- Modern Python standard
- Centralized configuration
- Tool configuration in one place
- Better than setup.py

**Consequences**:

- ✅ Modern standard
- ✅ Single config file
- ✅ Tool integration (black, pytest, mypy)
- ⚠️ Python 3.8+ required
