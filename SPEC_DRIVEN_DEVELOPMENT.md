# Spec-Driven Development Guide

This guide explains how to use Spec-Driven Development (SDD) with
agentic-devtools.

**Developer-only**: This guide is intended for AGDT maintainers and
contributors. **End‑User**: [README.md](README.md).

## Audience Labels

Use explicit audience labels when cross‑linking documentation:

- **Developer-only**: Use this label for links intended only for maintainers or

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
```

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
# Create feature branch and directory (pass the GitHub issue number)
.specify/extensions/agdt-workflows/scripts/bash/create-new-feature.sh --issue 42 "add-webhook-support"

# This creates:
# - Branch: 42-add-webhook-support
# - Directory: specs/42-add-webhook-support/
# - File: specs/42-add-webhook-support/spec.md (from template)
```

### 3. Fill Out the Specification

Edit `specs/ISSUE-feature-name/spec.md`:

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

> **Note**: AGDT-specific commands are namespaced as
> `/speckit.agdt:<command>` (for example, `/speckit.agdt:plan`) — see
> [Extension & Preset Architecture](#extension--preset-architecture).

AI assistants can use the `/speckit.agdt:plan` command:

```text
/speckit.agdt:plan
Technology stack:
- Python 3.11+
- Click for CLI
- Background task execution
- State-based parameter passing
```

This creates `specs/ISSUE-feature-name/plan.md` with:

- Technical context
- Architecture decisions
- Project structure
- Dependencies
- Constitution compliance check

### 5. Break Down into Tasks

Use `/speckit.agdt:tasks` to generate task list:

```text
/speckit.agdt:tasks
```

This creates `specs/ISSUE-feature-name/tasks.md` with:

- Tasks organized by user story
- Parallel execution markers [P]
- Exact file paths
- Dependencies clearly marked

### 6. Implement

Execute the implementation:

```text
/speckit.agdt:implement
```

AI assistant will:

- Follow the task list
- Reference the spec for requirements
- Check against the plan
- Run tests continuously
- Update documentation

## Extension & Preset Architecture

The SDD infrastructure uses a **monorepo-based split-package model** to maintain
upstream spec-kit compatibility while preserving AGDT-specific customizations.
Both packages are local to this repository and referenced via relative paths in
`.specify/config.yml` — no external installation or publishing is required.

| Package | Location | Purpose |
|---------|----------|---------|
| spec-kit core | [github/spec-kit](https://github.com/github/spec-kit) | Base SDD framework (upstream) |
| `agdt-workflows` | `.specify/extensions/agdt-workflows/` | AGDT commands and scripts |
| `agdt-templates` | `.specify/presets/agdt-templates/` | AGDT template overrides |

See [#1444](https://github.com/ayaiayorg/agentic-devtools/issues/1444) for the
monorepo strategy rationale.

### Installation & Setup

After cloning agentic-devtools, the extension and preset files are **already
present in the repository** because `.specify/config.yml` uses relative paths
that resolve to the in-repo packages:

```yaml
extensions:
  - "./.specify/extensions/agdt-workflows"

presets:
  - "./.specify/presets/agdt-templates"
```

AGDT-specific commands are namespaced with an `agdt:` prefix
(e.g., `/speckit.agdt:plan`, `/speckit.agdt:tasks`) to avoid collision
with spec-kit core commands.

Running `specify install` is therefore **optional**: use it only when you want
the Spec-Kit CLI to refresh/apply the local extension and preset configuration
in your environment. It does not download separate AGDT packages.

### When to Edit Extension or Preset

| Scenario | Where to Edit | Why |
|----------|---------------|-----|
| Change applies to all AGDT users | `.specify/extensions/agdt-workflows/` or `.specify/presets/agdt-templates/` | Shared improvement, versioned in-repo |
| New command template | `.specify/extensions/agdt-workflows/commands/` | Extension command |
| New document template | `.specify/presets/agdt-templates/templates/` | Preset template |
| New helper script | `.specify/extensions/agdt-workflows/scripts/` | Extension script |

### Upgrade Strategy

#### Upgrading spec-kit core

```bash
# Check for available updates
specify doctor

# Upgrade core (local packages remain unchanged)
specify upgrade
```

Core upgrades do not affect the local extension or preset packages — they are
managed as part of this repository.

## Repository SDD Assets

The `.specify/` directory contains local per-project configuration, memory,
and the monorepo-based extension and preset packages:

```text
.specify/
├── config.yml               # References local extension + preset via paths
├── extensions/
│   └── agdt-workflows/      # Extension package (commands + scripts)
│       ├── extension.yml    # Extension manifest
│       ├── commands/        # AI command templates
│       └── scripts/         # Helper scripts (bash + powershell)
├── presets/
│   └── agdt-templates/      # Preset package (document templates)
│       ├── preset.yml       # Preset manifest
│       └── templates/       # Template overrides
├── memory/
│   ├── constitution.md      # Project principles and governance
│   └── markdown-rules.md    # Markdown formatting rules
└── SDD_QUICK_REFERENCE.md   # Quick reference (local docs)
```

### SDD Command Templates

> AGDT command templates are namespaced as `/speckit.agdt:<command>`
> (for example, `/speckit.agdt:plan`). See
> [Extension & Preset Architecture](#extension--preset-architecture) for details.

AI assistants can use these command templates (in
`.specify/extensions/agdt-workflows/commands/`):

- `/speckit.agdt:constitution` - Update project principles
- `/speckit.agdt:specify` - Create feature specifications
- `/speckit.agdt:plan` - Develop implementation plans
- `/speckit.agdt:tasks` - Generate task lists
- `/speckit.agdt:implement` - Execute implementation
- `/speckit.agdt:analyze` - Validate cross-artifact consistency
- `/speckit.agdt:checklist` - Generate quality checklists

## Directory Structure

```text
agentic-devtools/
├── .specify/                    # SDD infrastructure
│   ├── memory/
│   │   └── constitution.md      # Project principles
│   ├── extensions/
│   │   └── agdt-workflows/      # Extension package
│   │       ├── extension.yml    # Extension manifest
│   │       ├── commands/        # AI command templates
│   │       └── scripts/         # Helper scripts
│   │           ├── bash/        # Linux/macOS scripts
│   │           └── powershell/  # Windows scripts
│   └── presets/
│       └── agdt-templates/      # Preset package
│           ├── preset.yml       # Preset manifest
│           └── templates/       # Document templates
├── specs/                       # Feature specifications
│   ├── 001-example-feature/
│   │   ├── spec.md             # The specification
│   │   ├── plan.md             # Implementation plan
│   │   └── tasks.md            # Task breakdown
│   └── README.md
├── agentic_devtools/           # Source code
└── tests/                      # Test suite
```

## Documentation Boundaries

- **End‑User entry point**: README.md (must not include Specify references).
- **Developer entry point**: SPEC_DRIVEN_DEVELOPMENT.md (this file).
- **Developer-only**: specs/README.md may link here with labels.
- Cross‑links between sections must include explicit audience labels (e.g.,

  “Developer‑only”, “End‑User”).

## SDD Commands for AI Assistants

> AGDT commands are namespaced as `/speckit.agdt:<command>`
> (for example, `/speckit.agdt:plan`).

These slash commands are available when properly configured:

### Core Workflow

1. **`/speckit.agdt:constitution`** - Update project principles

   ```text
   /speckit.agdt:constitution Update testing standards to require 95% coverage
   ```

2. **`/speckit.agdt:specify`** - Create feature specification

   ```text
   /speckit.agdt:specify Build a command that exports Jira issues to CSV format
   ```

3. **`/speckit.agdt:plan`** - Create implementation plan

   ```text
   /speckit.agdt:plan Use pandas for CSV export, Click for CLI
   ```

4. **`/speckit.agdt:tasks`** - Generate task list

   ```text
   /speckit.agdt:tasks
   ```

5. **`/speckit.agdt:implement`** - Execute implementation

   ```text
   /speckit.agdt:implement
   ```

### Quality Assurance

- **`/speckit.agdt:analyze`** - Check cross-artifact consistency

  ```text
  /speckit.agdt:analyze
  ```

- **`/speckit.agdt:checklist`** - Generate quality checklist

  ```text
  /speckit.agdt:checklist
  ```

- **`/speckit.agdt:clarify`** - Clarify underspecified areas

  ```text
  /speckit.agdt:clarify
  ```

## Integration with Existing Workflows

SDD complements existing agentic-devtools workflows:

### State Management

SDD specifications define what state keys are needed:

```markdown
## Requirements

- FR-001: System MUST support export.format state key
- FR-002: System MUST support export.output_file state key
```

Implementation uses standard state pattern:

```bash
agdt-set export.format csv
agdt-set export.output_file issues.csv
agdt-export-jira-issues
```

### Background Tasks

Specifications identify long-running operations:

```markdown
## Non-Functional Requirements

- NFR-001: Export operation MAY take > 30 seconds for large datasets
```

Implementation uses background task pattern:

```python
@background_task_wrapper
def export_jira_issues():
    # Long-running export logic
    pass
```

### Testing

Specifications drive test requirements:

```markdown
## Acceptance Scenarios

1. **Given** 100 Jira issues exist, **When** export runs, 
   **Then** CSV contains 100 rows with correct data
```

Tests verify acceptance criteria:

```python
def test_export_100_issues():
    # Test implementation matching spec
    pass
```

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
```

## Troubleshooting

## Development Environment

### Dev Container

This repository includes a devcontainer configuration for Python development:

- **VS Code**: Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers), then click "Reopen in Container"
- **GitHub Codespaces**: Create a new Codespace - all dependencies will be set

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
```

### Scripts Not Executable

```bash
chmod +x .specify/extensions/agdt-workflows/scripts/bash/*.sh
```

### Commands Not Available

Ensure command templates are in place:

```bash
ls .specify/extensions/agdt-workflows/commands/
```

### Constitution Conflicts

Review and update constitution:

```bash
vim .specify/memory/constitution.md
```

Run consistency check:

```text
/speckit.agdt:analyze
```

## Additional Resources

- [GitHub spec-kit](https://github.com/github/spec-kit) - Official SDD toolkit
- [Spec-Driven Development Guide](https://github.github.io/spec-kit/) - Full documentation
- [Constitution Template](.specify/extensions/agdt-workflows/commands/constitution.md) - How
  to manage constitution

- [Example Spec](../specs/001-example-feature/spec.md) - Reference

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
