<!--
Sync Impact Report
- Version change: 1.1.0 -> 1.2.0
- Modified principles:
   - I. Auto-Approval Friendly Design -> I. Scoped Tool Availability
   - II. Single Source of Truth -> II. State Architecture
   - IV. Test-Driven Development & Coverage (coverage 95% -> 100%)
   - VI. User Experience Consistency (removed breaking-change-requires-major-bump)
- Added sections:
   - IX. LangGraph Orchestration
   - X. Dual-Engine Compatibility
   - XI. Pre-1.0 Flexibility
- Modified sections:
   - Development Workflow → Code Changes (pre-1.0 flexibility replaces backward-compat)
   - Governance → Amendments (migration plan no longer mandatory pre-1.0)
   - Quality Gates → Pre-Commit (coverage 95% -> 100%)
- Removed sections: None
- Templates requiring updates:
   - .specify/presets/agdt-templates/templates/spec-template.md (review for alignment)
   - .specify/presets/agdt-templates/templates/tasks-template.md (review for alignment)
   - .specify/extensions/agdt-workflows/commands/tasks.md (review for alignment)
   - .specify/extensions/agdt-workflows/commands/implement.md (review for alignment)
- Follow-up TODOs:
   - docs/08-cross-cutting-concepts.md coverage table updated in this PR
   - docs/10-quality-requirements.md coverage references updated in this PR
-->

# agentic-devtools Constitution

## Core Principles

### I. Scoped Tool Availability

Each workflow step must have a precisely defined set of tools and commands available to it:

- Workflow definitions declare explicit capability sets per step
- Tools and commands are scoped to the minimum required for each operation
- Auto-approval and autopilot modes are recognized as temporary workarounds, not design goals
- Generic patterns (e.g., `agdt-set key value`) remain for flexibility but are not the primary scoping mechanism

**Rationale**: Explicit capability declarations improve safety, auditability, and predictability of AI-driven workflows.

### II. State Architecture

State management uses a dual-layer approach:

- **CLI state**: Parallel-safe isolated JSON segments (`.agdt/workflows/{identity}/{worktree_key}/`)
- **Orchestration state**: LangGraph checkpointing for multi-step workflow recovery
- Transparent state inspection via `agdt-show`
- Atomic state updates with file locking
- Parallel-safe isolated state segments for concurrent subagent execution

**Rationale**: Enables reliable orchestration with checkpoint recovery while maintaining CLI-level state transparency and parallel safety.

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
- 100% code coverage for new or changed code
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

### IX. LangGraph Orchestration

Multi-step workflows use LangGraph with checkpoint state recovery:

- Workflow state persisted via LangGraph checkpointing for resumability
- Human-in-the-loop interrupts at defined decision points
- Automatic retry and recovery from transient failures
- Clear separation between orchestration state and CLI state

**Rationale**: Provides reliable, resumable multi-step workflow execution with built-in recovery.

### X. Dual-Engine Compatibility

New orchestration engines must coexist with existing execution paths:

- Explicit opt-in routing via `--engine` flag
- Failures in one engine MUST NOT affect the other
- Both engines share the same CLI commands and state interfaces
- Migration between engines is user-initiated, never automatic

**Rationale**: Enables incremental adoption of new orchestration without disrupting existing workflows.

### XI. Pre-1.0 Flexibility

Until v1.0.0, the project prioritizes optimization over stability:

- Breaking changes are allowed and expected
- Optimization and simplification preferred over backward compatibility
- Dead code, unused config, and deprecated paths should be actively removed
- No migration plans or deprecation periods required pre-1.0

**Rationale**: Enables rapid iteration and architectural improvements during early development.

## Development Workflow

### Code Changes

1. Breaking changes are permitted pre-1.0 (see Principle XI); prefer simplification over backward compatibility
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
- Code coverage = 100% for changed files
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
3. Version bump following semantic versioning

### Compliance

- All PRs must verify compliance with constitution
- Code reviews must reference relevant principles
- Non-compliance requires explicit justification and approval

**Version**: 1.2.0 | **Ratified**: 2026-02-02 | **Last Amended**: 2026-05-27
