# Spec: Monorepo-based spec-kit extension/preset strategy

## Status

Proposed

**Source Issue**: #1444
**Supersedes**: #1408

## Summary

Restructure all AGDT-specific spec-kit customizations (scripts, command templates,
document templates) into local extension and preset packages within this repository,
referenced via relative paths in `.specify/config.yml`. This replaces the separate-repo
strategy proposed in #1408 while reusing its inventory and functional requirements.

## Problem Statement

Issue #1408 identified that in-repo customizations of spec-kit assets create maintenance
burden. Its solution proposed extracting customizations to separate published repositories.
However, investigation revealed that spec-kit supports local path extensions and presets,
eliminating the need for cross-repo coordination while achieving the same architectural
benefits:

1. **Clean separation** — AGDT-specific logic is packaged distinctly from spec-kit core
2. **No cross-repo burden** — no separate repos to version, publish, or coordinate
3. **Atomic changes** — extension/preset changes ship with the code that uses them
4. **Simple setup** — no `specify install` step needed; relative paths resolve locally

## Goals

- Structure scripts and templates as proper spec-kit extension and preset packages
- Reference them via relative paths in `.specify/config.yml`
- Maintain all existing functionality without content changes
- Supersede the separate-repo deployment strategy of #1408
- Enable future community catalog publishing if needed

## Non-Goals

- Rewriting script or template content (move only, no refactoring)
- Publishing to external repositories or registries (can be added later)
- Modifying `.specify/memory/` (stays local and per-project)
- Changes to spec-kit core

## User Scenarios & Testing

### User Story 1 (P1): Local extension/preset resolution

Related Requirements: FR-001, FR-002, FR-003

As a developer working on agentic-devtools, I want the extension and preset to resolve
from local paths so that no external installation step is required.

**Acceptance Criteria**

- AC-1.1: Given `.specify/config.yml` uses relative paths, when spec-kit commands are run,
  then scripts and templates resolve from the local packages.
- AC-1.2: Given the packages are in-repo, when a fresh clone is made, then the extension
  and preset are immediately available without `specify install`.

### User Story 2 (P1): Preserve existing functionality

Related Requirements: FR-001, FR-004

As a developer, I want all existing scripts and templates to work identically after the
restructure so that no workflows are broken.

**Acceptance Criteria**

- AC-2.1: Given scripts are moved to the extension package, when referenced by spec-kit,
  then they execute identically to their previous locations.
- AC-2.2: Given templates are moved to the preset package, when spec-kit renders them,
  then output is unchanged.

### User Story 3 (P2): Clear package boundaries

Related Requirements: FR-002, FR-005

As a contributor, I want to understand which package owns which files so that I know
where to make changes.

**Acceptance Criteria**

- AC-3.1: Given the extension manifest exists, when a contributor reads it, then they
  can identify all commands and scripts owned by the extension.
- AC-3.2: Given the preset manifest exists, when a contributor reads it, then they can
  identify all templates owned by the preset.

### User Story 4 (P3): Future community publishing

Related Requirements: FR-006

As a maintainer, I want the packages structured correctly so that they can be published
to the community catalog later without restructuring.

**Acceptance Criteria**

- AC-4.1: Given the packages follow spec-kit packaging conventions, when publishing is
  desired, then only a registry submission is needed (no restructuring).

## Requirements

### Functional Requirements

| ID | Requirement | Priority | User Story |
|----|-------------|----------|------------|
| FR-001 | Move all scripts from `.specify/scripts/` into extension package at `.specify/extensions/agdt-workflows/scripts/` | P1 | US1, US2 |
| FR-002 | Move all command templates from `.specify/templates/commands/` into extension package at `.specify/extensions/agdt-workflows/commands/` | P1 | US1, US3 |
| FR-003 | Update `.specify/config.yml` to reference extension and preset via relative paths | P1 | US1 |
| FR-004 | Move all document templates from `.specify/templates/` into preset package at `.specify/presets/agdt-templates/templates/` | P1 | US2, US3 |
| FR-005 | Create manifest/metadata files for both packages | P2 | US3 |
| FR-006 | Structure packages to be compatible with future community catalog publishing | P3 | US4 |

### Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-001 | Migration must not alter script or template content (move only) | P1 |
| NFR-002 | Existing specs in `specs/` must continue to work | P1 |
| NFR-003 | `.specify/memory/` must remain untouched | P1 |
| NFR-004 | Documentation changes must pass markdownlint validation | P3 |

## Edge Cases

| # | Edge Case | Mitigation |
|---|-----------|------------|
| EC-001 | Relative path resolution differs across OS | Use POSIX-style paths (forward slashes) in config.yml |
| EC-002 | Script references use old paths | Update any internal cross-references during move |
| EC-003 | markdownlint config in commands/ uses relative extends | Update path in moved .markdownlint.json |
| EC-004 | vscode-settings.json references old script paths | Update auto-approve paths to new locations |

## Success Criteria

| ID | Criterion | Measurement |
|----|-----------|-------------|
| SC-001 | All scripts available from extension package | Scripts exist at new paths and are executable |
| SC-002 | All templates available from preset package | Templates exist at new paths |
| SC-003 | Config references local packages | `.specify/config.yml` uses relative paths |
| SC-004 | No content changes to moved files | Diff shows only path changes, not content changes |
| SC-005 | Original directories cleaned up | `.specify/scripts/` and `.specify/templates/` removed |
