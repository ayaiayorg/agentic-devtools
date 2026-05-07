# Spec: Restructure setup-dev-tools into modular .agdt-managed scripts

**Source Issue**: #1322 (<https://github.com/ayaiayorg/agentic-devtools/issues/1322>)

## Problem Statement

The current `setup-dev-tools.py` script handles both agentic-devtools installation AND repo-specific tooling in a single monolithic script.
This causes several problems:

1. **Fragile upgrades** — when agentic-devtools has a corrupted installation (missing RECORD file from editable/dev builds),
   `pip install --force-reinstall` fails because it cannot uninstall the previous version. Users must manually delete site-packages artifacts like
   `~gentic-devtools`, `~gentic_devtools`, `_editable_impl_agentic_devtools.pth`.
2. **No separation of concerns** — agentic-devtools' own install logic is mixed with repo-specific tooling setup.
3. **No resilient self-repair** — there is no handling for the common "invalid distribution / no RECORD file" scenario when switching between
   dev builds and PyPI releases.

The goal of this change is to restructure the monolithic script into a modular architecture with scripts in the `.agdt/` folder, providing
robust self-repair, clear separation of managed vs customer-owned scripts, and a configurable tooling layer.

## Proposed Architecture

The restructured system consists of five scripts with clear ownership boundaries:

| Script | Location | Owner | Purpose |
|--------|----------|-------|---------|
| `agentic-devtools-required-setup.py` | `.agdt/` | agentic-devtools (managed) | Robust self-install/repair with cleanup of corrupted distributions |
| `agentic-devtools-configured-setup.py` | `.agdt/` | agentic-devtools (generated) | Dynamically generated based on user tool selections via `agdt-setup` |
| `agentic-devtools-complete-setup.py` | `.agdt/` | agentic-devtools (managed) | Orchestrator calling required then configured setup |
| `setup-dev-tools.py` | repo root | agentic-devtools (managed) | Entry point calling `.agdt/agentic-devtools-complete-setup.py` then `setup-repo-specific-dev-tools.py` |
| `setup-repo-specific-dev-tools.py` | repo root | customer-owned | Auto-created by `agdt-setup` if missing, never overwritten |

## Clarifications

### Session 2026-05-04

- Q: Should `agentic-devtools-required-setup.py` target a pinned version or always install the latest from PyPI?
  → A: Target the latest PyPI version. Version pinning introduces staleness and is not appropriate for a self-repair tool that should always
  bring the installation to the current stable release.
- Q: What is the full list of optional tools that `agentic-devtools-configured-setup.py` can install?
  → A: The exact list is determined dynamically by `agdt-setup` based on the user's answers. Known candidates include cspell, ruff,
  markdownlint-cli2, and other project-quality tools. The configured script only installs what the user selected.
- Q: Should the `--foreground` flag be exposed on `setup-dev-tools.py` or only on the inner scripts?
  → A: Expose `--foreground` on `setup-dev-tools.py` (the repo-root entry point) and propagate it to inner scripts. The flag exists for
  explicitness and forward-compatibility with a future `--background` mode; since the default is already synchronous (see below), passing
  `--foreground` today is a no-op that documents intent (e.g., in CI scripts or debugging sessions).
- Q: The `.agdt/` directory is currently listed in `.gitignore` (used for runtime state, workflows, and background tasks). Should the new managed setup scripts in `.agdt/` be committed to the
  repository, or generated on-the-fly each time `agdt-setup` runs?
  → A: The scripts must be committed to the repository so that `setup-dev-tools.py` can invoke them immediately after clone without requiring `agdt-setup` to have been run first. To achieve this,
  the `.gitignore` must use the following pattern (because git does not check negation rules for files inside a fully-ignored directory):

  ```gitignore
  # Keep .agdt/ contents ignored for runtime state, but track managed setup scripts
  .agdt/*
  !.agdt/agentic-devtools-*.py
  ```

  The key insight is that the existing `.agdt/` rule (trailing slash) ignores the **directory** itself, which prevents git from ever
  examining its contents — making negation rules ineffective. Changing to `.agdt/*` (with a glob) tells git to ignore the directory's
  **contents** while still traversing the directory, allowing subsequent `!` negations to re-include specific files.
