# Feature Specifications

This directory contains feature specifications following the
Spec-Driven Development (SDD) methodology.

**Developer-only**: This directory is intended for AGDT maintainers
and contributors. See the [Spec-Driven Development
Guide](../SPEC_DRIVEN_DEVELOPMENT.md) (Developer-only).

## Directory Structure

Each feature has its own numbered directory:

```text
specs/
├── 001-example-feature/
│   ├── spec.md              # Feature specification (mandatory)
│   ├── plan.md              # Implementation plan (created by /speckit.plan)
│   ├── tasks.md             # Task breakdown (created by /speckit.tasks)
│   ├── research.md          # Technical research (auto-generated)
│   ├── data-model.md        # Data models (auto-generated)
│   ├── quickstart.md        # Quick start guide (auto-generated)
│   └── contracts/           # API contracts (auto-generated)
├── 002-another-feature/
│   └── spec.md
└── README.md                # This file
```

## Feature Numbering

Features are numbered sequentially (001, 002, 003, etc.) to:

- Maintain chronological order
- Enable easy reference in commits and PRs
- Track feature evolution over time

## Creating a New Feature

Use the helper script to create a new feature:

```bash
# Bash/Linux/macOS
.specify/scripts/bash/create-new-feature.sh "your-feature-name"

# PowerShell/Windows
.specify/scripts/powershell/create-new-feature.ps1 "your-feature-name"
```

This will:

1. Create a new feature branch: `NNN-your-feature-name`
2. Create the specs directory: `specs/NNN-your-feature-name/`
3. Initialize with spec template
4. Update agent context

## SDD Workflow

1. **Specify** (`spec.md`) - Define what to build
   - User stories with priorities
   - Acceptance criteria
   - Requirements
   - Success metrics

2. **Plan** (`plan.md`) - Decide how to build it
   - Technical context
   - Architecture decisions
   - Project structure
   - Dependencies

3. **Tasks** (`tasks.md`) - Break down the work
   - Organized by user story
   - Independent tasks
   - Parallel execution opportunities

4. **Implement** - Execute the tasks
   - Follow the plan
   - Reference the spec
   - Update documentation

## Example Feature

See `001-example-feature/` for a complete example demonstrating:

- Well-structured user stories with priorities
- Clear acceptance criteria
- Functional and non-functional requirements
- Edge cases consideration

## Best Practices

### User Stories

- Prioritize as P1, P2, P3, etc.
- Each story should be independently testable
- Focus on user value, not technical implementation
- Include clear acceptance scenarios

### Requirements

- Use MUST/SHOULD/MAY consistently
- Number requirements (FR-001, NFR-001, etc.)
- Mark unclear items with [NEEDS CLARIFICATION]
- Keep requirements testable and measurable

### Plans

- Define technical context clearly
- Document architecture decisions
- Specify project structure
- List all dependencies

### Tasks

- Group by user story for independent delivery
- Mark parallel tasks with [P]
- Include exact file paths
- Estimate complexity where helpful

## Integration with AI Assistants

AI assistants can use these specifications through slash commands:

```text
/speckit.constitution - Update project principles
/speckit.specify - Create feature specifications
/speckit.plan - Develop implementation plans
/speckit.tasks - Generate task lists
/speckit.implement - Execute implementation
```

See `.specify/templates/commands/` for detailed command workflows.
