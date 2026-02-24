# Implementation Plan: PyPI Wheel Release

**Branch**: `001-pypi-wheel-release` | **Date**: 2026-02-03 | **Spec**: [specs/001-pypi-wheel-release/spec.md](specs/001-pypi-wheel-release/spec.md)
**Input**: Feature specification from `/specs/001-pypi-wheel-release/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See
`.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Release-Verantwortliche sollen einen Release-Lauf starten können, der vor dem
Upload einen vollständigen Testlauf ausführt, ein Wheel erzeugt und das Paket
auf pypi.org veröffentlicht. Technisch wird ein neuer CLI-Release-Command
eingeführt, der als Background-Task läuft, Tests via bestehender
Test-Infrastruktur ausführt, das Wheel mit PEP-517 (`python -m build`)
erstellt,
Metadaten validiert und den Upload via Twine vornimmt, inklusive
Versionsprüfung
über die PyPI-JSON-API.

## Technical Context

**Language/Version**: Python >= 3.8
**Primary Dependencies**: requests, Jinja2 (bestehend), neu: build, twine (für
Release-Flows)
**Storage**: N/A (Artefakte in `dist/`, temporäre Dateien im Repo)
**Testing**: pytest über `agdt-test`/`agdt-test-file`
**Target Platform**: Cross-Platform CLI (Windows, Linux, macOS)
**Project Type**: single (Python package)
**Performance Goals**: N/A (CLI-Workflow)
**Constraints**: Auto-Approval Pattern, Background-Tasks, TDD-First, keine
direkten `pytest`-Aufrufe
**Scale/Scope**: Ein Release-Lauf pro Ausführung, lokales CLI-Workflow-Tool

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Auto-Approval Friendly Design**: PASS — neue Commands folgen `agdt-set` +

  parameterloser Ausführung.
  parameterloser Ausführung.

- **Single Source of Truth**: PASS — Release-Parameter über `agdt-set`/State;

  Secrets via Umgebungsvariablen.
  Secrets via Umgebungsvariablen.

- **Background Task Architecture**: PASS — Release/Upload als Background-Task.
- **Test-Driven Development**: PASS — Tests vor Implementierung, Nutzung von

  `agdt-test`.
  `agdt-test`.

- **Python Package Best Practices**: PASS — neue CLI-Entry-Points,

  Typen/Docstrings, cross-platform.
  Typen/Docstrings, cross-platform.

## Project Structure

### Documentation (this feature)

```text
specs/001-pypi-wheel-release/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
agentic_devtools/
├── cli/
│   ├── release/
│   │   ├── __init__.py
│   │   ├── helpers.py
│   │   └── commands.py
│   └── runner.py
├── background_tasks.py
├── dispatcher.py
├── state.py

tests/
├── test_release_commands.py
├── test_release_helpers.py
└── test_release_integration.py

scripts/
└── temp/
```

**Structure Decision**: Single Python package; Release-CLI unter
`agentic_devtools/cli/release/`, Tests unter `tests/`.

## Constitution Check (Post-Design)

- **Auto-Approval Friendly Design**: PASS — Command-Design unverändert.
- **Single Source of Truth**: PASS — State/Umgebungsvariablen klar getrennt.
- **Background Task Architecture**: PASS — Release bleibt Background-Task.
- **Test-Driven Development**: PASS — Tests als erste Implementierungsphase

  eingeplant.
  eingeplant.

- **Python Package Best Practices**: PASS — Entry-Points, Typen, Docs

  eingeplant.
  eingeplant.

## Complexity Tracking

Keine Verstöße gegen die Verfassung festgestellt.
