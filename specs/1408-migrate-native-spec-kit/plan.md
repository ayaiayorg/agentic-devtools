# Implementation Plan: Migrate to Native Spec-Kit Core

**Source Issue**: #1408
**Date**: 2026-05-12

## Summary

Extract all AGDT-specific customizations from `.specify/` into two external packages —
an **extension** (commands + scripts) and a **preset** (templates) — then replace in-repo
files with a clean spec-kit core installation that references these packages via
`.specify/config.yml` version pins.

## Technical Context

**Tooling**: spec-kit CLI (`specify` command), bash/powershell scripts, markdown templates
**Package Format**: spec-kit extension manifest + preset manifest (per spec-kit extension guide)
**Hosting**: Public GitHub repositories under `ayaiayorg` organization
**CI**: Existing PR checks pipeline (`scripts/run-pr-checks.sh`), markdownlint
**State**: No runtime Python code changes — this is a packaging/configuration migration
**Existing Specs**: 20+ feature specs in `specs/` that must continue working post-migration

## Research Summary

Key design decisions made during research:

- Extension vs preset boundary (what goes where)
- Naming conventions for the two packages
- Command namespacing strategy
- Version pinning approach
- Community extension evaluation criteria

## Design Overview

```text
┌─────────────────────────────────────────────────────────┐
│  agentic-devtools repository                            │
│                                                         │
│  .specify/                                              │
│  ├── config.yml          ← pins extension + preset      │
│  ├── memory/             ← local, per-project (stays)   │
│  │   ├── constitution.md                                │
│  │   └── markdown-rules.md                              │
│  └── (no scripts/ or templates/ — managed by packages)  │
│                                                         │
│  specs/                  ← unchanged feature specs       │
└─────────────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
┌─────────────────────┐   ┌──────────────────────────┐
│ speckit-ext-agdt    │   │ speckit-preset-agdt      │
│ (extension package) │   │ (preset package)         │
│                     │   │                          │
│ • commands/         │   │ • spec-template.md       │
│   specify.md        │   │ • plan-template.md       │
│   plan.md           │   │ • tasks-template.md      │
│   tasks.md          │   │ • checklist-template.md   │
│   implement.md      │   │ • agent-file-template.md  │
│   analyze.md        │   │ • vscode-settings.json   │
│   clarify.md        │   └──────────────────────────┘
│   checklist.md      │
│   constitution.md   │
│   taskstoissues.md  │
│ • scripts/          │
│   bash/             │
│   powershell/       │
└─────────────────────┘
```

## Implementation Phases

### Phase 0: Inventory & Categorization (FR-001, FR-002)

**Deliverables**: Complete inventory document, categorization decisions

| # | Task | Details |
|---|------|---------|
| 0.1 | Audit all files in `.specify/scripts/` | 10 files, ~2805 lines total (5 bash, 5 powershell) |
| 0.2 | Audit all files in `.specify/templates/` | 16 files total: 9 command `.md` files + `.markdownlint.json` in `commands/`, 5 template `.md` files + `vscode-settings.json` at root |
| 0.3 | Categorize each file | Extension command, preset template, or local-only |
| 0.4 | Document AGDT-specific vs generic logic | Identify tight couplings to agentic-devtools concepts |
| 0.5 | Evaluate community extensions (FR-008) | Search spec-kit ecosystem for overlapping functionality |

**Categorization (preliminary based on exploration):**