- Q: What specific marker comment identifies the new modular orchestrator entry point in `setup-dev-tools.py`, so that FR-013's legacy detection can distinguish between old monolithic scripts and the
  new orchestrator?
  → A: Use the marker comment `# AGDT-MANAGED-ORCHESTRATOR` on a line by itself near the top of the generated `setup-dev-tools.py`. FR-013's detection logic checks whether this exact string appears
  anywhere in the file; if absent, the file is treated as a legacy monolithic script.
- Q: In FR-009, "propagating any errors" is ambiguous — does the orchestrator use a fail-fast strategy (abort on the first script failure) or a collect-all strategy (run all scripts and report all
  failures)?
  → A: Fail-fast. If `agentic-devtools-required-setup.py` fails, the orchestrator must stop immediately and not run `agentic-devtools-configured-setup.py`, because configured tools depend on a working
  agentic-devtools installation. The same fail-fast rule applies in the root `setup-dev-tools.py`: if the complete-setup script fails, the repo-specific script is not run.
- Q: What is the default execution mode when `--foreground` is not passed? The spec defines `--foreground` for synchronous execution but does not specify the default.
  → A: The default execution mode is foreground (synchronous). The `--foreground` flag exists for explicitness and forward-compatibility — a future `--background` mode may run scripts as background
  tasks via the existing task infrastructure. For now, omitting the flag behaves identically to passing `--foreground`.
- Q: How does this restructuring relate to the existing `agdt-setup` command (`setup_cmd` in `agentic_devtools/cli/setup/commands.py`)? Does this extend the existing command or replace it?
  → A: This extends the existing `agdt-setup` command. The current `agdt-setup` already handles dependency checking, Copilot CLI installation, GH CLI installation, and cert prefetching. The
  restructuring adds a new phase at the end of `agdt-setup` that generates the `.agdt/` setup scripts and updates the repo-root `setup-dev-tools.py`. The existing `agdt-setup` functionality
  (dependency checks, CLI installs, cert setup) is preserved unchanged.

## User Stories & Testing

### User Story 1 — Corrupted install self-repair (Priority: P1)

A developer has a corrupted agentic-devtools installation (missing RECORD file, leftover `~gentic-devtools` artifacts from a failed
editable install). Running `setup-dev-tools.py` should automatically detect the corruption, clean up invalid artifacts from site-packages,
and reinstall cleanly from PyPI without manual intervention.

**Covers**: FR-001, FR-002, FR-003, FR-004, FR-012

**Why this priority**: This is the primary pain point that blocks developers when switching between dev builds and PyPI releases.

**How to test**: Simulate a corrupted state by creating dummy `~gentic-devtools` and `~gentic_devtools` directories and a
`_editable_impl_agentic_devtools.pth` file in the site-packages directory. Run `agentic-devtools-required-setup.py` and verify the artifacts
are removed and `agentic-devtools` is installed successfully from PyPI.

### User Story 2 — Modular script generation via agdt-setup (Priority: P1)

A developer runs `agdt-setup` in a new repository. The command prompts for tool selections (e.g., cspell, ruff) and generates
`agentic-devtools-configured-setup.py` with only the selected tools. Re-running `agdt-setup` regenerates the configured script with
updated selections.

**Covers**: FR-005, FR-006, FR-014, FR-015

**Why this priority**: This is the core user-facing workflow for configuring per-repo tooling.

**How to test**: Run `agdt-setup` with mocked user inputs selecting specific tools. Verify the generated
`agentic-devtools-configured-setup.py` contains install commands only for the selected tools. Re-run with different selections and verify
the file is overwritten with the new configuration.

