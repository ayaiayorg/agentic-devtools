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
.specify/scripts/bash/create-new-feature.sh --issue 42 "add-webhook-support"

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

> **Note**: The command names below (e.g., `/speckit.plan`) reflect the
> current pre-migration setup. After migration, AGDT-specific commands
> will be namespaced as `/speckit.agdt:<command>` — see
> [Extension & Preset Architecture](#extension--preset-architecture).

AI assistants can use the `/speckit.plan` command:

```text
/speckit.plan
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

Use `/speckit.tasks` to generate task list:

```text
/speckit.tasks
```

This creates `specs/ISSUE-feature-name/tasks.md` with:

- Tasks organized by user story
- Parallel execution markers [P]
- Exact file paths
- Dependencies clearly marked

### 6. Implement

Execute the implementation:

```text
/speckit.implement
```

AI assistant will:

- Follow the task list
- Reference the spec for requirements
- Check against the plan
- Run tests continuously
- Update documentation

## Extension & Preset Architecture

The SDD infrastructure uses a **split-package model** to maintain upstream
spec-kit compatibility while preserving AGDT-specific customizations:

> **Placeholder links**: The `speckit-ext-agdt` and `speckit-preset-agdt`
> repositories listed below are not yet created (see T001/T002 and T016/T017
> in the migration tasks). Links may 404 until those tasks are completed.

| Package | Repository | Purpose |
|---------|-----------|---------|
| spec-kit core | [github/spec-kit](https://github.com/github/spec-kit) | Base SDD framework (upstream) |
| `speckit-ext-agdt` | [ayaiayorg/speckit-ext-agdt](https://github.com/ayaiayorg/speckit-ext-agdt) | AGDT commands and scripts |
| `speckit-preset-agdt` | [ayaiayorg/speckit-preset-agdt](https://github.com/ayaiayorg/speckit-preset-agdt) | AGDT template overrides |

Version pins are declared in `.specify/config.yml` for reproducible builds.
See [#1408](https://github.com/ayaiayorg/agentic-devtools/issues/1408) for
current migration status.

### Installation & Setup (Post-Migration)

> **Not yet available**: The steps below require the extension and preset
> packages to be published (see T016/T017 in the migration tasks). Until
> then, use the repo-local scripts in `.specify/scripts/` and templates
> in `.specify/templates/` directly.

After cloning agentic-devtools, install the extension and preset:

```bash
# Install spec-kit core (if not already installed)
npm install -g @github/spec-kit

# Install the AGDT extension and preset (reads .specify/config.yml)
specify install
```

This installs the pinned versions of both packages. After migration,
AGDT-specific commands will be namespaced with an `agdt:` prefix
(e.g., `/speckit.agdt:plan`, `/speckit.agdt:tasks`) to avoid collision
with spec-kit core commands (see T007/T010/T019 in the migration tasks).
The AGDT extension adds custom scripts and lifecycle hooks invoked via
spec-kit's extension system; template overrides from the preset become
available immediately.

### When to Edit Preset vs Local Override

| Scenario | Where to Edit | Why |
|----------|---------------|-----|
| Change applies to all AGDT users | `speckit-preset-agdt` repo → publish new version | Shared improvement |
| Change is specific to your fork/branch | Create a local override in `.specify/templates/` | Won't affect others |
| New template section needed | `speckit-preset-agdt` repo | Template structure change |
| One-off experiment | Local `.specify/templates/` override | Temporary, not shared |

**Local overrides**: Place a file with the same name in `.specify/templates/`
to override the preset version. Local files take precedence over preset
templates.

### Upgrade Strategy

#### Upgrading spec-kit core

```bash
# Check for available updates
specify doctor

# Upgrade core (extension/preset versions remain pinned)
specify upgrade
```

Core upgrades do not affect extension or preset files — they are managed
separately via version pins.

#### Upgrading the extension or preset

1. Review the changelog in the package repository
2. Assess breaking changes against current workflows
3. Update the version pin in `.specify/config.yml`:

   ```yaml
   extensions:
     speckit-ext-agdt: "1.1.0"  # Updated from 1.0.0
   ```

4. Run `specify install` to apply the update
5. Run `specify doctor` to verify compatibility
6. Test all SDD commands work correctly

#### Rollback procedure

If an upgrade causes issues, revert the version pin in `.specify/config.yml`
and run `specify install` again.

## Repository SDD Assets

> **Transition note**: The extension and preset packages (`speckit-ext-agdt`,
> `speckit-preset-agdt`) are not yet published. Until they are, the
> `.specify/templates/` and `.specify/scripts/` directories remain the
> canonical source for all templates and commands. Once the packages are
> published and installed via `specify install`, the repo-local files will be
> superseded and can be removed (see Phase 9 in the migration tasks).

The `.specify/` directory contains local per-project configuration and memory.
After migration, commands and templates will be managed by the extension and
preset packages:

```text
.specify/
├── config.yml               # Version pins for extension + preset
├── memory/
│   ├── constitution.md      # Project principles and governance
│   └── markdown-rules.md    # Markdown formatting rules
├── SDD_QUICK_REFERENCE.md   # Quick reference (local docs)
├── templates/               # Template overrides (preset provides defaults)
│   ├── spec-template.md     # Feature specification template
│   ├── plan-template.md     # Implementation plan template
│   ├── tasks-template.md    # Task breakdown template
│   ├── checklist-template.md
│   └── commands/            # SDD workflow command templates
└── scripts/                 # Helper scripts (bash & PowerShell)
```

### SDD Command Templates (Current, Pre-Migration)

> **Pre-migration commands**: The command names below reflect the current
> repo-local setup. After migration (T007/T010/T019), these will be
> namespaced as `/speckit.agdt:<command>` (e.g., `/speckit.agdt:plan`).
> See [Extension & Preset Architecture](#extension--preset-architecture)
> for details.

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
```

## Documentation Boundaries

- **End‑User entry point**: README.md (must not include Specify references).
- **Developer entry point**: SPEC_DRIVEN_DEVELOPMENT.md (this file).
- **Developer-only**: specs/README.md may link here with labels.
- Cross‑links between sections must include explicit audience labels (e.g.,

  “Developer‑only”, “End‑User”).

## SDD Commands for AI Assistants (Current, Pre-Migration)

> **Pre-migration commands**: The command names below reflect the current
> repo-local setup. After migration (T007/T010/T019), these will be
> namespaced as `/speckit.agdt:<command>` (e.g., `/speckit.agdt:plan`).

These slash commands are available when properly configured:

### Core Workflow

1. **`/speckit.constitution`** - Update project principles

   ```text
   /speckit.constitution Update testing standards to require 95% coverage
   ```

2. **`/speckit.specify`** - Create feature specification

   ```text
   /speckit.specify Build a command that exports Jira issues to CSV format
   ```

3. **`/speckit.plan`** - Create implementation plan

   ```text
   /speckit.plan Use pandas for CSV export, Click for CLI
   ```

4. **`/speckit.tasks`** - Generate task list

   ```text
   /speckit.tasks
   ```

5. **`/speckit.implement`** - Execute implementation

   ```text
   /speckit.implement
   ```

### Quality Assurance

- **`/speckit.analyze`** - Check cross-artifact consistency

  ```text
  /speckit.analyze
  ```

- **`/speckit.checklist`** - Generate quality checklist

  ```text
  /speckit.checklist
  ```

- **`/speckit.clarify`** - Clarify underspecified areas

  ```text
  /speckit.clarify
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
chmod +x .specify/scripts/bash/*.sh
```

### Commands Not Available

Ensure templates are in place:

```bash
ls .specify/templates/commands/
```

### Constitution Conflicts

Review and update constitution:

```bash
vim .specify/memory/constitution.md
```

Run consistency check:

```text
/speckit.analyze
```

## Additional Resources

- [GitHub spec-kit](https://github.com/github/spec-kit) - Official SDD toolkit
- [Spec-Driven Development Guide](https://github.github.io/spec-kit/) - Full documentation
- [Constitution Template](../.specify/templates/commands/constitution.md) - How

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
