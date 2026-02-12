# Create Jira Issue Workflow

You are creating a new issue in project **{{jira_project_key}}**.

## Gathering Information

Before creating the issue, ensure you have:

1. A clear, concise summary
2. A detailed description with context
3. Appropriate issue type (Bug, Story, Task, etc.)
4. Complete acceptance criteria following the guidance below

## Creating the Issue

1. Set the required state:

   ```bash
   agdt-set jira.project_key {{jira_project_key}}
   agdt-set jira.summary "<issue summary>"
   agdt-set jira.description "<detailed description>"
   ```

2. Create the issue:

   ```bash
   agdt-create-issue
   ```

---

## Acceptance Criteria Guidance

**Every issue must have well-defined acceptance criteria.** Use the following
decision trees and checklists to determine what acceptance criteria to include.

### Minimum Expectations

At minimum, every code change issue should address:

- **Test requirements** - What tests are needed to verify the change?
- **Documentation requirements** - What documentation needs to be added or

  updated?
  updated?

If an issue genuinely doesn't require tests or documentation, explicitly state
why in the acceptance criteria (e.g., "No tests required - configuration-only
change with no logic").

---

## Testing Requirements Decision Tree

### Unit Tests

**Include unit test requirements when:**

- [ ] Adding or modifying business logic in domain/application layers
- [ ] Creating new service methods or command handlers
- [ ] Implementing validation rules or guards
- [ ] Fixing bugs (regression test required)
- [ ] Adding helper/utility functions
- [ ] Modifying existing tested code

**Coverage guidance:**

- Target minimum 80% coverage for added/modified files
- Document justification if coverage target cannot be met (e.g., mocking

  complexity, infrastructure-only code)
  complexity, infrastructure-only code)

### E2E Tests

**Include E2E test requirements when:**

- [ ] Adding new UI features, pages, or components
- [ ] Modifying user-facing workflows
- [ ] Adding API endpoints consumed by frontend
- [ ] Changing navigation or routing
- [ ] Implementing new user interactions (buttons, forms, dialogs)

### Integration Tests

**Include integration test requirements when:**

- [ ] Adding new external service integrations
- [ ] Modifying database queries or repositories
- [ ] Changing message handling (Service Bus, RabbitMQ)
- [ ] Implementing new API client calls

---

## Documentation Requirements Checklist

### README Updates

**Include README updates when:**

- [ ] Adding new setup steps or prerequisites
- [ ] Changing deployment or configuration
- [ ] Adding new features that users need to know about
- [ ] Modifying existing documented workflows

### copilot-instructions.md Updates

**Include instruction file updates when:**

- [ ] Changing patterns that AI agents should follow
- [ ] Adding new domain concepts or terminology
- [ ] Modifying service architecture or conventions
- [ ] Adding new file organization patterns

### API Documentation

**Include API documentation when:**

- [ ] Adding new endpoints
- [ ] Modifying request/response schemas
- [ ] Changing authentication or authorization
- [ ] Deprecating or removing endpoints

### Mermaid Diagrams

**Include diagram requirements when:**

- [ ] Implementing complex multi-step processes
- [ ] Adding flows involving multiple systems
- [ ] Creating entry points for dataproduct, outport, or subscription workflows
- [ ] Modifying system integration patterns

Place diagrams in the same directory (or parent) as the code they document.

---

## CI/CD Requirements Checklist

### Pipeline Changes

**Include pipeline considerations when:**

- [ ] Adding new build dependencies
- [ ] Requiring new test stages
- [ ] Adding new deployment targets
- [ ] Modifying artifact generation

### Environment Configuration

**Include environment config when:**

- [ ] Adding new environment variables
- [ ] Requiring new secrets in Key Vault
- [ ] Adding new connection strings
- [ ] Modifying configuration schema

### Coverage Threshold Enforcement

**For all code changes:**

1. Check if affected code area has coverage threshold in CI
2. If no threshold exists:

   - Run coverage analysis on current codebase
   - Add threshold set to current coverage (rounded down to nearest integer)