### User Story 3 — Orchestrated complete setup (Priority: P2)

A developer clones a repository that already has `.agdt/` scripts configured. Running `setup-dev-tools.py` from the repo root executes the
full chain: required setup (self-repair/install), configured setup (selected tools), then repo-specific setup (customer script).

**Covers**: FR-009, FR-010, FR-011

**Why this priority**: This is the standard onboarding flow for existing repositories.

**How to test**: Set up a repository with all scripts present. Run `setup-dev-tools.py` and verify each script executes in order. Mock
subprocess calls to confirm the orchestration sequence. Verify that if `agentic-devtools-required-setup.py` fails, the subsequent scripts
are not executed (fail-fast behavior per the clarified FR-009).

### User Story 4 — Backward compatibility with existing repos (Priority: P2)

A repository that predates this restructuring (has only a monolithic `setup-dev-tools.py`) continues to work. Running `agdt-setup` in such a
repository creates the `.agdt/` structure and replaces the old `setup-dev-tools.py` with the new modular entry point, while preserving any
repo-specific logic by migrating it into `setup-repo-specific-dev-tools.py`.

**Covers**: FR-007, FR-008, FR-013

**Why this priority**: Existing repos must not break when updating agentic-devtools.

**How to test**: Start with a legacy monolithic `setup-dev-tools.py` (one that does not contain the `# AGDT-MANAGED-ORCHESTRATOR` marker).
Run `agdt-setup` and verify the old content is preserved in `setup-repo-specific-dev-tools.py`, the new modular scripts are created in
`.agdt/`, and the root `setup-dev-tools.py` is replaced with the orchestrator entry point containing the marker comment. Verify that if
`setup-repo-specific-dev-tools.py` already exists, the legacy content is appended below a separator comment rather than overwriting.

### User Story 5 — Git hooks setup via required-setup (Priority: P3)

Running `agentic-devtools-required-setup.py` configures git hooks (e.g., `core.hooksPath`) as part of the required environment setup,
ensuring developers have consistent pre-commit/pre-push behavior without additional manual steps.

**Covers**: FR-004

**Why this priority**: Git hooks are a convenience feature, not blocking for core functionality.

**How to test**: Run `agentic-devtools-required-setup.py` in a git repository and verify `git config core.hooksPath` is set to `.githooks`.
Verify the `.githooks` directory is created if it did not exist. Verify that a pre-existing `core.hooksPath` value other than `.githooks` is
overwritten with a logged warning.

## Requirements

### Functional Requirements

- **FR-001**: `agentic-devtools-required-setup.py` must detect corrupted installations by scanning site-packages for artifacts matching
  `~gentic-devtools`, `~gentic_devtools`, invalid `.dist-info` directories without a RECORD file, and
  `_editable_impl_agentic_devtools.pth`.
- **FR-002**: `agentic-devtools-required-setup.py` must remove all detected corrupted artifacts before attempting installation.
- **FR-003**: `agentic-devtools-required-setup.py` must install the latest PyPI version of `agentic-devtools` using
  `sys.executable -m pip install --upgrade agentic-devtools` (without `--force-reinstall`) after cleanup. Using `sys.executable -m pip`
  ensures the install targets the same Python environment that is executing the setup script, avoiding mismatches on systems with multiple
  Python installations.
- **FR-004**: `agentic-devtools-required-setup.py` must set up git hooks by configuring `core.hooksPath` to `.githooks` relative to
  the repository root. If the `.githooks` directory does not exist, the script must create it. If `core.hooksPath` is already set to
  `.githooks`, the step is a no-op. If it is set to a different value, the script must overwrite it with `.githooks` and log a warning
  indicating the previous value.
- **FR-005**: `agdt-setup` must generate `agentic-devtools-configured-setup.py` based on the user's interactive tool selections.
- **FR-006**: `agdt-setup` must always overwrite `agentic-devtools-required-setup.py`, `agentic-devtools-configured-setup.py`,
  `agentic-devtools-complete-setup.py`, and the root `setup-dev-tools.py` on each run. The generated `setup-dev-tools.py` must contain the
  `# AGDT-MANAGED-ORCHESTRATOR` marker comment near the top of the file.
