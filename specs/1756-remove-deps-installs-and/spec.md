# Feature Specification: Remove --no-deps Installs and Make github-copilot-sdk a Direct Dependency

**Feature Branch**: `speckit/1756/phase-1-specify`  
**Created**: 2026-06-03  
**Status**: Draft  
**Input**: GitHub Issue #1756 — Remove --no-deps installs and make github-copilot-sdk a direct dependency  
**Source Issue**: #1756 (<https://github.com/ayaiayorg/agentic-devtools/issues/1756>)

## Problem Statement

The `agentic-devtools` Python package currently treats `github-copilot-sdk` as an optional dependency declared under `[project.optional-dependencies]` in `pyproject.toml`. Despite being optional in
the package metadata, the SDK is actually required at runtime by multiple CI workflows and the `copilot_generate.py` script. This mismatch between declared and actual dependency status has created a
fragile installation pattern where CI workflows must perform a separate `pip install "github-copilot-sdk>=0.1.0,<1.0.0"` followed by a `--force-reinstall --no-deps` invocation before installing
`agentic-devtools` itself. This workaround exists in at least two critical workflow files (`ai-pr-loop.yml` and `speckit-phase-progression.yml`), creating duplicated maintenance burden and an opaque
installation sequence that obscures the true dependency graph.

The practical consequence of this architectural debt was demonstrated in PR #1753, where a breaking change in the SDK surfaced as a runtime error rather than an install-time dependency resolution
failure. When a dependency is declared as optional but actually required, pip's dependency resolver cannot catch incompatibilities during installation — they only manifest when the code attempts to
import the missing or incompatible module at runtime. This defeats one of the core purposes of a dependency management system: catching conflicts early and deterministically. Developers and CI runners
waste time debugging import errors that should never occur if the dependency graph is honest.

Additionally, the `copilot_generate.py` script (located at `.github/scripts/speckit-trigger/copilot_generate.py`) contains 20+ lines of defensive diagnostic code that runs `pip show github-copilot-sdk`
as a subprocess to investigate import failures. This runtime detection logic adds complexity, increases script execution time, and produces diagnostic messages that must be maintained in test assertions.
By making the SDK a direct dependency, standard Python import error reporting becomes sufficient here without custom diagnostic machinery.

## Clarifications

### Session 2026-06-03

- Q: Should the `copilot_generate.py` diagnostic removal also remove the check for a conflicting `copilot` package (lines 39–51 that detect a shadowing `copilot` package), or only the
  `pip show github-copilot-sdk` diagnostic? → A: Remove the entire defensive diagnostic block (lines 30–56 of the try/except handler), including the
  conflicting-package check. Once the SDK is a direct dependency, separate `pip show` diagnostics are no longer required here; the except block should re-raise the ImportError (or allow it to
  propagate naturally) rather than performing subprocess diagnostics.
- Q: The spec references `pip install agentic-devtools` for the `ai-pr-loop.yml` workflow — should this remain as a PyPI install from the published package, or should it use `pip install .` (source
  install) like `speckit-phase-progression.yml`? → A: Retain the existing install mechanism for each workflow: `ai-pr-loop.yml` uses `pip install agentic-devtools` (from PyPI) and
  `speckit-phase-progression.yml` uses `pip install .` (from source). The spec already correctly distinguishes these in FR-003 and FR-004.
- Q: After removing the `copilot-sdk` optional-dependencies group, should any deprecation notice or migration guidance be added to CHANGELOG.md or a migration document? → A: Yes, add a CHANGELOG.md
  entry under the next release noting the removal of the `copilot-sdk` optional extra and that `github-copilot-sdk` is now installed automatically as a direct dependency. No separate migration
  document is needed since the change is backward-compatible for users who were already installing the extra.
- Q: The `speckit-phase-progression.yml` workflow (line 487) also uses `pip install . --no-deps` for `agentic-devtools` itself — should this `--no-deps` on the package install also be removed? → A:
  Yes, absolutely. The `--no-deps` flag on `pip install .` defeats the entire purpose of declaring direct dependencies. It must be replaced with a plain `pip install .` so that pip resolves all
  declared dependencies (including the newly-direct `github-copilot-sdk`).
