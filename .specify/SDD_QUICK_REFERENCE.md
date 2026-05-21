# SDD Quick Reference

Quick reference for using Spec-Driven Development with agentic-devtools.

## Command Quick Reference

### For AI Assistants

```text
/speckit.agdt:constitution [prompt]    # Update project principles
/speckit.agdt:specify [description]    # Create feature specification
/speckit.agdt:plan [tech-stack]        # Create implementation plan
/speckit.agdt:tasks                    # Generate task list
/speckit.agdt:implement                # Execute implementation
/speckit.agdt:analyze                  # Validate consistency
/speckit.agdt:clarify                  # Clarify requirements
/speckit.agdt:checklist                # Generate quality checklist
```

### For Manual Use

The scripts below are available from the extension package at
`.specify/extensions/agdt-workflows/scripts/`:
they consume templates from `.specify/presets/agdt-templates/templates/`.

```bash
# Create new feature (pass the GitHub issue number)
.specify/extensions/agdt-workflows/scripts/bash/create-new-feature.sh --issue 1175 "feature-name"

# Check prerequisites
.specify/extensions/agdt-workflows/scripts/bash/check-prerequisites.sh

# Setup plan
.specify/extensions/agdt-workflows/scripts/bash/setup-plan.sh

# Update agent context
.specify/extensions/agdt-workflows/scripts/bash/update-agent-context.sh
```

### Package Management (Post-Migration)

> **Command namespacing**: AGDT-customized commands use the `agdt:` prefix
> (e.g., `/speckit.agdt:plan`, `/speckit.agdt:tasks`) to avoid collisions with
> core spec-kit commands.

```bash
# Optional: refresh/apply local extension + preset config from .specify/config.yml
specify install

# Check compatibility and health
specify doctor

# Upgrade spec-kit core (does not change extension/preset)
specify upgrade
```

## Directory Structure

```text
.specify/
├── config.yml                   # References local extension + preset
├── extensions/
│   └── agdt-workflows/          # Extension package
│       ├── extension.yml        # Extension manifest
│       ├── commands/            # AI command workflows
│       └── scripts/             # Helper scripts
│           ├── bash/            # Linux/macOS
│           └── powershell/      # Windows
├── presets/
│   └── agdt-templates/          # Preset package
│       ├── preset.yml           # Preset manifest
│       └── templates/           # Document templates
├── memory/constitution.md       # Project governance
├── memory/markdown-rules.md     # Markdown formatting rules
└── SDD_QUICK_REFERENCE.md       # This file

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
/speckit.agdt:constitution Update testing to require 95% coverage
```

### 2. Create Feature Spec

```bash
# Manual (pass the GitHub issue number)
.specify/extensions/agdt-workflows/scripts/bash/create-new-feature.sh --issue 42 "webhook-support"
# Creates branch 42-webhook-support and specs/42-webhook-support/

# Or via AI
/speckit.agdt:specify Add webhook support for Jira events
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
/speckit.agdt:plan
Technology: Python 3.11, Click, Requests
Architecture: Event-driven webhook handler
Storage: Redis for event queue
```

### 5. Generate Tasks

```text
/speckit.agdt:tasks
```

Organizes tasks by user story for independent implementation.

### 6. Implement

```text
/speckit.agdt:implement
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

- Specification: `.specify/presets/agdt-templates/templates/spec-template.md`
- Plan: `.specify/presets/agdt-templates/templates/plan-template.md`
- Tasks: `.specify/presets/agdt-templates/templates/tasks-template.md`
- Checklist: `.specify/presets/agdt-templates/templates/checklist-template.md`

## Documentation

- **Full Guide**: `SPEC_DRIVEN_DEVELOPMENT.md`
- **Specs Guide**: `specs/README.md`
- **Constitution**: `.specify/memory/constitution.md`
- **Command Workflows**: `.specify/extensions/agdt-workflows/commands/`

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
- [AGDT Extension](.specify/extensions/agdt-workflows/) — Commands and scripts (local monorepo package)
- [AGDT Preset](.specify/presets/agdt-templates/) — Template overrides (local monorepo package)
- [Migration Inventory](../docs/speckit-migration-inventory.md) — File categorization
