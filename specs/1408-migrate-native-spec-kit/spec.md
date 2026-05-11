# Spec: Migrate to native spec-kit core, extracting all customizations into extension and preset packages (restore upstream compatibility)

## Status

Proposed

**Source Issue**: #1408

## Summary

The agentic-devtools repository has heavily customized spec-kit assets directly
in-repo (`.specify/scripts/`, `.specify/templates/commands/`, `.specify/templates/*.md`).
This divergence from upstream spec-kit prevents easy adoption of bugfixes, features, and
security updates. The migration will restore upstream compatibility by extracting all
AGDT-specific customizations into a dedicated extension package and a preset package.

## Problem Statement

Currently, many core spec-kit assets have been heavily customized directly inside this
repository:

- `.specify/scripts/bash/` — feature/scripts generator, agent context management,
  environment checks, shared utility functions
- `.specify/templates/commands/` — custom slash command templates for spec, plan,
  implement, analyze, etc.
- `.specify/templates/*-template.md` — AGDT custom versions of spec/plan/tasks/checklist
  templates
- `.specify/templates/agent-file-template.md` — multi-agent support

This direct-in-repo customization means we diverge from upstream spec-kit's mainline.
The consequences are:

1. **Manual merges needed** for all upstream spec-kit updates
2. **Mixed concerns** — local project-specific concepts (AGDT workflows, agent context,
   test/PR conventions) entangled with generic SDD infrastructure
3. **Risk of missing community improvements** — bugfixes, extensions already available
   from the community are not easily adopted
4. **Duplication of effort** that could be addressed by existing or future
   official/community extensions

## Goals

- Restore full upstream compatibility with spec-kit core for quick upgrades
- Extract all AGDT-specific workflows into a well-defined, versioned extension
- Extract all template enhancements into a dedicated preset package
- Minimize technical debt and manual maintenance burden
- Improve clarity, onboarding, and autonomy for contributors

## Non-Goals

- Rewriting spec-kit core itself
- Removing the `.specify/memory/` directory (remains per-project and local)
- Building a generic spec-kit extension framework (leverage the existing one)
- Automating upstream spec-kit release tracking (manual periodic review is acceptable)
- Migrating away from spec-kit entirely

## Clarifications

### Extension Command Registration

Q: How should extracted extension commands be registered with spec-kit?

A: Follow the official spec-kit extension development guide. Commands are registered via
the extension's manifest file and installed using `specify install`. The extension must
declare its commands in its package metadata so spec-kit can discover them at runtime.

### Reusability Scope

Q: Should the extracted extension/preset be designed for reuse across other repositories,
or is it specific to agentic-devtools?

A: Design for potential reuse but prioritize agentic-devtools needs first. The extension
should be published as a public repository so the community can adopt it if useful. However,
breaking-change decisions should favor this repo's needs over hypothetical external consumers.

### Minimum Core Version

Q: What minimum spec-kit core version should the extension/preset target?

A: Target the latest stable spec-kit release at the time of implementation. Pin the minimum
version in the extension/preset metadata so that incompatible older cores produce a clear
error message during installation.

## User Scenarios & Testing

### US-1 (P1): Upgrade spec-kit core without conflicts

As a developer maintaining agentic-devtools, I want to upgrade spec-kit core to the latest
version without merge conflicts so that I can adopt upstream bugfixes and features quickly.

**Acceptance Criteria**

- AC-1.1: Given the extension/preset are installed, when `specify upgrade` is run, then
  core files update cleanly without conflicts in customized files.
- AC-1.2: Given a new spec-kit release is available, when a developer pulls the update,
  then no manual resolution is needed for files that were previously customized in-repo.

### US-2 (P1): Install extension and preset packages

As a developer setting up a fresh clone of agentic-devtools, I want to install the AGDT
extension and preset with a single command so that I can start using the custom workflows
immediately.

**Acceptance Criteria**

- AC-2.1: Given the extension is published, when `specify install <extension-name>` is
  run, then all AGDT-specific commands become available.
- AC-2.2: Given the preset is published, when the preset is referenced in
  `.specify/config.yml`, then all custom templates are loaded automatically.

### US-3 (P2): Onboard new contributors

As a new contributor to agentic-devtools, I want clear documentation on how to set up
the spec-kit environment so that I can start working without tribal knowledge.

**Acceptance Criteria**

- AC-3.1: Given the README is updated, when a new contributor follows the setup guide,
  then extension and preset are installed within 5 minutes.
- AC-3.2: Given the developer guidelines exist, when a contributor wants to modify a
  template, then they know whether to edit the preset or the local override.

### US-4 (P2): Adopt community extensions

As a developer, I want to evaluate and adopt community spec-kit extensions where they
overlap with our custom scripts so that we reduce maintenance burden.

**Acceptance Criteria**

- AC-4.1: Given the inventory is complete, when a community extension covers ≥80% of
  a custom script's functionality, then that script is replaced by the extension.
