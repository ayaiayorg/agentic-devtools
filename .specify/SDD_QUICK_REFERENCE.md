# SDD Quick Reference

Quick reference for using Spec-Driven Development with agentic-devtools.

## Command Quick Reference

### For AI Assistants

```text
/speckit.constitution [prompt]    # Update project principles
/speckit.specify [description]    # Create feature specification
/speckit.plan [tech-stack]        # Create implementation plan
/speckit.tasks                    # Generate task list
/speckit.implement                # Execute implementation
/speckit.analyze                  # Validate consistency
/speckit.clarify                  # Clarify requirements
/speckit.checklist                # Generate quality checklist
```

### For Manual Use

> **Transition note**: The scripts below are repo-local helpers that remain
> available today. Once the extension package (`speckit-ext-agdt`) is published
> and installed via `specify install`, these scripts will be superseded by
> the extension's built-in commands.

```bash
# Create new feature (pass the GitHub issue number)
.specify/scripts/bash/create-new-feature.sh --issue 1175 "feature-name"

# Check prerequisites
.specify/scripts/bash/check-prerequisites.sh

# Setup plan
.specify/scripts/bash/setup-plan.sh

# Update agent context
.specify/scripts/bash/update-agent-context.sh
```

### Package Management (Post-Migration)

> **Command namespacing**: After migration, AGDT-customized commands will
> use the `agdt:` prefix (e.g., `/speckit.agdt:plan`, `/speckit.agdt:tasks`)
> instead of the current `/speckit.plan`, `/speckit.tasks` names. See
> T007/T010/T019 in the migration tasks for details.

```bash
# Install extension + preset (reads .specify/config.yml)
specify install

# Check compatibility and health
specify doctor

# Upgrade spec-kit core (does not change extension/preset)
specify upgrade
```

## Directory Structure

```text
.specify/
├── config.yml                   # Version pins for extension + preset
├── memory/constitution.md       # Project governance
├── memory/markdown-rules.md     # Markdown formatting rules
├── SDD_QUICK_REFERENCE.md       # This file
├── templates/                   # Template overrides (preset provides defaults)
│   ├── spec-template.md
│   ├── plan-template.md
│   ├── tasks-template.md
│   └── commands/               # AI command workflows
└── scripts/                    # Helper scripts
    ├── bash/                   # Linux/macOS
    └── powershell/             # Windows

specs/
└── ISSUE-feature-name/           # Feature directory (ISSUE = GitHub issue number)
    ├── spec.md                 # Specification (mandatory)
    ├── plan.md                 # Implementation plan
    ├── tasks.md                # Task breakdown
    ├── research.md             # Auto-generated research
    ├── data-model.md           # Auto-generated models
    └── contracts/              # Auto-generated contracts
```

## Workflow Steps

### 1. Define Principles (Once)

Review and update project constitution:

```bash
cat .specify/memory/constitution.md
```

Or via AI:

```text
/speckit.constitution Update testing to require 95% coverage
```

### 2. Create Feature Spec

```bash
# Manual (pass the GitHub issue number)
.specify/scripts/bash/create-new-feature.sh --issue 42 "webhook-support"
# Creates branch 42-webhook-support and specs/42-webhook-support/

# Or via AI
/speckit.specify Add webhook support for Jira events
```

### 3. Fill Specification

Edit `specs/ISSUE-feature-name/spec.md`:

- **User Stories** (P1, P2, P3)
- **Acceptance Criteria** (Given/When/Then)
- **Requirements** (FR-001, NFR-001)
- **Edge Cases**
- **Success Metrics**

### 4. Create Plan

```text
/speckit.plan
Technology: Python 3.11, Click, Requests
Architecture: Event-driven webhook handler
Storage: Redis for event queue
```

### 5. Generate Tasks

```text
/speckit.tasks
```

Organizes tasks by user story for independent implementation.

### 6. Implement

```text
/speckit.implement
```

Executes tasks following the plan.

## File Naming Conventions

- Features: `ISSUE-feature-name` (e.g., `1175-plan-phase-fails-large`)
- Requirements: `FR-001`, `NFR-001` (Functional/Non-functional)
- Priorities: `P1`, `P2`, `P3` (High to Low)
- Parallel Tasks: `[P]` marker in task list

## Key Principles

From `.specify/memory/constitution.md`:

1. **Auto-Approval Friendly** - Commands designed for AI assistants
2. **Single Source of Truth** - One JSON state file
3. **Background Tasks** - Long operations run async
4. **Test-Driven** - 95% coverage required
5. **Python Best Practices** - Standard packaging, type hints

## Common Patterns

### User Story Format

```markdown
### User Story N - Title (Priority: PN)

As a [role], I want to [action], so that [benefit].

**Why this priority**: [Explanation]

**Independent Test**: [How to verify standalone]

**Acceptance Scenarios**:
1. **Given** [state], **When** [action], **Then** [result]
```

### Requirement Format

```markdown
- **FR-001**: System MUST [capability]
- **NFR-001**: Response time MUST be < 100ms
- **FR-002**: Users MUST be able to [action]
```

### Task Format

```markdown
- [ ] T001 [P] Create base webhook handler (src/webhooks/handler.py)
- [ ] T002 [US1] Add Jira webhook parsing (src/webhooks/jira.py)
```

## Template Locations

- Specification: `.specify/templates/spec-template.md`
- Plan: `.specify/templates/plan-template.md`
- Tasks: `.specify/templates/tasks-template.md`
- Checklist: `.specify/templates/checklist-template.md`

## Documentation

- **Full Guide**: `SPEC_DRIVEN_DEVELOPMENT.md`
- **Specs Guide**: `specs/README.md`
- **Constitution**: `.specify/memory/constitution.md`
- **Command Workflows**: `.specify/templates/commands/*.md`

## Example

See `specs/001-example-feature/spec.md` for a complete example.

## Tips

✅ **Do:**

- Start with spec before any code
- Make user stories independently testable
- Include edge cases
- Define success metrics
- Check constitution compliance

❌ **Don't:**

- Skip specification phase
- Mix implementation details in spec
- Create dependent user stories
- Ignore non-functional requirements

## Integration with agentic-devtools

SDD complements existing commands:

```bash
# Set state from spec requirements
agdt-set webhook.event_type "issue_updated"
agdt-set webhook.callback_url "https://example.com/webhook"

# Execute command (background task)
agdt-register-webhook

# Monitor progress
agdt-task-status
```

## Resources

- [GitHub spec-kit](https://github.com/github/spec-kit)
- [Full Documentation](https://github.github.io/spec-kit/)
- [Local Guide](../SPEC_DRIVEN_DEVELOPMENT.md)
- [AGDT Extension](https://github.com/ayaiayorg/speckit-ext-agdt) — Commands and scripts
- [AGDT Preset](https://github.com/ayaiayorg/speckit-preset-agdt) — Template overrides
- [Migration Inventory](../docs/speckit-migration-inventory.md) — File categorization

> **Note**: The AGDT Extension and Preset links above are placeholder
> repositories that may 404 until published (see T016/T017 in the
> [migration issue](https://github.com/ayaiayorg/agentic-devtools/issues/1408)).