| File | Category | Package |
|------|----------|---------|
| `.specify/scripts/bash/create-new-feature.sh` | Extension script | speckit-ext-agdt |
| `.specify/scripts/bash/update-agent-context.sh` | Extension script | speckit-ext-agdt |
| `.specify/scripts/bash/setup-plan.sh` | Extension script | speckit-ext-agdt |
| `.specify/scripts/bash/check-prerequisites.sh` | Extension script | speckit-ext-agdt |
| `.specify/scripts/bash/common.sh` | Extension script (shared lib) | speckit-ext-agdt |
| `.specify/scripts/powershell/*` (5 files) | Extension script | speckit-ext-agdt |
| `.specify/templates/commands/specify.md` | Extension command | speckit-ext-agdt |
| `.specify/templates/commands/plan.md` | Extension command | speckit-ext-agdt |
| `.specify/templates/commands/tasks.md` | Extension command | speckit-ext-agdt |
| `.specify/templates/commands/implement.md` | Extension command | speckit-ext-agdt |
| `.specify/templates/commands/analyze.md` | Extension command | speckit-ext-agdt |
| `.specify/templates/commands/clarify.md` | Extension command | speckit-ext-agdt |
| `.specify/templates/commands/checklist.md` | Extension command | speckit-ext-agdt |
| `.specify/templates/commands/constitution.md` | Extension command | speckit-ext-agdt |
| `.specify/templates/commands/taskstoissues.md` | Extension command | speckit-ext-agdt |
| `.specify/templates/commands/.markdownlint.json` | Extension config | speckit-ext-agdt |
| `.specify/templates/spec-template.md` | Preset template | speckit-preset-agdt |
| `.specify/templates/plan-template.md` | Preset template | speckit-preset-agdt |
| `.specify/templates/tasks-template.md` | Preset template | speckit-preset-agdt |
| `.specify/templates/checklist-template.md` | Preset template | speckit-preset-agdt |
| `.specify/templates/agent-file-template.md` | Preset template | speckit-preset-agdt |
| `.specify/templates/vscode-settings.json` | Preset asset | speckit-preset-agdt |
| `.specify/memory/constitution.md` | Local only | stays in-repo |
| `.specify/memory/markdown-rules.md` | Local only | stays in-repo |
| `.specify/SDD_QUICK_REFERENCE.md` | Local only | stays in-repo |

### Phase 1: Create Extension Package (FR-003, FR-005)

**Deliverables**: `speckit-ext-agdt` repository with working extension

| # | Task | Details |
|---|------|---------|
| 1.1 | Create `ayaiayorg/speckit-ext-agdt` repository | Public repo with README, LICENSE |
| 1.2 | Create extension manifest file | Declare commands, scripts, min spec-kit version |
| 1.3 | Move command templates to `commands/` | All 9 `.md` files from `.specify/templates/commands/` |
| 1.4 | Migrate `.specify/templates/commands/.markdownlint.json` into extension package | Preserve command-level markdownlint behavior in `speckit-ext-agdt` as an extension-managed artifact |
| 1.5 | Move scripts to `scripts/` | All bash + powershell scripts |
| 1.6 | Namespace commands as `agdt:*` | Prefix to avoid collision with core (EC-003) |
| 1.7 | Add compatibility declaration (NFR-003) | Pin exact spec-kit core version in extension manifest; CI verifies compatibility on each release |
| 1.8 | Write comprehensive README | Installation, usage, command reference |
| 1.9 | Add CI for extension (lint, validate manifest) | GitHub Actions workflow |
| 1.10 | Tag initial release (v1.0.0) | Semantic versioning from day one |

### Phase 2: Create Preset Package (FR-004, FR-005)

**Deliverables**: `speckit-preset-agdt` repository with working preset

| # | Task | Details |
|---|------|---------|
| 2.1 | Create `ayaiayorg/speckit-preset-agdt` repository | Public repo with README, LICENSE |
| 2.2 | Create preset manifest file | Declare templates, min spec-kit version |
| 2.3 | Move template files | 5 templates + vscode-settings.json |
| 2.4 | Verify no new dependencies introduced (NFR-005) | Preset is pure templates |
| 2.5 | Write README with template override documentation | How to customize locally |
| 2.6 | Add CI for preset (markdownlint, validate) | GitHub Actions workflow |
| 2.7 | Tag initial release (v1.0.0) | Semantic versioning |

### Phase 3: Integration & Configuration (FR-007, US1, US2)

**Deliverables**: `.specify/config.yml` with version pins, working installation

