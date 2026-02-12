---

description: "Task list for PyPI Wheel Release"
---

# Tasks: PyPI Wheel Release

**Input**: Design documents from `/specs/001-pypi-wheel-release/`
**Prerequisites**: plan.md (required), spec.md (required for user stories),
research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required (TDD laut Verfassung; Test-Gate vor Veröffentlichung ist
P2).

**Organization**: Tasks sind nach User Story gruppiert, damit jede Story
unabhängig implementiert und getestet werden kann.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Projektinitialisierung und Abhängigkeiten für den Release-Flow

- [x] T001 Aktualisiere Abhängigkeiten für Build/Upload in pyproject.toml (add

  `build`, `twine` in project dependencies)
  `build`, `twine` in project dependencies)

- [x] T002 [P] Lege Release-CLI-Struktur an in

  agentic_devtools/cli/release/**init**.py und
  agentic_devtools/cli/release/**init**.py und
  agentic_devtools/cli/release/commands.py

- [x] T003 [P] Ergänze README.md um den neuen Release-Command und die

  State-Keys (Dokumentation der Nutzung)
  State-Keys (Dokumentation der Nutzung)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Gemeinsame Basis für alle User Stories

- [x] T004 Ergänze State-Getter/Setter für Release-Parameter in

  agentic_devtools/state.py (z. B. `pypi.package_name`, `pypi.version`,
  agentic_devtools/state.py (z. B. `pypi.package_name`, `pypi.version`,
  `pypi.repository`, `pypi.dry_run`)

- [x] T005 [P] Implementiere PyPI-JSON-Version-Check Helper in

  agentic_devtools/cli/release/helpers.py
  agentic_devtools/cli/release/helpers.py

- [x] T006 [P] Implementiere Build/Validate/Upload Helper (build, twine check,

  twine upload) in agentic_devtools/cli/release/helpers.py
  twine upload) in agentic_devtools/cli/release/helpers.py

- [x] T007 Integriere Background-Task Wrapper für Release in

  agentic_devtools/cli/release/commands.py (run_in_background)
  agentic_devtools/cli/release/commands.py (run_in_background)

- [x] T008 Verdrahte neuen CLI-Entry-Point in agentic_devtools/dispatcher.py

  und pyproject.toml (z. B. `agdt-release-pypi`)
  und pyproject.toml (z. B. `agdt-release-pypi`)

**Checkpoint**: Basis steht; User Story Implementierungen können beginnen

---

## Phase 3: User Story 1 - Rad für PyPI veröffentlichen (Priority: P1) 🎯 MVP

**Goal**: Release-Lauf erzeugt Wheel und veröffentlicht auf pypi.org

**Independent Test**: Release-Run mit gültiger Version führt zu Wheel in `dist/`
und Upload (bei Dry-Run nur Simulation).

### Tests für User Story 1 (TDD)

- [x] T009 [P] [US1] Unit-Tests für Version-Check in

  tests/test_release_helpers.py
  tests/test_release_helpers.py

- [x] T010 [P] [US1] Unit-Tests für Build/Validate/Upload Helper in

  tests/test_release_helpers.py
  tests/test_release_helpers.py

- [x] T011 [P] [US1] Integrationstest für Release-Command-Flow in

  tests/test_release_integration.py
  tests/test_release_integration.py

### Implementation für User Story 1

- [x] T012 [US1] Implementiere Release-Flow (Tests → Build → Validate → Upload)

  in agentic_devtools/cli/release/commands.py
  in agentic_devtools/cli/release/commands.py

- [x] T013 [US1] Ergänze Release-Run Statusmodell und

  Zusammenfassungserstellung in agentic_devtools/cli/release/commands.py
  Zusammenfassungserstellung in agentic_devtools/cli/release/commands.py

- [x] T014 [US1] Ergänze Release-CLI-Output für Erfolg/Fehler inkl.

  Paketname/Version in agentic_devtools/cli/release/commands.py
  Paketname/Version in agentic_devtools/cli/release/commands.py

**Checkpoint**: US1 ist unabhängig testbar und liefert MVP-Funktionalität

---

## Phase 4: User Story 2 - Test-Gate vor Veröffentlichung (Priority: P2)

**Goal**: Tests blockieren Veröffentlichung bei Fehlern

**Independent Test**: Ein absichtlich fehlschlagender Testlauf verhindert Upload
und markiert Release als fehlgeschlagen.

### Tests für User Story 2 (TDD)

- [x] T015 [P] [US2] Unit-Test für Test-Gate-Entscheidung in

  tests/test_release_commands.py
  tests/test_release_commands.py

- [x] T016 [P] [US2] Integrationstest: fehlschlagende Tests blockieren Upload

  in tests/test_release_integration.py
  in tests/test_release_integration.py

### Implementation für User Story 2

- [x] T017 [US2] Implementiere Test-Gate-Logik (Run

  `agdt-test`/`agdt-test-file` im Background-Flow) in
  `agdt-test`/`agdt-test-file` im Background-Flow) in
  agentic_devtools/cli/release/commands.py

- [x] T018 [US2] Ergänze Fehlerbehandlung und Statusübergänge für Test-Failures

  in agentic_devtools/cli/release/commands.py
  in agentic_devtools/cli/release/commands.py

**Checkpoint**: US2 verhindert Releases bei Testfehlschlag

---

## Phase 5: User Story 3 - Transparente Release-Ergebnisse (Priority: P3)

**Goal**: Klare Zusammenfassung über Test- und Release-Status

**Independent Test**: Release-Run erzeugt Zusammenfassung mit Paketname,
Version, Teststatus, Zeitpunkt und Ergebnis.

### Tests für User Story 3 (TDD)

- [x] T019 [P] [US3] Unit-Test für Release-Zusammenfassung in

  tests/test_release_commands.py
  tests/test_release_commands.py

- [x] T020 [P] [US3] Integrationstest für Summary-Ausgabe in

  tests/test_release_integration.py
  tests/test_release_integration.py

### Implementation für User Story 3

- [x] T021 [US3] Implementiere Summary-Format (inkl. Zeitstempel, Status) in

  agentic_devtools/cli/release/commands.py
  agentic_devtools/cli/release/commands.py

- [x] T022 [US3] Ergänze konsistente CLI-Ausgabe und Logs in

  agentic_devtools/cli/release/commands.py
  agentic_devtools/cli/release/commands.py

**Checkpoint**: US3 liefert transparente, nachvollziehbare Release-Ergebnisse

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Qualität, Doku, Stabilität

- [x] T023 [P] Dokumentiere Quickstart-Validierung und Beispiele in

  specs/001-pypi-wheel-release/quickstart.md
  specs/001-pypi-wheel-release/quickstart.md

- [x] T024 [P] Ergänze Sicherheits- und Token-Hinweise in README.md
- [x] T025 Code-Aufräumen und Fehlerpfade konsolidieren in

  agentic_devtools/cli/release/commands.py
  agentic_devtools/cli/release/commands.py

- [x] T026 [P] Ergänze zusätzliche Unit-Tests für Edge-Cases (Version

  existiert, Netzwerkfehler) in tests/test_release_helpers.py
  existiert, Netzwerkfehler) in tests/test_release_helpers.py

- [x] T027 [P] Aktualisiere CHANGELOG.md mit Release-Notes für den PyPI-Workflow
- [x] T028 Bumpe Version in pyproject.toml gemäß Release (SemVer)
- [x] T029 Führe `agdt-test` aus und warte mit `agdt-task-wait` (Pre-Release

  Gate)
  Gate)

- [x] T030 Führe `agdt-test-file --source-file

  agentic_devtools/cli/release/commands.py` aus und warte mit `agdt-task-wait`
  agentic_devtools/cli/release/commands.py` aus und warte mit `agdt-task-wait`
  (Coverage-Gate)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Keine Abhängigkeiten
- **Foundational (Phase 2)**: Blocker für alle User Stories
- **User Stories (Phase 3–5)**: Abhängig von Phase 2
- **Polish (Phase 6)**: Nach Abschluss der gewünschten User Stories

### User Story Dependencies

- **US1 (P1)**: Abhängig von Foundational
- **US2 (P2)**: Abhängig von Foundational, kann parallel zu US1 starten
- **US3 (P3)**: Abhängig von Foundational, kann parallel zu US1/US2 starten

### Within Each User Story

- Tests schreiben und fehlschlagen lassen → Implementierung → Integration

---

## Parallel Execution Examples

### US1 Parallelisierung

- T009: Unit-Tests Version-Check in tests/test_release_helpers.py
- T010: Unit-Tests Build/Upload Helper in tests/test_release_helpers.py
- T011: Integrationstest Release-Flow in tests/test_release_integration.py

### Foundational Parallelisierung

- T005: Version-Check Helper in agentic_devtools/cli/release/helpers.py
- T006: Build/Upload Helper in agentic_devtools/cli/release/helpers.py

---

## Implementation Strategy

### MVP (User Story 1)

1. Phase 1 + Phase 2 abschließen
2. US1 Tests (T009–T011) schreiben
3. US1 Implementierung (T012–T014)
4. Validieren, dass Release-Flow funktioniert

### Incremental Delivery

1. US1 (MVP)
2. US2 (Test-Gate)
3. US3 (Summary/Transparenz)
4. Polish