- Q: Should the `copilot-setup-steps.yml` workflow (used for Copilot cloud agent setup) also be checked and updated if it contains similar SDK install workarounds? → A: Yes, all workflow files under
  `.github/workflows/` that contain separate `github-copilot-sdk` install steps or `--no-deps`/`--force-reinstall` workarounds must be updated. The scope includes `ai-pr-loop.yml`,
  `speckit-phase-progression.yml`, and any other workflow exhibiting the same pattern. The spec's FR-003 and FR-004 explicitly name the two known workflows; any additional workflows discovered during
  implementation should be fixed under the same principle.

## User Scenarios & Testing

### User Story 1 - Simplified CI Workflow Installation (Priority: P1)

As a CI workflow maintainer, I want `agentic-devtools` to declare all its runtime dependencies directly so that a single `pip install agentic-devtools` (or `pip install .`) command installs everything
needed, eliminating fragile multi-step install sequences that are prone to ordering bugs and version drift.

Today, when a new contributor or a renovate bot updates the SDK version constraint in one workflow file but not the other, the system enters an inconsistent state where one workflow succeeds and
another fails. By centralizing the dependency declaration in `pyproject.toml`, version constraints are defined once and pip resolves them uniformly across all consumers.

**Why this priority**: This is the core value proposition of the change. Every other improvement (simplified scripts, removed diagnostics) flows from getting the dependency declaration right. Without
this, the workarounds remain necessary.

**Independent Test**: Can be fully tested by running `pip install .` in a fresh virtual environment and verifying that `from copilot import CopilotClient` succeeds without any prior SDK installation
step.

**Acceptance Scenarios**:

1. **Given** a fresh supported Python (3.10+) virtual environment with no packages installed, **When** a user runs `pip install agentic-devtools`,
   **Then** `github-copilot-sdk` is automatically installed as a direct dependency of `agentic-devtools` and `from copilot import CopilotClient, SubprocessConfig` succeeds.
2. **Given** the `pyproject.toml` file, **When** a developer inspects the `[project.dependencies]` list, **Then** `github-copilot-sdk>=0.1.0,<1.0.0` appears as a direct dependency and no `copilot-sdk`
   optional-dependencies group exists.
3. **Given** a CI environment running the `ai-pr-loop.yml` workflow, **When** the install step executes, **Then** only `pip install --upgrade pip` and `pip install agentic-devtools` install
   commands are required (an optional one-line SDK import smoke check may be present), and no `--force-reinstall`, `--no-deps`, or separate SDK install lines exist.

---

### User Story 2 - Early Detection of SDK Incompatibilities (Priority: P1)

As a developer upgrading or modifying SDK-dependent code, I want dependency conflicts to be caught at install time by pip's resolver so that I receive clear, actionable error messages before any code
executes, rather than encountering cryptic runtime import failures in production CI runs.

The current pattern allows pip to successfully install `agentic-devtools` even when the separately-installed SDK version is incompatible with the package's actual requirements. By declaring the SDK as
a direct dependency with a version constraint (`>=0.1.0,<1.0.0`), pip will refuse to install if the constraint cannot be satisfied, surfacing the conflict immediately.

**Why this priority**: Equally critical to Story 1 because it addresses the reliability guarantee. The issue specifically references PR #1753 where this exact failure mode caused production impact.

**Independent Test**: Can be tested by attempting to install `agentic-devtools` alongside a hypothetical `github-copilot-sdk==2.0.0` and verifying that pip raises a `ResolutionImpossible` error rather
than silently succeeding.

**Acceptance Scenarios**:

1. **Given** a `pyproject.toml` with `github-copilot-sdk>=0.1.0,<1.0.0` in direct dependencies, **When** a user attempts `pip install agentic-devtools` in an environment where only
   `github-copilot-sdk==2.0.0` is available, **Then** pip reports a dependency resolution conflict at install time.
2. **Given** the updated dependency declaration, **When** Dependabot or Renovate proposes an SDK version bump, **Then** the version constraint in `pyproject.toml` is the single source of truth that
   must be updated.

---

### User Story 3 - Simplified Runtime Import Handling (Priority: P2)

As a maintainer of `copilot_generate.py`, I want the script's import error handling to rely on standard Python mechanisms rather than custom `pip show` subprocess diagnostics, reducing code complexity
and test maintenance burden.

The current `copilot_generate.py` (at `.github/scripts/speckit-trigger/copilot_generate.py`) contains approximately 20 lines of defensive code that shells out to `pip show github-copilot-sdk` and
`pip show copilot` to diagnose installation problems. This code exists solely because the SDK might not be installed despite `agentic-devtools` being present. Once the SDK is a direct dependency,
these diagnostics become redundant because installation and import failures should be surfaced through standard pip/Python error reporting.

