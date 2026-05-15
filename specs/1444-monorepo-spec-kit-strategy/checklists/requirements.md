# Requirements Checklist: Monorepo-based spec-kit extension/preset strategy

**Purpose**: Validate implementation completeness
**Created**: 2026-05-15
**Feature**: [spec.md](../spec.md)
**Source Issue**: #1444

## Structural Verification

- [x] CHK001 Extension package directory exists at `.specify/extensions/agdt-workflows/`
- [x] CHK002 Preset package directory exists at `.specify/presets/agdt-templates/`
- [x] CHK003 Extension manifest (`extension.yml`) declares all commands and scripts
- [x] CHK004 Preset manifest (`preset.yml`) declares all templates
- [x] CHK005 `.specify/config.yml` uses relative paths to both packages

## Content Integrity

- [x] CHK006 All 9 command templates moved to extension package without content changes
- [x] CHK007 All 5 bash scripts moved to extension package without content changes
- [x] CHK008 All 5 powershell scripts moved to extension package without content changes
- [x] CHK009 All 5 document templates moved to preset package without content changes
- [x] CHK010 `vscode-settings.json` moved to preset package without content changes
- [x] CHK011 `.markdownlint.json` moved and `extends` path updated for new location

## Cleanup Verification

- [x] CHK012 `.specify/scripts/` directory removed (empty after moves)
- [x] CHK013 `.specify/templates/` directory removed (empty after moves)
- [x] CHK014 `.specify/memory/` remains untouched
- [x] CHK015 `.specify/SDD_QUICK_REFERENCE.md` remains untouched
