# Spec-Driven Development Guide

This guide explains how to use Spec-Driven Development (SDD) with
agentic-devtools.

**Developer-only**: This guide is intended for AGDT maintainers and
contributors. **End‑User**: [README.md](README.md).

## Audience Labels

Use explicit audience labels when cross‑linking documentation:

- **Developer-only**: Use this label for links intended only for maintainers or

  contributors.
  contributors.

- **End‑User**: Use this label when pointing to end‑user documentation.

## What is Spec-Driven Development?

Spec-Driven Development is a methodology that emphasizes:

- **Intent-driven development** - Define "what" before "how"
- **Rich specifications** - Detailed, executable specifications
- **Multi-step refinement** - Iterative improvement over one-shot generation
- **AI-native workflows** - Designed for AI assistant collaboration

## Quick Start

### 1. Review the Constitution

The project constitution defines core principles and governance:

```bash
cat .specify/memory/constitution.md
```text

Key principles for agentic-devtools:

- Auto-approval friendly command design
- Single source of truth (state file)
- Background task architecture
- Test-driven development and coverage standards
- Code quality and maintainability
- User experience consistency
- Performance and responsiveness
- Python best practices

### 2. Create a Feature Specification

Use the helper script:

```bash
# Create feature branch and directory
.specify/scripts/bash/create-new-feature.sh "add-webhook-support"

# This creates:
# - Branch: 002-add-webhook-support
# - Directory: specs/002-add-webhook-support/
# - File: specs/002-add-webhook-support/spec.md (from template)
```text

### 3. Fill Out the Specification

Edit `specs/NNN-feature-name/spec.md`:

1. **User Stories** - Prioritized scenarios (P1, P2, P3)

   - What users want to accomplish
   - Why it's valuable
   - How to test independently

2. **Requirements** - Functional and non-functional

   - FR-001, FR-002, etc. (functional)
   - NFR-001, NFR-002, etc. (non-functional)

3. **Edge Cases** - Boundary conditions and error scenarios

4. **Success Metrics** - How to measure success

### 4. Create Implementation Plan

AI assistants can use the `/speckit.plan` command:

```text
/speckit.plan
Technology stack:
- Python 3.11+
- Click for CLI
- Background task execution
- State-based parameter passing
```text

This creates `specs/NNN-feature-name/plan.md` with:

- Technical context
- Architecture decisions
- Project structure
- Dependencies
- Constitution compliance check

### 5. Break Down into Tasks

Use `/speckit.tasks` to generate task list:

```text
/speckit.tasks
```text

This creates `specs/NNN-feature-name/tasks.md` with:

- Tasks organized by user story
- Parallel execution markers [P]
- Exact file paths
- Dependencies clearly marked

### 6. Implement

Execute the implementation:

```text
/speckit.implement
```text

AI assistant will:

- Follow the task list
- Reference the spec for requirements
- Check against the plan
- Run tests continuously
- Update documentation

## Repository SDD Assets

The `.specify/` directory contains the SDD templates and helper scripts:

```text
.specify/
├── memory/
│   └── constitution.md      # Project principles and governance
├── templates/
│   ├── spec-template.md     # Feature specification template
│   ├── plan-template.md     # Implementation plan template
│   ├── tasks-template.md    # Task breakdown template
│   ├── checklist-template.md
│   └── commands/            # SDD workflow command templates
└── scripts/                 # Helper scripts (bash & PowerShell)
```text

### SDD Command Templates

AI assistants can use these command templates (in
`.specify/templates/commands/`):

- `/speckit.constitution` - Update project principles
- `/speckit.specify` - Create feature specifications
- `/speckit.plan` - Develop implementation plans
- `/speckit.tasks` - Generate task lists
- `/speckit.implement` - Execute implementation
- `/speckit.analyze` - Validate cross-artifact consistency
- `/speckit.checklist` - Generate quality checklists

## Directory Structure

