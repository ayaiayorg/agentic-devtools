# Tasks: Monorepo-based spec-kit extension/preset strategy (#1444)

## Phase Mapping: Plan → Tasks

| Plan Phase | Tasks Phase | Tasks |
|------------|-------------|-------|
| Phase 1: Create Extension Package | Phase 1 | T001–T005 |
| Phase 2: Create Preset Package | Phase 2 | T006–T008 |
| Phase 3: Update Configuration | Phase 3 | T009 |
| Phase 4: Cleanup | Phase 4 | T010–T011 |

## Phase 1: Create Extension Package

- [x] T001 Create `extension.yml` manifest at `.specify/extensions/agdt-workflows/extension.yml`
  declaring commands, scripts, and package metadata
- [x] T002 Move 9 command template `.md` files from `.specify/templates/commands/` to
  `.specify/extensions/agdt-workflows/commands/`
- [x] T003 Move `.markdownlint.json` from `.specify/templates/commands/` to
  `.specify/extensions/agdt-workflows/commands/` and update `extends` path
- [x] T004 Move 5 bash scripts from `.specify/scripts/bash/` to
  `.specify/extensions/agdt-workflows/scripts/bash/`
- [x] T005 Move 5 powershell scripts from `.specify/scripts/powershell/` to
  `.specify/extensions/agdt-workflows/scripts/powershell/`

## Phase 2: Create Preset Package

- [x] T006 Create `preset.yml` manifest at `.specify/presets/agdt-templates/preset.yml`
  declaring templates and package metadata
- [x] T007 Move 5 template `.md` files from `.specify/templates/` to
  `.specify/presets/agdt-templates/templates/`
- [x] T008 Move `vscode-settings.json` from `.specify/templates/` to
  `.specify/presets/agdt-templates/templates/`

## Phase 3: Update Configuration

- [x] T009 Rewrite `.specify/config.yml` to reference extension and preset via relative
  paths (replacing remote version pins)

## Phase 4: Cleanup

- [x] T010 Remove now-empty `.specify/scripts/` directory
- [x] T011 Remove now-empty `.specify/templates/` directory

## Dependencies

```text
T001 → T002, T003, T004, T005 (manifest before content)
T006 → T007, T008 (manifest before content)
T002–T005, T007–T008 → T009 (all moves before config update)
T009 → T010, T011 (config updated before cleanup)
```

## FR Coverage Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T004, T005 |
| FR-002 | T002, T003 |
| FR-003 | T009 |
| FR-004 | T007, T008 |
| FR-005 | T001, T006 |
| FR-006 | T001, T006 (manifest structure supports publishing) |
