# Tasks: Migrate to Native Spec-Kit Core (#1408)

## Phase Mapping: Plan → Tasks

The plan phases map to task phases as follows. Plan phases are
combined or expanded where granularity differs.

| Plan Phase | Tasks Phase(s) | Tasks |
|------------|----------------|-------|
| Phase 0: Inventory & Categorization (FR-001, FR-002) | Phase 1: Setup & Inventory | T001–T004 |
| Phase 1: Create Extension Package (FR-003, FR-005) | Phase 2 (T005, T007–T009), Phase 3 (T010–T012, T016) | T005, T007–T012, T016 |
| Phase 2: Create Preset Package (FR-004, FR-005) | Phase 2 (T006), Phase 3 (T013–T015, T017) | T006, T013–T015, T017 |
| Phase 3: Integration & Configuration (FR-007, US1, US2) | Phase 4: Install Extension and Preset | T018–T023 |
| Phase 4: Cleanup & Documentation (FR-010, FR-006, FR-011, FR-012) | Phase 5 (T024–T026), Phase 9 (T036–T039), Final (T040–T044) | T024–T026, T036–T044 |
| Phase 5: Community Extension Adoption (FR-008, FR-009) | Phase 6: Adopt Community Extensions | T027–T030 |
| — (user-story driven) | Phase 7: Pin Versions (US5), Phase 8: Community Adoption (US6) | T031–T035 |

## Phase 1: Setup & Inventory

- [ ] T001 Scaffold `speckit-ext-agdt` repository structure under `ayaiayorg` org with README.md, LICENSE, and directory layout (`commands/`, `scripts/bash/`, `scripts/powershell/`)
- [ ] T002 Scaffold `speckit-preset-agdt` repository structure under `ayaiayorg` org with README.md, LICENSE, and directory layout (`templates/`)
- [x] T003 [FR-001] Inventory all customized files in `.specify/scripts/` and `.specify/templates/` —
  produce and verify `docs/speckit-migration-inventory.md` with file paths, line counts, and purpose summaries against the repository file listing
- [x] T004 [FR-002] Categorize each inventoried file as extension command, preset template, or local-only —
  update `docs/speckit-migration-inventory.md` with category and target package columns; verify each file is assigned exactly one category

## Phase 2: Foundational — Extension & Preset Package Creation

- [ ] T005 Create extension manifest file in `speckit-ext-agdt` declaring all commands, scripts, and minimum spec-kit core version pin (NFR-003) — `speckit-ext-agdt/manifest.yml`
- [ ] T006 Create preset manifest file in `speckit-preset-agdt` declaring all templates and minimum spec-kit core version — `speckit-preset-agdt/manifest.yml`
- [ ] T007 Namespace all extension commands with `agdt:` prefix to avoid collision with core commands (EC-003) — update manifest and command file names in `speckit-ext-agdt/commands/`
- [ ] T008 [FR-003] Add CI workflow for extension package (lint, validate manifest) — `speckit-ext-agdt/.github/workflows/ci.yml`
- [ ] T009 [FR-004] Add CI workflow for preset package (markdownlint, validate manifest) — `speckit-preset-agdt/.github/workflows/ci.yml`

## Phase 3: US1 — Upgrade Spec-Kit Core Without Conflicts (P1)

- [ ] T010 [US1] [FR-003] Move 9 command template `.md` files from `.specify/templates/commands/` into `speckit-ext-agdt/commands/` with `agdt:` namespaced filenames
- [ ] T011 [P] [US1] [FR-003] Move `.specify/templates/commands/.markdownlint.json` into `speckit-ext-agdt/` as extension-managed config
- [ ] T012 [P] [US1] [FR-003] Move 10 script files (5 bash, 5 powershell) from `.specify/scripts/` into `speckit-ext-agdt/scripts/bash/` and `speckit-ext-agdt/scripts/powershell/`
- [ ] T013 [US1] [FR-004] Move 5 template `.md` files from `.specify/templates/` into `speckit-preset-agdt/templates/` (`spec-template.md`, `plan-template.md`, `tasks-template.md`,
  `checklist-template.md`, `agent-file-template.md`)
- [ ] T014 [P] [US1] [FR-004] Move `vscode-settings.json` from `.specify/templates/` into `speckit-preset-agdt/templates/`
- [ ] T015 [US1] [FR-005] Verify preset introduces no new dependencies beyond spec-kit core (NFR-005) — audit `speckit-preset-agdt/manifest.yml`
- [ ] T016 [US1] [FR-005] Tag and publish `speckit-ext-agdt` initial release v1.0.0 to public GitHub repository
- [ ] T017 [US1] [FR-005] Tag and publish `speckit-preset-agdt` initial release v1.0.0 to public GitHub repository

## Phase 4: US2 — Install Extension and Preset Packages (P1)

- [ ] T018 [US2] [FR-007] Create `.specify/config.yml` with exact semver version pins for both `speckit-ext-agdt@1.0.0` and `speckit-preset-agdt@1.0.0` (NFR-004)
- [ ] T019 [US2] [FR-003] Install extension via `specify install speckit-ext-agdt` and verify all `agdt:*` commands are available (AC-2.1)
- [ ] T020 [US2] [FR-004] Reference preset in `.specify/config.yml` and verify all custom templates load automatically (AC-2.2)
- [ ] T021 [US2] [FR-003] [FR-004] Validate all 20+ existing specs in `specs/` directory still parse and render correctly after migration (NFR-002, SC-002)
- [ ] T022 [US2] [FR-003] Run `specify upgrade` and confirm core files update without conflicts in customized files (AC-1.1, SC-001)
- [ ] T023 [US2] [FR-003] Update `.github/agents/` speckit.* agent references if command names changed due to `agdt:` namespacing