- AC-4.2: Given a community extension is adopted, when it receives updates, then those
  updates are available via `specify upgrade` without manual intervention.

### US-5 (P2): Pin extension/preset versions

As a release engineer, I want extension and preset versions pinned in configuration so
that builds are reproducible and upgrades are intentional.

**Acceptance Criteria**

- AC-5.1: Given version pins exist in `.specify/config.yml`, when a newer version is
  released, then the pinned version continues to be used until explicitly updated.
- AC-5.2: Given a pin is updated, when the team reviews the changelog, then they can
  assess breaking changes before merging.

### US-6 (P3): Community adoption of the extension

As an external developer using spec-kit, I want the AGDT extension to be discoverable
in the community catalog so that I can reuse agentic workflow patterns.

**Acceptance Criteria**

- AC-6.1: Given the extension is published, when listed in the community catalog, then
  its README clearly describes capabilities and installation.

### US-7 (P3): Clean up deprecated in-repo assets

As a maintainer, I want all superseded in-repo scripts and templates removed after
migration so that the repository has a single source of truth.

**Acceptance Criteria**

- AC-7.1: Given the migration is complete, when inspecting the `.specify/` directory,
  then only local per-project files remain (memory, config).
- AC-7.2: Given deprecated files are removed, when `specify` commands are run, then
  no warnings about orphaned scripts appear.

## Requirements

### Functional Requirements

| ID | Requirement | Priority | User Story |
|----|-------------|----------|------------|
| FR-001 | Inventory all customized files in `.specify/scripts/` and `.specify/templates/` | P1 | US-1 |
| FR-002 | Categorize each file as extension command, preset template, or local-only | P1 | US-1 |
| FR-003 | Create a spec-kit extension package with proper manifest and command registration | P1 | US-2 |
| FR-004 | Create a spec-kit preset package with template overrides | P1 | US-2 |
| FR-005 | Publish both packages to public repositories | P1 | US-2, US-6 |
| FR-006 | Add installation instructions to developer documentation | P2 | US-3 |
| FR-007 | Add version pins to `.specify/config.yml` for both packages | P2 | US-5 |
| FR-008 | Evaluate community extensions against the inventory for potential replacements | P2 | US-4 |
| FR-009 | Replace custom scripts with community extensions where ≥80% overlap exists | P2 | US-4 |
| FR-010 | Remove all superseded in-repo files after migration is verified | P3 | US-7 |
| FR-011 | Update README with links to extension and preset repositories | P3 | US-6 |
| FR-012 | Document the upgrade strategy for core, extension, and preset | P2 | US-3, US-5 |

### Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-001 | Extension installation must complete in under 30 seconds on a standard connection | P2 |
| NFR-002 | The migration must not break existing specs in the `specs/` directory | P1 |
| NFR-003 | The extension must declare and verify compatibility with a pinned spec-kit core version (the exact version is recorded in the extension manifest and must pass `specify doctor` at CI time) | P1 |
| NFR-004 | Version pins must use exact semver (no ranges) for reproducibility | P2 |
| NFR-005 | The preset must not introduce new dependencies beyond spec-kit core | P2 |
| NFR-006 | Documentation changes must pass markdownlint validation | P3 |

## Edge Cases

| # | Edge Case | Mitigation |
|---|-----------|------------|
| EC-001 | Migration conflict: a file is both a local override and a preset candidate | Categorization step (FR-002) must resolve ambiguity; local overrides take precedence |
| EC-002 | Version mismatch: extension requires newer core than what is installed | Extension manifest declares minimum core version; `specify install` fails with clear error |
| EC-003 | Command collision: extension command name conflicts with core command | Extension commands are namespaced (e.g., `agdt:command-name`) to avoid collisions |
| EC-004 | Partial community extension overlap: extension covers only 50% of a custom script | Keep custom script as extension command; document the gap for future community contribution |
| EC-005 | Upgrade breaks preset: new core version changes template variable API | Version pins protect against unintentional upgrades; changelog review before pin update (AC-5.2) |

## Success Criteria

| ID | Criterion | Measurement |
|----|-----------|-------------|
| SC-001 | `specify upgrade` runs without conflicts on agentic-devtools | Upgrade succeeds cleanly with zero manual merge resolution |
| SC-002 | All existing `specs/` directory content continues to work | All existing spec files parse and render correctly after migration |
| SC-003 | Extension and preset are installable via `specify install` | Fresh clone setup completes successfully following documentation |
| SC-004 | No customized files remain in `.specify/scripts/` or `.specify/templates/` post-migration | Directory audit shows only per-project files (memory, config) |
| SC-005 | Community extensions adopted where applicable | At least one community extension replaces a custom script |
| SC-006 | Version pins are configured and documented | `.specify/config.yml` contains exact version pins for both packages |
| SC-007 | Developer documentation is updated | README and developer guidelines reflect the new architecture |
