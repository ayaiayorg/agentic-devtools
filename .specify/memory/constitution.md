# agentic-devtools Constitution

## Core Principles

### I. Auto-Approval Friendly Design

All CLI commands must be designed for auto-approval by AI assistants:
- Use generic `agdt-set key value` pattern for state management (approve once, use for all keys)
- Parameterless action commands that read from state (e.g., `agdt-reply-to-pr-thread`)
- Native Python CLI handling of special characters and multiline content
- Clear, predictable command patterns that enable trust-based automation

**Rationale**: Minimizes approval friction for AI assistants while maintaining safety through state transparency.

### II. Single Source of Truth

State management must use a single JSON file (`scripts/temp/agdt-state.json`):
- All parameters stored in one location
- No distributed configuration
- Transparent state inspection via `agdt-show`
- Atomic state updates with file locking

**Rationale**: Simplifies debugging, ensures consistency, and provides clear audit trail.

### III. Background Task Architecture

All action commands that mutate state or perform API calls must run as background tasks:
- Commands spawn async processes and return immediately with task ID
- Results written to output files when complete
- Monitoring via `agdt-task-status`, `agdt-task-log`, `agdt-task-wait`
- Prevents AI agents from timing out or thinking operations failed

**Rationale**: Enables reliable execution of long-running operations in AI-driven workflows.

### IV. Test-Driven Development (Non-Negotiable)

All features must follow TDD practices:
- Tests written before implementation
- Minimum 95% code coverage for new code
- Integration tests for all CLI commands
- Use `agdt-test` commands (never run pytest directly)
- Background task execution for test runs

**Rationale**: Ensures reliability and maintainability of automation tools.

### V. Python Package Best Practices

Follow standard Python packaging conventions:
- Clear module organization under `agentic_devtools/`
- Entry points defined in `pyproject.toml`
- Type hints for all public APIs
- Comprehensive docstrings
- Cross-platform compatibility (Windows/Linux/macOS)

**Rationale**: Maintains professional standards and enables easy installation/distribution.

## Development Workflow

### Code Changes

1. All changes must maintain backward compatibility unless major version bump
2. New commands require:
   - State management pattern documentation
   - Background task integration (for actions)
   - CLI parameter support where appropriate
   - Integration tests
   - README documentation

### Testing Standards

- Use `agdt-test` for full test suite (~55 seconds, 2000+ tests)
- Use `agdt-test-quick` for rapid iteration
- Use `agdt-test-file --source-file <file>` for focused coverage (100% required)
- Use `agdt-test-pattern` for specific test selection
- All tests run as background tasks with proper log capture

### Documentation Requirements

- README.md must document all CLI commands
- State keys must be documented with purpose and examples
- Workflow steps must include CLI usage examples
- Both explicit (CLI args) and parameterless patterns must be shown

## Quality Gates

### Pre-Commit

- All tests pass
- Code coverage ≥ 95% for changed files
- No linting errors
- Type checking passes

### Pre-Release

- Full test suite passes
- Documentation updated
- CHANGELOG.md updated
- Version bumped appropriately

## Technical Constraints

### Dependencies

- Minimize external dependencies
- Only add dependencies for core functionality
- Prefer standard library when possible
- Document all dependency choices

### Platform Support

- Must work on Windows (PowerShell), Linux (bash), and macOS (zsh)
- File paths must use cross-platform utilities
- Scripts provided in both bash and PowerShell variants

### API Integration

- Azure DevOps REST API v7.1+
- Jira REST API v3
- GitHub API v3 (for future integrations)
- All API calls must include error handling and retry logic

## Governance

This constitution supersedes all other practices. All changes must comply with these principles.

### Amendments

Constitution changes require:
1. Documentation of rationale
2. Approval from maintainers
3. Migration plan for affected code
4. Version bump following semantic versioning

### Compliance

- All PRs must verify compliance with constitution
- Code reviews must reference relevant principles
- Non-compliance requires explicit justification and approval

**Version**: 1.0.0 | **Ratified**: 2026-02-02 | **Last Amended**: 2026-02-02