The entire defensive diagnostic block (including the conflicting-package shadow detection for the `copilot` package name) must be removed. The except block should allow the `ImportError` to propagate
naturally with standard Python traceback output.

**Why this priority**: This is a clean-up task that reduces maintenance burden but doesn't change user-facing behavior. The diagnostic removal makes the codebase simpler and eliminates test assertions
that track internal implementation details rather than observable behavior.

**Independent Test**: Can be tested by verifying that `copilot_generate.py` no longer invokes `pip show` as a subprocess, and that import failures produce a standard Python traceback rather than
custom diagnostic messages.

**Acceptance Scenarios**:

1. **Given** the updated `copilot_generate.py`, **When** a developer searches for `pip show github-copilot-sdk` in the file, **Then** no such subprocess invocation exists.
2. **Given** the updated test file `tests/workflows/test_copilot_generate.py`, **When** tests are executed,
   **Then** no assertions reference the strings `pip show github-copilot-sdk` or `Ensure 'github-copilot-sdk' is installed`.
3. **Given** a broken environment where the copilot module genuinely cannot be imported, **When** `copilot_generate.py` runs, **Then** a standard Python `ImportError` or `ModuleNotFoundError` is
   raised with a clear module path.

---

### User Story 4 - Consistent Local Development Experience (Priority: P3)

As a local developer setting up the project for the first time, I want `pip install -e .` or `pip install -e ".[dev]"` to provide a fully functional environment without needing to know about separate
SDK installation steps that are only documented in CI workflow files.

Currently, a developer who follows the README's installation instructions may end up without the Copilot SDK installed because it's only an optional dependency. They discover the gap when they attempt
to run speckit workflows or the AI PR loop locally. By making the SDK a direct dependency, the standard development setup path becomes complete.

**Why this priority**: Affects developer onboarding experience but is not a blocking operational issue since most development doesn't require the Copilot SDK locally.

**Independent Test**: Can be tested by following the README installation steps in a fresh environment and confirming that all SDK-dependent scripts can be invoked without additional installation
steps.

**Acceptance Scenarios**:

1. **Given** a fresh clone of the repository, **When** a developer runs `pip install -e ".[dev]"`, **Then** `python -c "from copilot import CopilotClient"` succeeds without any additional commands.

---

### Edge Cases

- What happens when a user has an older version of `github-copilot-sdk` (e.g., 0.0.9) already installed? Pip's resolver should upgrade it to satisfy the `>=0.1.0` constraint during `agentic-devtools`
  installation.
- What happens if `github-copilot-sdk` is temporarily unavailable on PyPI? The `agentic-devtools` installation will fail entirely, which is the correct behavior — it's better to fail clearly at
  install time than to succeed installation and fail at runtime.
- What happens to environments that previously installed `agentic-devtools` with the `[copilot-sdk]` extra? The extra group is removed, so `pip install agentic-devtools[copilot-sdk]` will emit a
  warning about an unknown extra (pip does not hard-fail on unknown extras but prints a warning). Migration guidance is to run `pip install agentic-devtools` (without extras), since the SDK is now
  installed unconditionally. A CHANGELOG.md entry will document this change.
- What happens to `pip install . --no-deps` in `speckit-phase-progression.yml`? This flag is removed because it prevented pip from resolving any dependencies including the newly-direct SDK. It is
  replaced with a plain `pip install .`.

## Requirements

### Functional Requirements

- **FR-001**: The `pyproject.toml` file MUST declare `github-copilot-sdk>=0.1.0,<1.0.0` in the `[project.dependencies]` list, ensuring pip installs it automatically when `agentic-devtools` is
  installed.

- **FR-002**: The `[project.optional-dependencies]` section MUST NOT contain a `copilot-sdk` group, since the SDK is no longer optional. Other optional dependency groups (such as `langchain` and
  `dev`) must remain unchanged.

- **FR-003**: The `.github/workflows/ai-pr-loop.yml` install step MUST use `pip install --upgrade pip` and `pip install agentic-devtools` as the installation commands, with no separate SDK
  installation, `--force-reinstall`, or `--no-deps` flags present. An optional SDK import smoke check command MAY be retained.

