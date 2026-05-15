# Implementation Plan: Monorepo-based spec-kit extension/preset strategy

**Source Issue**: #1444
**Supersedes**: #1408
**Date**: 2026-05-15

## Summary

Move all AGDT-specific spec-kit customizations into local extension and preset packages
within the repository, referenced by relative paths in `.specify/config.yml`. This is a
structural reorganization — no content changes to scripts or templates.

## Technical Context

**Tooling**: spec-kit CLI, bash/powershell scripts, markdown templates
**Package Format**: Local spec-kit extension and preset packages (directory-based)
**Hosting**: In-repo under `.specify/extensions/` and `.specify/presets/`
**CI**: Existing PR checks pipeline
**State**: No runtime code changes — this is a file move and config update

## Design Overview

```text
.specify/
├── config.yml                          ← references local packages
├── extensions/
│   └── agdt-workflows/                 ← extension package
│       ├── extension.yml               ← extension manifest
│       ├── commands/                   ← command templates (from templates/commands/)
│       │   ├── analyze.md
│       │   ├── checklist.md
│       │   ├── clarify.md
│       │   ├── constitution.md
│       │   ├── implement.md
│       │   ├── plan.md
│       │   ├── specify.md
│       │   ├── tasks.md
│       │   ├── taskstoissues.md
│       │   └── .markdownlint.json
│       └── scripts/                    ← scripts (from scripts/)
│           ├── bash/
│           │   ├── check-prerequisites.sh
│           │   ├── common.sh
│           │   ├── create-new-feature.sh
│           │   ├── setup-plan.sh
│           │   └── update-agent-context.sh
│           └── powershell/
│               ├── check-prerequisites.ps1
│               ├── common.ps1
│               ├── create-new-feature.ps1
│               ├── setup-plan.ps1
│               └── update-agent-context.ps1
├── presets/
│   └── agdt-templates/                 ← preset package
│       ├── preset.yml                  ← preset manifest
│       └── templates/                  ← document templates (from templates/)
│           ├── agent-file-template.md
│           ├── checklist-template.md
│           ├── plan-template.md
│           ├── spec-template.md
│           ├── tasks-template.md
│           └── vscode-settings.json
├── memory/                             ← untouched
│   ├── constitution.md
│   └── markdown-rules.md
└── SDD_QUICK_REFERENCE.md             ← untouched
```

## Implementation Phases

### Phase 1: Create Extension Package

Move command templates and scripts into the extension package structure.

| # | Task | Details |
|---|------|---------|
| 1.1 | Create `extension.yml` manifest | Declare commands, scripts, metadata |
| 1.2 | Move command templates | 9 `.md` files + `.markdownlint.json` from `templates/commands/` |
| 1.3 | Move bash scripts | 5 files from `scripts/bash/` |
| 1.4 | Move powershell scripts | 5 files from `scripts/powershell/` |
| 1.5 | Update `.markdownlint.json` extends path | Adjust relative path for new location |

### Phase 2: Create Preset Package

Move document templates into the preset package structure.

| # | Task | Details |
|---|------|---------|
| 2.1 | Create `preset.yml` manifest | Declare templates, metadata |
| 2.2 | Move template files | 5 `*-template.md` files + `vscode-settings.json` |

### Phase 3: Update Configuration

Update `.specify/config.yml` to use relative paths.

| # | Task | Details |
|---|------|---------|
| 3.1 | Rewrite `config.yml` | Replace remote pins with relative path references |

### Phase 4: Cleanup

Remove now-empty original directories.

| # | Task | Details |
|---|------|---------|
| 4.1 | Remove `.specify/scripts/` | Empty after move |
| 4.2 | Remove `.specify/templates/` | Empty after move |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Script path references break | Medium | Low | Update internal cross-references |
| markdownlint extends path invalid | High | Low | Update relative path in moved config |
| CI scripts reference old paths | Low | Medium | Search and verify no hard-coded paths |

## Dependencies

No external dependencies. All work is within this repository.