```text
agentic-devtools/
├── .specify/                    # SDD infrastructure
│   ├── memory/
│   │   └── constitution.md      # Project principles
│   ├── templates/
│   │   ├── spec-template.md     # Feature spec template
│   │   ├── plan-template.md     # Implementation plan template
│   │   ├── tasks-template.md    # Task list template
│   │   ├── checklist-template.md
│   │   └── commands/            # AI command templates
│   │       ├── constitution.md  # Update constitution
│   │       ├── specify.md       # Create specs
│   │       ├── plan.md          # Create plans
│   │       ├── tasks.md         # Create tasks
│   │       ├── implement.md     # Execute implementation
│   │       ├── analyze.md       # Validate consistency
│   │       └── clarify.md       # Clarify requirements
│   └── scripts/                 # Helper scripts
│       ├── bash/                # Linux/macOS scripts
│       └── powershell/          # Windows scripts
├── specs/                       # Feature specifications
│   ├── 001-example-feature/
│   │   ├── spec.md             # The specification
│   │   ├── plan.md             # Implementation plan
│   │   └── tasks.md            # Task breakdown
│   └── README.md
├── agentic_devtools/           # Source code
└── tests/                      # Test suite
```text

## Documentation Boundaries

- **End‑User entry point**: README.md (must not include Specify references).
- **Developer entry point**: SPEC_DRIVEN_DEVELOPMENT.md (this file).
- **Developer-only**: specs/README.md may link here with labels.
- Cross‑links between sections must include explicit audience labels (e.g.,

  “Developer‑only”, “End‑User”).
  “Developer‑only”, “End‑User”).

## SDD Commands for AI Assistants

These slash commands are available when properly configured:

### Core Workflow

1. **`/speckit.constitution`** - Update project principles

   ```text
   /speckit.constitution Update testing standards to require 95% coverage
   ```text

2. **`/speckit.specify`** - Create feature specification

   ```text
   /speckit.specify Build a command that exports Jira issues to CSV format
   ```text

3. **`/speckit.plan`** - Create implementation plan

   ```text
   /speckit.plan Use pandas for CSV export, Click for CLI
   ```text

4. **`/speckit.tasks`** - Generate task list

   ```text
   /speckit.tasks
   ```text

5. **`/speckit.implement`** - Execute implementation

   ```text
   /speckit.implement
   ```text

### Quality Assurance

- **`/speckit.analyze`** - Check cross-artifact consistency

  ```text
  /speckit.analyze
  ```text

- **`/speckit.checklist`** - Generate quality checklist

  ```text
  /speckit.checklist
  ```text

- **`/speckit.clarify`** - Clarify underspecified areas

  ```text
  /speckit.clarify
  ```text

## Integration with Existing Workflows

SDD complements existing agentic-devtools workflows:

### State Management

SDD specifications define what state keys are needed:

```markdown
## Requirements

- FR-001: System MUST support export.format state key
- FR-002: System MUST support export.output_file state key
```text

Implementation uses standard state pattern:

```bash
agdt-set export.format csv
agdt-set export.output_file issues.csv
agdt-export-jira-issues
```text

### Background Tasks

Specifications identify long-running operations:

```markdown
## Non-Functional Requirements

- NFR-001: Export operation MAY take > 30 seconds for large datasets
```text

Implementation uses background task pattern:

```python
@background_task_wrapper
def export_jira_issues():
    # Long-running export logic
    pass
```text

### Testing

Specifications drive test requirements:

```markdown
## Acceptance Scenarios

1. **Given** 100 Jira issues exist, **When** export runs, 
   **Then** CSV contains 100 rows with correct data
```text

Tests verify acceptance criteria:

```python
def test_export_100_issues():
    # Test implementation matching spec
    pass
```text

## Best Practices

### Writing Specifications

✅ **Do:**

- Focus on user value and "what" not "how"
- Prioritize user stories (P1 > P2 > P3)
- Make stories independently testable
- Include clear acceptance criteria
- Document edge cases
- Define success metrics

❌ **Don't:**

- Specify implementation details in spec
- Mix multiple concerns in one story
- Create dependencies between stories
- Skip non-functional requirements
- Ignore error scenarios

### Creating Plans

✅ **Do:**