3. After completing changes:
4. After completing changes:

   - Run coverage analysis again
   - Update threshold to new coverage (rounded down to nearest integer)

---

## Codebase Analysis Requirement

Before finalizing acceptance criteria, analyze the relevant part(s) of the
codebase and include gathered context in the issue's **Additional Information**
section:

- **Existing patterns** - What conventions are used in the affected area?
- **Related components** - What other files or services are involved?
- **Dependencies** - What must this code integrate with?
- **Potential risks** - What edge cases or failure modes exist?
- **Architectural considerations** - How does this fit the overall design?

---

## Acceptance Criteria Examples

### Example: New Business Logic Feature

```none
h3. +Acceptance Criteria+
# Domain: Add {{Dataproduct.UpdateDescription()}} method with validation
# Application: Add {{DataproductCommands.UpdateDescriptionAsync()}} orchestration
# Unit tests: Achieve 80%+ coverage for new domain and application code
# E2E tests: Not required (no UI changes)
# Documentation: Update {{mgmt-backend/.github/copilot-instructions.md}} with new pattern
# CI/CD: Verify existing coverage thresholds pass after changes
```

### Example: New UI Feature

```none
h3. +Acceptance Criteria+
# Component: Create {{DataproductDescriptionEditor}} component
# Integration: Wire up to {{DataproductViewComponent}} with state management
# Unit tests: 80%+ coverage for new component logic
# E2E tests: Add page object and spec for description editing workflow
# Documentation: Add data-test selectors following selector taxonomy
# API: Endpoint already exists (no backend changes needed)
```

### Example: Bug Fix

```none
h3. +Acceptance Criteria+
# Fix: Correct null reference in {{OutportService.GetVersionAsync()}}
# Regression test: Add unit test reproducing the null scenario
# Root cause: Document in PR description why the bug occurred
# Coverage: Maintain or improve existing coverage threshold
```

### Example: Infrastructure/Configuration Change

```none
h3. +Acceptance Criteria+
# Terraform: Add new subnet for {{jira-consumer}} app
# Variables: Add {{jira_api_token}} to variable group {{VG_WB_TESR_SETTINGS}}
# Documentation: Update {{wb-infra/README.md}} with new resource
# No unit tests required (infrastructure-only change)
```

---

## Issue Format Templates

### For User Stories

```none
*As a* <role>,
*I want* <desired outcome>,
*so that* <benefit>.

h3. +Acceptance Criteria+
# <criterion derived from decision trees above>
# <criterion derived from decision trees above>

h3. +Background+
<context and motivation>

h3. +Additional Information+
* Existing patterns in affected area: <patterns>
* Related components: <components>
* Potential risks: <risks>
```

### For Bug Reports

```none
h3. +Problem+
<description of the bug>

h3. +Steps to Reproduce+
# Step 1
# Step 2

h3. +Expected Behavior+
<what should happen>

h3. +Actual Behavior+
<what actually happens>

h3. +Acceptance Criteria+
# Fix the identified issue
# Add regression test covering the failure scenario
# Document root cause in PR description

h3. +Additional Information+
* Environment: <env details>
* Logs/Screenshots: <evidence>
```

### For Tasks

```none
h3. +Objective+
<clear scope of work>

h3. +Acceptance Criteria+
# <specific deliverable 1>
# <specific deliverable 2>
# <test requirements per decision tree>
# <documentation requirements per checklist>

h3. +Additional Information+
* Dependencies: <dependencies if any>
* Related issues: <linked issues>
```

---

## After Creation

The command will output the new issue key. Use it to:

- Link related issues
- Create subtasks if needed
- Assign to appropriate team member

## Quality Check

Before finalizing the issue, verify:

- [ ] Summary is clear and actionable
- [ ] Description follows appropriate template
- [ ] Acceptance criteria address testing requirements
- [ ] Acceptance criteria address documentation requirements
- [ ] CI/CD considerations are noted if applicable
- [ ] Codebase analysis insights are included in Additional Information
