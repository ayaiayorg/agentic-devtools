# SDD Quick Reference

Quick reference for using Spec-Driven Development with agentic-devtools.

## Command Quick Reference

### For AI Assistants

```
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

```bash
# Create new feature
.specify/scripts/bash/create-new-feature.sh "feature-name"

# Check prerequisites
.specify/scripts/bash/check-prerequisites.sh

# Setup plan
.specify/scripts/bash/setup-plan.sh

# Update agent context
.specify/scripts/bash/update-agent-context.sh
```

## Directory Structure

```
.specify/
├── memory/constitution.md       # Project governance
├── templates/                   # All SDD templates
│   ├── spec-template.md
│   ├── plan-template.md
│   ├── tasks-template.md
│   └── commands/               # AI command workflows
└── scripts/                    # Helper scripts
    ├── bash/                   # Linux/macOS
    └── powershell/             # Windows

specs/
└── NNN-feature-name/           # Feature directory
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

```
/speckit.constitution Update testing to require 95% coverage
```

### 2. Create Feature Spec

```bash
# Manual
.specify/scripts/bash/create-new-feature.sh "webhook-support"
# Creates branch 002-webhook-support and specs/002-webhook-support/

# Or via AI
/speckit.specify Add webhook support for Jira events
```

### 3. Fill Specification

Edit `specs/NNN-feature-name/spec.md`:

- **User Stories** (P1, P2, P3)
- **Acceptance Criteria** (Given/When/Then)
- **Requirements** (FR-001, NFR-001)
- **Edge Cases**
- **Success Metrics**

### 4. Create Plan

```
/speckit.plan
Technology: Python 3.11, Click, Requests
Architecture: Event-driven webhook handler
Storage: Redis for event queue
```

### 5. Generate Tasks

```
/speckit.tasks
```

Organizes tasks by user story for independent implementation.

### 6. Implement

```
/speckit.implement
```

Executes tasks following the plan.

## File Naming Conventions

- Features: `NNN-feature-name` (001, 002, 003...)
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
dfly-set webhook.event_type "issue_updated"
dfly-set webhook.callback_url "https://example.com/webhook"

# Execute command (background task)
dfly-register-webhook

# Monitor progress
dfly-task-status
```

## Resources

- [GitHub spec-kit](https://github.com/github/spec-kit)
- [Full Documentation](https://github.github.io/spec-kit/)
- [Local Guide](SPEC_DRIVEN_DEVELOPMENT.md)