- Document technical decisions and rationale
- Define clear project structure
- List all dependencies with versions
- Check constitution compliance
- Consider existing patterns

❌ **Don't:**

- Start implementation before plan approval
- Ignore constitution principles
- Skip architecture discussion
- Forget cross-platform concerns

### Breaking Down Tasks

✅ **Do:**

- Organize by user story
- Mark parallel tasks with [P]
- Include exact file paths
- Specify test tasks clearly
- Estimate blocking dependencies

❌ **Don't:**

- Create monolithic tasks
- Hide dependencies
- Skip test tasks
- Mix setup with implementation

## Examples

### Example 1: Simple Command

See `specs/001-example-feature/spec.md` for a complete example showing:

- User story structure
- Acceptance scenarios
- Requirements (FR/NFR)
- Edge cases
- Success metrics

### Example 2: Workflow Documentation

See `specs/002-github-action-speckit-trigger/workflow-sequence-diagram.md` for
a
comprehensive example showing:

- Mermaid sequence diagram of complete workflow
- Documentation of all actors and their responsibilities
- Phase-by-phase breakdown of the process
- Decision points and error handling
- Integration with SDD pattern
- Configuration options and performance targets

This example demonstrates how to document complex workflows that follow the SDD
pattern, making it easy for new contributors to understand the system behavior.

### Example 3: Complex Feature

For multi-component features:

```text
specs/00X-complex-feature/
├── spec.md              # Main specification
├── plan.md              # Implementation plan
│   ├── Phase 0: Research
│   ├── Phase 1: Design
│   └── Phase 2: Implementation
├── tasks.md             # Task breakdown
├── research.md          # Technical research (auto-generated)
├── data-model.md        # Data structures (auto-generated)
├── quickstart.md        # Usage guide (auto-generated)
└── contracts/           # API contracts (auto-generated)
    ├── endpoint-1.md
    └── endpoint-2.md
```text

## Troubleshooting

## Development Environment

### Dev Container

This repository includes a devcontainer configuration for Python development:

- **VS Code**: Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers), then click "Reopen in Container"
- **GitHub Codespaces**: Create a new Codespace - all dependencies will be set

  up automatically
  up automatically

See [.devcontainer/README.md](.devcontainer/README.md) for more details
(Developer-only).

### Testing Commands (Developer-only)

Use the AGDT test commands (do not run pytest directly):

```bash
# Run full test suite with coverage (background)
agdt-test
agdt-task-wait

# Run tests quickly (no coverage)
agdt-test-quick
agdt-task-wait

# Run specific test file, class, or method (synchronous)
agdt-test-pattern tests/test_jira_helpers.py
agdt-test-pattern tests/test_jira_helpers.py::TestEnsureJiraPem
agdt-test-pattern tests/test_jira_helpers.py::TestEnsureJiraPem::test_returns_existing_pem_path

# Run tests using state (alternative)
agdt-set test_pattern test_jira_helpers.py
agdt-test-file
agdt-task-wait
```text

### Scripts Not Executable

```bash
chmod +x .specify/scripts/bash/*.sh
```text

### Commands Not Available

Ensure templates are in place:

```bash
ls .specify/templates/commands/
```text

### Constitution Conflicts

Review and update constitution:

```bash
vim .specify/memory/constitution.md
```text

Run consistency check:

```text
/speckit.analyze
```text

## Additional Resources

- [GitHub spec-kit](https://github.com/github/spec-kit) - Official SDD toolkit
- [Spec-Driven Development Guide](https://github.github.io/spec-kit/) - Full documentation
- [Constitution Template](../.specify/templates/commands/constitution.md) - How

  to manage constitution
  to manage constitution

- [Example Spec](../specs/001-example-feature/spec.md) - Reference

  implementation
  implementation

## Contributing

When contributing to agentic-devtools with SDD:

1. Create feature spec first
2. Get spec reviewed and approved
3. Create implementation plan
4. Break down into tasks
5. Implement following the plan
6. Reference spec in PR description
7. Update documentation

This ensures consistency and maintainability across the project.