- **FR-007**: `agdt-setup` must only create `setup-repo-specific-dev-tools.py` if it does not already exist. It must never overwrite a
  customer-managed script.
- **FR-008**: When `setup-repo-specific-dev-tools.py` is auto-created, it must contain initial content that logs "No repo-specific dev tools
  configured" with an explanatory comment guiding the user on how to customize it.
- **FR-009**: `agentic-devtools-complete-setup.py` must call `agentic-devtools-required-setup.py` first, then
  `agentic-devtools-configured-setup.py`, using a fail-fast strategy: if the required-setup script exits with a non-zero code, the
  orchestrator must abort immediately without running the configured-setup script.
- **FR-010**: The root `setup-dev-tools.py` must call `.agdt/agentic-devtools-complete-setup.py` first, then
  `setup-repo-specific-dev-tools.py`, using the same fail-fast strategy: if complete-setup fails, the repo-specific script is not executed.
- **FR-011**: All scripts must support a `--foreground` flag that runs operations synchronously (for CI and debugging use cases). The root
  `setup-dev-tools.py` must propagate this flag to inner scripts. The default execution mode (when `--foreground` is omitted) is also
  synchronous; the flag exists for explicitness and forward-compatibility with a future `--background` mode.
- **FR-012**: Each script must be executable standalone (e.g., `python .agdt/agentic-devtools-required-setup.py`) without requiring the
  orchestrator.
- **FR-013**: When `agdt-setup` detects an existing legacy monolithic `setup-dev-tools.py` (one that does not contain the
  `# AGDT-MANAGED-ORCHESTRATOR` marker comment), it must migrate the legacy content into `setup-repo-specific-dev-tools.py` using the
  following rules:
  (a) the entire content of the old `setup-dev-tools.py` is moved verbatim into `setup-repo-specific-dev-tools.py`;
  (b) if `setup-repo-specific-dev-tools.py` already exists, the legacy content must be appended below a clearly-delimited separator
  comment (e.g., `# --- Migrated from legacy setup-dev-tools.py ---`) rather than overwriting existing customer content;
  (c) after migration, the root `setup-dev-tools.py` is replaced with the new modular orchestrator entry point.
- **FR-014**: The `.gitignore` file must be updated to allow managed setup scripts in `.agdt/` to be tracked by git. The existing
  `.agdt/` ignore rule must be replaced with `.agdt/*` (glob form), followed by a negation rule for managed scripts:
  `!.agdt/agentic-devtools-*.py`. This ensures runtime state files remain ignored while the managed setup scripts are committed to the
  repository.
- **FR-015**: The script generation phase must be added as a new phase at the end of the existing `agdt-setup` command
  (`agentic_devtools/cli/setup/commands.py`), preserving all existing functionality (dependency checks, CLI installs, cert prefetching) unchanged.

### Non-Functional Requirements

- **NFR-001**: All managed scripts must be cross-platform compatible (Windows, macOS, Linux) using only standard library modules for path
  handling and subprocess execution.
- **NFR-002**: The self-repair logic in `agentic-devtools-required-setup.py` must complete within 30 seconds under normal conditions
  (excluding network latency for pip install).
- **NFR-003**: Script generation by `agdt-setup` must be idempotent — running `agdt-setup` twice with the same inputs must produce
  byte-for-byte identical output files.
- **NFR-004**: Error messages from script failures must clearly indicate which script in the chain failed (by name and path) and provide
  actionable guidance for manual recovery (e.g., "Run `python .agdt/agentic-devtools-required-setup.py` directly to diagnose the issue").
- **NFR-005**: The restructured system must maintain backward compatibility: repositories with only the old monolithic `setup-dev-tools.py`
  must continue to function until explicitly migrated via `agdt-setup`.

