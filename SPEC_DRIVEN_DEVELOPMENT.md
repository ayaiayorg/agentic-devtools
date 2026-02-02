# Spec-Driven Development Guide

This guide explains how to use Spec-Driven Development (SDD) with agentic-devtools.

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
- Test-driven development
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
```

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

```
/speckit.plan
Technology stack:
- Python 3.11+
- Click for CLI
- Background task execution
- State-based parameter passing
```

This creates `specs/NNN-feature-name/plan.md` with:
- Technical context
- Architecture decisions
- Project structure
- Dependencies
- Constitution compliance check

### 5. Break Down into Tasks

Use `/speckit.tasks` to generate task list:

```
/speckit.tasks
```

This creates `specs/NNN-feature-name/tasks.md` with:
- Tasks organized by user story
- Parallel execution markers [P]
- Exact file paths
- Dependencies clearly marked

### 6. Implement

Execute the implementation:

```
/speckit.implement
```

AI assistant will:
- Follow the task list
- Reference the spec for requirements
- Check against the plan
- Run tests continuously
- Update documentation

## Directory Structure

```
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

## SDD Commands for AI Assistants

These slash commands are available when properly configured:

### Core Workflow

1. **`/speckit.constitution`** - Update project principles
   ```
   /speckit.constitution Update testing standards to require 95% coverage
   ```

2. **`/speckit.specify`** - Create feature specification
   ```
   /speckit.specify Build a command that exports Jira issues to CSV format
   ```

3. **`/speckit.plan`** - Create implementation plan
   ```
   /speckit.plan Use pandas for CSV export, Click for CLI
   ```

4. **`/speckit.tasks`** - Generate task list
   ```
   /speckit.tasks
   ```

5. **`/speckit.implement`** - Execute implementation
   ```
   /speckit.implement
   ```

### Quality Assurance

- **`/speckit.analyze`** - Check cross-artifact consistency
  ```
  /speckit.analyze
  ```

- **`/speckit.checklist`** - Generate quality checklist
  ```
  /speckit.checklist
  ```

- **`/speckit.clarify`** - Clarify underspecified areas
  ```
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

### Example 2: Complex Feature

For multi-component features:

```
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

```
/speckit.analyze
```

## Additional Resources

- [GitHub spec-kit](https://github.com/github/spec-kit) - Official SDD toolkit
- [Spec-Driven Development Guide](https://github.github.io/spec-kit/) - Full documentation
- [Constitution Template](../.specify/templates/commands/constitution.md) - How to manage constitution
- [Example Spec](../specs/001-example-feature/spec.md) - Reference implementation

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