## Phase 5: US3 — Onboard New Contributors (P2)

- [x] T024 [US3] [FR-006] Add installation and setup instructions to `SPEC_DRIVEN_DEVELOPMENT.md` covering extension and preset installation steps (AC-3.1)
- [x] T025 [P] [US3] [FR-006] Add developer guidelines section explaining when to edit the preset vs a local override (AC-3.2)
- [x] T026 [P] [US3] [FR-012] Document upgrade strategy for core, extension, and preset in `SPEC_DRIVEN_DEVELOPMENT.md` —
  include version pin update procedure and changelog review process; verify documented steps cover version-pin update, changelog review, and rollback scenarios

## Phase 6: US4 — Adopt Community Extensions (P2)

- [ ] T027 [US4] [FR-008] Search spec-kit community catalog and validate candidate extensions against inventory for ≥80% functionality overlap (AC-4.1)
- [ ] T028 [US4] [FR-009] Replace qualifying custom scripts with community extensions where ≥80% overlap exists —
  document substitutions in `docs/speckit-migration-inventory.md` and verify replaced commands produce equivalent output (AC-4.1)
- [ ] T029 [US4] Add community extension version pins to `.specify/config.yml` with exact semver (AC-4.2)
- [ ] T030 [US4] Remove replaced scripts from `speckit-ext-agdt` and publish updated release

## Phase 7: US5 — Pin Extension/Preset Versions (P2)

- [ ] T031 [US5] [FR-007] Verify version pins in `.specify/config.yml` prevent automatic upgrades — confirm pinned version is used even when newer version exists (AC-5.1)
- [ ] T032 [US5] Document version pin update workflow including changelog review checklist (AC-5.2) — add to `SPEC_DRIVEN_DEVELOPMENT.md`

## Phase 8: US6 — Community Adoption of Extension (P3)

- [ ] T033 [US6] Write comprehensive README for `speckit-ext-agdt` with capabilities, installation, command reference, and usage examples (AC-6.1)
- [ ] T034 [P] [US6] Write comprehensive README for `speckit-preset-agdt` with template override documentation
- [ ] T035 [US6] Submit extension to spec-kit community catalog for discoverability (AC-6.1)

## Phase 9: US7 — Clean Up Deprecated In-Repo Assets (P3)

- [ ] T036 [US7] [FR-010] Remove all 10 superseded script files from `.specify/scripts/bash/` and `.specify/scripts/powershell/` (AC-7.1)
- [ ] T037 [US7] [FR-010] Remove all 16 superseded files from `.specify/templates/` — 9 command `.md` files, `.markdownlint.json`, 5 template `.md` files, `vscode-settings.json` (AC-7.1)
- [ ] T038 [US7] [FR-010] Verify `.specify/` directory contains only local per-project files (`memory/`, `config.yml`, `SDD_QUICK_REFERENCE.md`) (AC-7.1, SC-004)
- [ ] T039 [US7] [FR-010] Run all `specify` commands and confirm no orphaned-script warnings appear (AC-7.2)

## Final Phase: Polish & Cross-Cutting

- [x] T040 Update `.specify/SDD_QUICK_REFERENCE.md` with new installation and usage commands
- [x] T041 [FR-011] Update `SPEC_DRIVEN_DEVELOPMENT.md` with links to extension and preset repositories — add placeholder links (verification deferred until T016/T017 publish)
- [ ] T042 Global search-and-replace for stale `.specify/scripts/` path references in CI configs, docs, and agent files (deferred — paths are still valid until extension packages are published at T016/T017)
- [ ] T043 [FR-003] [FR-004] [FR-010] Run `bash scripts/run-pr-checks.sh` to validate all PR checks pass
- [ ] T044 [FR-006] Verify all updated documentation files pass markdownlint validation (NFR-006)
- [ ] T045 [FR-007] E2E smoke test — installation: fresh clone → `specify install` → verify extension and preset install correctly from version pins
- [ ] T046 [FR-003] [FR-004] E2E smoke test — commands: run all spec-kit workflow commands (spec, plan, tasks, checklist) → verify correct output post-migration

## Dependencies

```text
T003 → T004 (inventory before categorization)
T004 → T005, T006 (categorization before manifests)
T005 → T010, T011, T012 (manifest before moving files)
T006 → T013, T014 (manifest before moving files)
T010, T011, T012 → T016 (all extension files moved before publish)
T013, T014 → T017 (all preset files moved before publish)
T016, T017 → T018 (both published before config)
T018 → T019, T020 (config before install)
T019, T020 → T021, T022 (install before validation)
T022 → T036, T037 (upgrade verified before cleanup)
T027 → T028 (validate before replace)
T028 → T029, T030 (replace before pin/publish)
T036, T037 → T038, T039 (remove before verify)
T039 → T040, T041, T042 (cleanup verified before polish)
T045 → T046 (installation verified before command verification)
```

## FR Coverage Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T003 |
| FR-002 | T004 |
| FR-003 | T010, T011, T012, T019, T021, T022, T023, T043, T046 |
| FR-004 | T013, T014, T020, T021, T043, T046 |
| FR-005 | T015, T016, T017 |
| FR-006 | T024, T025, T044 |
| FR-007 | T018, T031, T045 |
| FR-008 | T027 |
| FR-009 | T028 |
| FR-010 | T036, T037, T038, T039, T043 |
| FR-011 | T041 |
| FR-012 | T026 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