## Success Criteria

1. **Self-repair works end-to-end**: A developer with a corrupted agentic-devtools installation can run `setup-dev-tools.py` and have the
   corruption automatically detected, cleaned, and the package reinstalled from PyPI without any manual intervention.
2. **Modular generation works**: Running `agdt-setup` in a repository produces all five scripts with correct content matching the user's
   tool selections. Re-running with different selections regenerates all managed scripts (per FR-006), but only the configured-setup
   script's content changes; the other scripts are overwritten with byte-for-byte identical output.
3. **Orchestration chain is correct**: `setup-dev-tools.py` executes the scripts in the correct order (required → configured → repo-specific)
   with fail-fast error propagation.
4. **Legacy migration preserves content**: Running `agdt-setup` in a repository with an old monolithic `setup-dev-tools.py` migrates the
   legacy content into `setup-repo-specific-dev-tools.py` without data loss, and the new orchestrator entry point replaces the old file.
5. **Scripts are standalone**: Each `.agdt/` script can be invoked directly with `python <script>` and functions correctly without depending
   on the orchestrator.
6. **Cross-platform**: All scripts pass on Windows, macOS, and Linux without platform-specific code paths for basic path/subprocess
   operations.
7. **Gitignore selective un-ignore**: Managed setup scripts in `.agdt/` are tracked by git while runtime state remains ignored.
8. **Existing agdt-setup preserved**: The dependency checking, CLI installation, and cert prefetching phases of `agdt-setup` continue to
   work unchanged.

## Edge Cases

- **Read-only site-packages**: If the Python environment's site-packages directory is read-only (e.g., system Python on Linux),
  `agentic-devtools-required-setup.py` must detect the permission error during cleanup, report it clearly (e.g.,
  "Permission denied: cannot clean site-packages at `/usr/lib/python3.x/site-packages`. Use a virtual environment instead."), and exit with
  a non-zero code without proceeding to the install step.
- **Non-git contexts**: If `agentic-devtools-required-setup.py` is run outside a git repository (e.g., in an extracted archive or a bare
  directory), the git hooks setup step must be skipped with an informational message (e.g., "Not a git repository — skipping git hooks
  setup") rather than failing.
- **Syntax errors in customer scripts**: If `setup-repo-specific-dev-tools.py` contains syntax errors, the orchestrator must catch the
  failure, report which script failed (including the full path), and still return a non-zero exit code without masking the error.
- **Direct script execution without orchestrator**: Each `.agdt/` script must function correctly when invoked directly (e.g.,
  `python .agdt/agentic-devtools-required-setup.py`) without depending on environment variables or state set by the orchestrator.
- **Multiple orphaned artifacts**: If site-packages contains multiple generations of corrupted artifacts (e.g., both `~gentic-devtools` and
  an old `.dist-info` without RECORD), all must be cleaned in a single pass rather than requiring multiple runs.
- **Missing `.agdt/` directory after clone**: If a repository has the managed scripts committed but the `.agdt/` directory was not created
  (e.g., sparse checkout or incomplete clone), `setup-dev-tools.py` must detect the missing directory and report a clear error
  (e.g., "`.agdt/` directory not found — restore tracked files with `git checkout -- .agdt/` or re-clone the repository") rather than
  failing with a confusing FileNotFoundError. The error message must not assume `agentic-devtools` is installed; if the CLI is available,
  running `agdt-setup` may be mentioned as an optional fallback but must not be the primary recovery instruction.
- **Concurrent `agdt-setup` runs**: If two developers run `agdt-setup` simultaneously in different terminals of the same worktree, the
  generated files must not be corrupted. File writes must be atomic (e.g., the implementation must ensure partial writes are never visible
  to concurrent readers). The expected outcome is a consistent final state reflecting whichever run completed last, with no truncated or
  interleaved file content.

---

*Generated by Copilot SDK (claude-opus-4.6)*
