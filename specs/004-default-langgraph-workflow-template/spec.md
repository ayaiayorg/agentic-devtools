# Feature Specification: Add default LangGraph workflow template generation

**Source Issue**: #976 (https://github.com/ayaiayorg/agentic-devtools/issues/976)
**Feature Branch**: `004-default-langgraph-workflow-template`
**Created**: 2026-03-23
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - [Primary User Goal] (Priority: P1)

## Summary

Create a workflow template generation module that produces starter LangGraph workflow configuration files during `agdt-setup`. Templates reference the existing `agentic_devtools/orchestration/` patterns (state schema, graph builder, pilot workflow) and are written to a user-accessible location for customization.

## Context

- **Parent issue:** [#944 — Improve agdt-setup with platform detection, pluggable issue management, and workflow templates](https://github.com/ayaiayorg/agentic-devtools/issues/944)
- **Grandparent issue:** [#859 — Integrate selected orchestration framework to replace workflow engine and refactor core](https://github.com/ayaiayorg/agentic-devtools/issues/859)
- The orchestration module already exists at `agentic_devtools/orchestration/` with `graph_builder.py`, `state_schema.py`, `pilot_workflow.py`, and `checkpointing.py`
- Currently there is no way for users to get started with a custom workflow — they must write graph definitions from scratch
- Templates should provide a "batteries included" starting point that users can modify

## Scope

**In scope:**
- Create `agentic_devtools/cli/setup/workflow_templates.py` with:
  - `generate_default_templates(target_dir: Path, overwrite: bool = False) -> list[Path]` — writes template files
  - `list_available_templates() -> list[TemplateInfo]` — returns metadata about bundled templates
- Bundled template files in `agentic_devtools/cli/setup/templates/`:
  - `work-on-issue.py` — starter workflow graph (based on existing pilot workflow pattern)
  - `review-pr.py` — starter PR review workflow template
  - `README.md` — documentation explaining how to customize templates
- No-clobber behavior: skip existing files unless `overwrite=True`
- Templates should be valid Python that users can run/import directly
- 100% test coverage on all new code

**Out of scope:**
- Configuration schema (Sub-issue 1 — prerequisite)
- Platform detection (Sub-issue 2)
- Issue adapters (Sub-issue 3)
- Integration into `agdt-setup` (Sub-issue 5)
- Runtime execution of templates (templates are generated files, not executed during setup)

## Dependencies

- **Sub-issue 1** must be completed first (reads config for workflow customization settings)
- Depends on the existing `agentic_devtools/orchestration/` module (already shipped as part of parent #859 Sub-issue 1)

## Affected Files

- `agentic_devtools/cli/setup/workflow_templates.py` — new: generation logic
- `agentic_devtools/cli/setup/templates/work-on-issue.py` — new: bundled template
- `agentic_devtools/cli/setup/templates/review-pr.py` — new: bundled template
- `agentic_devtools/cli/setup/templates/README.md` — new: template documentation
- `tests/unit/cli/setup/test_workflow_templates.py` — new: generation tests, no-clobber tests, template listing tests

**Why this priority**: This is the primary functionality requested in the issue.

**Independent Test**: [NEEDS CLARIFICATION: Define how to test this feature independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### Edge Cases

- [NEEDS CLARIFICATION: What edge cases should be considered?]

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST [primary capability from issue description]

### Non-Functional Requirements

- **NFR-001**: [NEEDS CLARIFICATION: Define performance/reliability requirements]

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: [Define measurable success criteria]

---

*This specification was automatically generated from GitHub issue #976. Please review and refine before proceeding to the planning phase.*
