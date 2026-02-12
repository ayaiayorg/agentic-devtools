<!--
Sync Impact Report
- Version change: 1.0.0 -> 1.1.0
- Modified principles:
   - IV. Test-Driven Development (Non-Negotiable) -> IV. Test-Driven Development & Coverage
   - V. Python Package Best Practices -> VIII. Python Package Best Practices (renumbered)
- Added sections:
   - V. Code Quality & Maintainability
   - VI. User Experience Consistency
   - VII. Performance & Responsiveness
- Removed sections: None
- Templates requiring updates:
   - .specify/templates/spec-template.md ✅ updated
   - .specify/templates/tasks-template.md ✅ updated
   - .specify/templates/commands/tasks.md ✅ updated
   - .specify/templates/commands/implement.md ✅ updated
   - README.md ✅ updated
   - SPEC_DRIVEN_DEVELOPMENT.md ✅ updated
- Follow-up TODOs: None
-->

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

### IV. Test-Driven Development & Coverage

All features must follow TDD practices:

- Tests written before implementation
- Minimum 95% code coverage for new or changed code
- Unit tests for new logic and integration tests for all CLI commands
- Use `agdt-test` commands (never run pytest directly)
- Background task execution for test runs
- Any exception to coverage requires explicit justification in the PR

**Rationale**: Ensures reliability and maintainability of automation tools.

### V. Code Quality & Maintainability

All changes must meet explicit quality and maintainability standards:

- Public APIs MUST include type hints and docstrings
- Linting and formatting MUST pass without warnings
- Changes MUST avoid dead code and unused configuration
- Error handling MUST be explicit and actionable (no silent failures)

**Rationale**: Ensures reliable automation and long-term maintainability.

### VI. User Experience Consistency

CLI user experience must be consistent and predictable:

- Command naming, flags, and state keys MUST follow existing patterns
- Output MUST be structured, concise, and include next-step guidance
- Error messages MUST explain cause and resolution steps
- Breaking changes to CLI UX require a major version bump and migration notes

**Rationale**: Enables AI and human users to operate the CLI confidently.

### VII. Performance & Responsiveness

Performance requirements must be explicit and enforced:

- Any synchronous CLI command MUST complete within 2 seconds on typical inputs
- Operations expected to exceed 2 seconds MUST use background tasks
- Network calls MUST set timeouts and include retry logic where safe
- Performance expectations MUST be documented in specs and validated in tests

**Rationale**: Prevents workflow stalls and supports reliable automation.

### VIII. Python Package Best Practices

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
- Performance expectations documented and verified for new commands

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
- UX output and error handling conform to established patterns

### Pre-Release

- Full test suite passes
- Documentation updated
- CHANGELOG.md updated
- Version bumped appropriately
- Performance expectations validated for new or modified commands

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

**Version**: 1.1.0 | **Ratified**: 2026-02-02 | **Last Amended**: 2026-02-03