- **FR-004**: The `.github/workflows/speckit-phase-progression.yml` install step MUST use `pip install --upgrade pip` and `pip install .` as the installation commands, with no separate SDK
  installation, `--force-reinstall`, or `--no-deps` flags present (including the `--no-deps` flag on the `pip install .` command itself, which must also be removed). An optional SDK import smoke check
  command MAY be retained.

- **FR-005**: The `copilot_generate.py` script (at `.github/scripts/speckit-trigger/copilot_generate.py`) MUST NOT invoke `pip show github-copilot-sdk` or `pip show copilot` as subprocess commands for
  diagnostic purposes. The entire defensive diagnostic block — including the conflicting-package shadow detection — must be removed. Import failure handling should rely
  on standard Python exception propagation (allowing `ImportError`/`ModuleNotFoundError` to propagate naturally).

- **FR-006**: All existing tests in the repository MUST continue to pass after the changes. Tests that assert on SDK diagnostic messages (such as strings containing `"pip show github-copilot-sdk"` or
  `"Ensure 'github-copilot-sdk' is installed"`)
  MUST be updated or removed to reflect the simplified error handling.

- **FR-007**: The upper bound version constraint (`<1.0.0`) MUST be maintained on the SDK dependency to protect against breaking changes from a future v1 release, consistent with the project's stated
  intent to address the v1 upgrade in a separate issue.

- **FR-008**: A CHANGELOG.md entry MUST be added under the next release section documenting: (a) the removal of the `copilot-sdk` optional extra, (b) that `github-copilot-sdk` is now a direct
  dependency installed automatically, and (c) that users previously using `pip install agentic-devtools[copilot-sdk]` should switch to `pip install agentic-devtools`.

### Non-Functional Requirements

- **NFR-001**: CI workflow installation time MUST NOT increase by more than 10% compared to the current multi-step installation approach. Since pip already resolves dependencies transitively, the
  simplified single-command install should be equivalent or faster due to fewer subprocess invocations.

- **NFR-002**: The change MUST NOT introduce any new runtime dependencies beyond `github-copilot-sdk` and its own transitive dependencies. The SDK's dependency tree must be compatible with the
  existing `agentic-devtools` dependency set without version conflicts.

- **NFR-003**: Error messages when the SDK cannot be imported MUST remain actionable. While custom diagnostics are removed, the standard Python import error traceback must clearly identify which
  module failed to import and from which package it should come.

### Key Entities

- **`pyproject.toml` dependency declaration**: The single source of truth for the SDK version constraint, consumed by pip during installation of `agentic-devtools`.
- **CI workflow install steps**: The YAML configurations in `.github/workflows/` that install the package in CI runners. These must be simplified to a single pip install command (specifically
  `ai-pr-loop.yml` and `speckit-phase-progression.yml`, plus any other workflows found to have the same pattern).
- **SDK diagnostic block in `copilot_generate.py`**: The defensive import error handling code (approximately lines 30–56 in `.github/scripts/speckit-trigger/copilot_generate.py`) that performs
  subprocess calls to diagnose SDK installation issues, including the conflicting-package shadow detection.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Each CI workflow install step MUST remove the separate SDK install and `--no-deps`/`--force-reinstall` workaround while retaining `pip install --upgrade pip` plus package installation
  (`pip install agentic-devtools` or `pip install .`) as the required install commands; an optional one-line SDK import smoke check is allowed.

- **SC-002**: No CI workflow MUST contain a separate `pip install` step targeting `github-copilot-sdk` directly, nor MUST any such step use `--no-deps` or `--force-reinstall`;
  other workflow steps that legitimately use these flags for unrelated packages are unaffected.

- **SC-003**: The `copilot_generate.py` script MUST have zero subprocess calls to `pip show`, reducing the diagnostic code block from approximately 20 lines to 0 lines.

- **SC-004**: 100% of existing tests MUST pass after the changes, with test modifications limited to removing or updating assertions that reference removed diagnostic behavior.

- **SC-005**: A fresh `pip install .` in a clean virtual environment MUST successfully resolve and install `github-copilot-sdk` within the declared version constraint;
  this is verifiable by `pip show github-copilot-sdk` showing a version satisfying `>=0.1.0,<1.0.0`.

- **SC-006**: Both the `ai-pr-loop` and `speckit-phase-progression` CI workflows MUST complete their install steps successfully on the first PR that implements this change, confirming end-to-end
  compatibility with the simplified installation approach.

---
*Generated by Copilot SDK (claude-opus-4.6)*