| # | Task | Details |
|---|------|---------|
| 3.1 | Create `.specify/config.yml` | Pin extension and preset to v1.0.0 exact semver (NFR-004) |
| 3.2 | Install extension via `specify install speckit-ext-agdt` | Verify command availability |
| 3.3 | Reference preset in config | Verify template loading |
| 3.4 | Validate existing specs still work (NFR-002) | Run through all 20+ specs in `specs/` |
| 3.5 | Run `specify upgrade` to confirm no conflicts (SC-001) | Core upgrades cleanly |
| 3.6 | Update `.github/agents/` if command names changed | Adjust speckit.* agent references |

### Phase 4: Cleanup & Documentation (FR-010, FR-006, FR-011, FR-012)

**Deliverables**: Clean `.specify/` directory, updated documentation

| # | Task | Details |
|---|------|---------|
| 4.1 | Remove superseded scripts from `.specify/scripts/` | All 10 files |
| 4.2 | Remove all superseded files from `.specify/templates/` | 9 command `.md` files, `.markdownlint.json` from `commands/`; 5 template `.md` files, `vscode-settings.json` from root (16 files total) |
| 4.3 | Verify no orphaned-script warnings (AC-7.2) | Run `specify` commands |
| 4.4 | Update `SPEC_DRIVEN_DEVELOPMENT.md` | Reflect extension/preset architecture |
| 4.5 | Update `.specify/SDD_QUICK_REFERENCE.md` | New installation and usage commands |
| 4.6 | Update main `README.md` (FR-011) | Add links to extension and preset repos |
| 4.7 | Document upgrade strategy (FR-012) | Core, extension, preset upgrade procedures |
| 4.8 | Run markdownlint on all updated docs (NFR-006) | `markdownlint-cli2` validation |

### Phase 5: Community Extension Adoption (FR-008, FR-009)

**Deliverables**: At least one community extension adopted (SC-005)

| # | Task | Details |
|---|------|---------|
| 5.1 | Search spec-kit community catalog | Identify extensions with ≥80% overlap |
| 5.2 | Evaluate candidates against custom scripts | Compare functionality coverage |
| 5.3 | Replace qualifying scripts with community extensions | Document substitutions |
| 5.4 | Update `.specify/config.yml` with community extension pins | Exact semver |
| 5.5 | Remove replaced scripts from speckit-ext-agdt | Keep extension lean |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| spec-kit extension API instability | Medium | High | Pin exact versions; test in CI; maintain fallback branch with in-repo files |
| Command name conflicts after namespacing | Low | Medium | `agdt:` prefix (EC-003); test all commands after migration |
| Existing specs break during migration | Medium | High | Phase 3.4 validation gate; keep old files until verified |
| Community extensions are immature/abandoned | Medium | Low | Only adopt extensions with active maintenance (>1 release in 6 months) |
| Script path references in CI/docs become stale | High | Low | Global search-and-replace for `.specify/scripts/` paths |
| Multi-agent support regression | Low | High | Test `update-agent-context.sh` for all 15+ agent types |

## Dependencies

### External Dependencies

| Dependency | Purpose | Risk |
|-----------|---------|------|
| spec-kit core (pinned exact version via `.specify/config.yml`) | Base framework | Must support extension/preset APIs; version controlled by config pin (NFR-003/NFR-004) |
| spec-kit extension development guide | Extension manifest format | Must be stable/documented |
| GitHub repository creation (ayaiayorg org) | Hosting extension + preset | Requires org admin access |
| `specify install` command | Extension installation | Must support external packages |

### Internal Dependencies

| Dependency | Purpose | Blocker For |
|-----------|---------|-------------|
| Phase 0 complete inventory | Informs all subsequent phases | Phase 1, 2 |
| Phase 1 extension published | Required for integration | Phase 3 |
| Phase 2 preset published | Required for integration | Phase 3 |
| Phase 3 integration verified | Gate for cleanup | Phase 4 |
| `.github/agents/` compatibility | speckit.* agents must work | Phase 3.6 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
