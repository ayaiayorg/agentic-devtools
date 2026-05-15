# Spec-Kit Migration Inventory

**Source Issue**: [#1408](https://github.com/ayaiayorg/agentic-devtools/issues/1408)
**Date**: 2026-05-13
**Purpose**: Complete inventory of all customized spec-kit assets in this
repository, with categorization and migration target for each file.

> **Scope**: This inventory covers *pre-existing* customized files that are
> migration targets (scripts, templates, and local-only assets). New
> configuration files introduced as part of the migration (e.g.,
> `.specify/config.yml`) are not included here — they are documented
> alongside their respective tasks in the migration plan.

## Summary

| Category | File Count | Total Lines |
|----------|-----------|-------------|
| Extension scripts (bash) | 5 | 1,621 |
| Extension scripts (powershell) | 5 | 1,174 |
| Extension commands | 9 | 1,645 |
| Extension config | 1 | 6 |
| Preset templates | 5 | 700 |
| Preset assets | 1 | 14 |
| Local-only (stays in-repo) | 3 | 471 |
| **Total customized files** | **29** | **5,631** |

> **Counting method**: Line counts use PowerShell `(Get-Content <file>).Count`,
> which returns the number of content lines (array elements) in the file.
>
> This may differ from other tools:
>
> - **`wc -l`** counts newline characters, so it reports one fewer for
>   files that lack a trailing newline (e.g., 165 vs 166).
> - **Editors / GitHub file view** display an extra empty line for files
>   that *have* a trailing newline, so they show one more (e.g., 167 vs
>   166). This is a display artifact — the file contains 166 lines of
>   content.
>
> All counts in this inventory were re-verified against the current tree
> using `(Get-Content <file>).Count` on 2026-05-14.

## Inventory

### Scripts — `.specify/scripts/bash/`

| File | Lines | Purpose | Category | Target Package |
|------|-------|---------|----------|----------------|
| `check-prerequisites.sh` | 166 | Validates feature branch, spec directory, and required docs before SDD commands run | Extension script | `speckit-ext-agdt` |
| `common.sh` | 167 | Shared utility functions (JSON output, error handling, path resolution) used by all other scripts | Extension script | `speckit-ext-agdt` |
| `create-new-feature.sh` | 316 | Scaffolds a new feature spec directory with branch detection, issue linking, and directory creation | Extension script | `speckit-ext-agdt` |
| `setup-plan.sh` | 61 | Locates spec file and sets up plan.md output path for the plan agent | Extension script | `speckit-ext-agdt` |
| `update-agent-context.sh` | 911 | Generates and updates `.github/agents/` context files with plan.md, spec.md, and codebase summaries | Extension script | `speckit-ext-agdt` |

### Scripts — `.specify/scripts/powershell/`

| File | Lines | Purpose | Category | Target Package |
|------|-------|---------|----------|----------------|
| `check-prerequisites.ps1` | 148 | PowerShell equivalent of `check-prerequisites.sh` | Extension script | `speckit-ext-agdt` |
| `common.ps1` | 137 | PowerShell equivalent of `common.sh` | Extension script | `speckit-ext-agdt` |
| `create-new-feature.ps1` | 314 | PowerShell equivalent of `create-new-feature.sh` | Extension script | `speckit-ext-agdt` |
| `setup-plan.ps1` | 61 | PowerShell equivalent of `setup-plan.sh` | Extension script | `speckit-ext-agdt` |
| `update-agent-context.ps1` | 514 | PowerShell equivalent of `update-agent-context.sh` | Extension script | `speckit-ext-agdt` |

### Command Templates — `.specify/templates/commands/`

| File | Lines | Purpose | Category | Target Package |
|------|-------|---------|----------|----------------|
| `analyze.md` | 264 | Slash command template for `/speckit.analyze` — deep code analysis with multi-pass review | Extension command | `speckit-ext-agdt` |
| `checklist.md` | 298 | Slash command template for `/speckit.checklist` — generates quality checklists from spec | Extension command | `speckit-ext-agdt` |
| `clarify.md` | 185 | Slash command template for `/speckit.clarify` — asks targeted clarification questions | Extension command | `speckit-ext-agdt` |
| `constitution.md` | 83 | Slash command template for `/speckit.constitution` — manages project constitution | Extension command | `speckit-ext-agdt` |
| `implement.md` | 139 | Slash command template for `/speckit.implement` — executes task-based implementation | Extension command | `speckit-ext-agdt` |
| `plan.md` | 96 | Slash command template for `/speckit.plan` — generates implementation plan from spec | Extension command | `speckit-ext-agdt` |
| `specify.md` | 336 | Slash command template for `/speckit.specify` — creates feature specification from issue | Extension command | `speckit-ext-agdt` |
| `tasks.md` | 202 | Slash command template for `/speckit.tasks` — generates task breakdown from plan | Extension command | `speckit-ext-agdt` |
| `taskstoissues.md` | 42 | Slash command template for `/speckit.taskstoissues` — converts tasks to GitHub issues | Extension command | `speckit-ext-agdt` |
| `.markdownlint.json` | 6 | Markdownlint config for command templates (extends root config, disables MD041/MD013) | Extension config | `speckit-ext-agdt` |

### Document Templates — `.specify/templates/`

| File | Lines | Purpose | Category | Target Package |
|------|-------|---------|----------|----------------|
| `spec-template.md` | 166 | Template for `spec.md` — defines required sections (summary, problem, goals, user stories, requirements) | Preset template | `speckit-preset-agdt` |
| `plan-template.md` | 113 | Template for `plan.md` — defines implementation plan structure (phases, tasks, risks, dependencies) | Preset template | `speckit-preset-agdt` |
| `tasks-template.md` | 353 | Template for `tasks.md` — defines task breakdown structure (phase mapping, dependencies, FR coverage) | Preset template | `speckit-preset-agdt` |
| `checklist-template.md` | 40 | Template for quality checklists — defines checklist format (categories, CHK IDs, meta section) | Preset template | `speckit-preset-agdt` |
| `agent-file-template.md` | 28 | Template for `.github/agents/*.agent.md` files — defines multi-agent support structure | Preset template | `speckit-preset-agdt` |
| `vscode-settings.json` | 14 | VS Code settings for spec-kit features (custom labels, slash command config) | Preset asset | `speckit-preset-agdt` |

### Local-Only Files (Stay In-Repo)

| File | Lines | Purpose | Reason |
|------|-------|---------|--------|
| `.specify/memory/constitution.md` | 204 | Project-specific principles and constraints | Per-project, not reusable |
| `.specify/memory/markdown-rules.md` | 8 | Markdown formatting rules for this project | Per-project, not reusable |
| `.specify/SDD_QUICK_REFERENCE.md` | 259 | Quick reference for SDD commands | Per-project documentation |

## AGDT-Specific vs Generic Logic

### Tightly Coupled to agentic-devtools

These files contain logic specific to agentic-devtools workflows:

- `update-agent-context.sh` — References `.github/agents/` structure, copilot-instructions, and AGDT-specific agent types
- `create-new-feature.sh` — Uses AGDT branch naming conventions and spec directory structure
- All command templates — Reference AGDT-specific scripts, agent context, and project conventions

### Potentially Generic (Community Extension Candidates)

These files implement patterns that could be generic spec-kit functionality:

- `check-prerequisites.sh` / `common.sh` — Feature branch detection, spec directory validation (common SDD patterns)
- `setup-plan.sh` — Plan file path resolution (generic SDD pattern)
- Template files — Could be contributed as community templates with AGDT-specific sections factored out

## Stale Path References

> **Scope**: This table covers `.github/` files (agents and other docs) —
> the primary consumers of script/template paths that will break after
> migration. Additional references exist in `specs/README.md`,
> `specs/*/plan.md`, `specs/*/tasks.md`, and `SPEC_DRIVEN_DEVELOPMENT.md`;
> these will be addressed as part of T042 (global search-and-replace).

The following `.github/` files reference `.specify/scripts/` or
`.specify/templates/` paths that will need updating after migration:

| File | Reference Type |
|------|---------------|
| `.github/agents/speckit.analyze.agent.md` | Script path: `check-prerequisites.sh` |
| `.github/agents/speckit.implement.agent.md` | Script path: `check-prerequisites.sh` |
| `.github/agents/speckit.clarify.agent.md` | Script path: `check-prerequisites.sh` |
| `.github/agents/speckit.checklist.agent.md` | Script path: `check-prerequisites.sh`, template: `checklist-template.md` |
| `.github/agents/speckit.plan.agent.md` | Script paths: `setup-plan.sh`, `update-agent-context.sh` |
| `.github/agents/speckit.specify.agent.md` | Script paths: `create-new-feature.sh` |
| `.github/agents/speckit.tasks.agent.md` | Script path: `check-prerequisites.sh`, template: `tasks-template.md` |
| `.github/agents/speckit.taskstoissues.agent.md` | Script path: `check-prerequisites.sh` |
| `.github/agents/speckit.constitution.agent.md` | Template paths: `plan-template.md`, `spec-template.md`, `tasks-template.md`, `commands/*.md` |
| `.github/MARKDOWN_LINTING.md` | Template directory reference |

## Migration Notes

### Community Extension Evaluation (T027-T030)

Catalog review was completed against the Spec-Kit community catalog
(`docs/community/extensions.md` in the spec-kit repository, which backs
[`speckit-community.github.io/extensions`](https://speckit-community.github.io/extensions/)).
The upstream spec-kit community documentation also points to this same catalog
URL: [github/spec-kit/docs/community/extensions.md](https://github.com/github/spec-kit/blob/main/docs/community/extensions.md).

Repository structure check for #1444 status:

- `.specify/extensions/` not present
- `.specify/scripts/bash/` and `.specify/scripts/powershell/` still present

This indicates #1444 has **not** landed in this branch, so the T027-T030
comparison and replacement decision is scoped to the current in-repo script
layout.

#### Candidate overlap analysis (≥80% threshold)

| Community extension | Closest inventoried custom scope | Estimated overlap | Decision |
|---------------------|----------------------------------|-------------------|----------|
| `spec-kit-branch-convention` | `.specify/scripts/bash/create-new-feature.sh` + `.ps1` equivalent (branch naming/pattern checks) | ~35% | Not adopted |
| `spec-kit-brownfield` | `.specify/scripts/bash/check-prerequisites.sh`, `create-new-feature.sh` (bootstrap/setup concepts) | ~30% | Not adopted |
| `speckit-utils` | `.specify/scripts/bash/check-prerequisites.sh` and `setup-plan.sh` (workflow health/utility helpers) | ~25% | Not adopted |

**Result:** No community extension meets the **≥80% functionality overlap**
threshold required by FR-008/FR-009 and User Story 4 acceptance criteria (see
`specs/1408-migrate-native-spec-kit/spec.md` Functional Requirements table:
FR-008/FR-009 and User Story 4 acceptance criteria).

T028/T029/T030 close-out for this branch:

- No substitutions were made.
- `.specify/config.yml` received no community extension pins because no
  qualifying replacement was found.
- No scripts were removed from `.specify/scripts/bash/` or
  `.specify/scripts/powershell/`.

### Command Namespacing

After migration, extension commands will be namespaced with the `agdt:` prefix to avoid
collision with spec-kit core commands (per EC-003):

| Current Command | Post-Migration Command |
|-----------------|----------------------|
| `/speckit.specify` | `/speckit.agdt:specify` |
| `/speckit.plan` | `/speckit.agdt:plan` |
| `/speckit.tasks` | `/speckit.agdt:tasks` |
| `/speckit.implement` | `/speckit.agdt:implement` |
| `/speckit.analyze` | `/speckit.agdt:analyze` |
| `/speckit.clarify` | `/speckit.agdt:clarify` |
| `/speckit.checklist` | `/speckit.agdt:checklist` |
| `/speckit.constitution` | `/speckit.agdt:constitution` |
| `/speckit.taskstoissues` | `/speckit.agdt:taskstoissues` |

### Dependency Chain

```text
T003 (this inventory) → T004 (categorization, done above)
  → T005/T006 (manifests in external repos)
  → T010-T017 (move files + publish)
  → T018-T023 (integrate + validate)
  → T036-T039 (remove superseded files)
```

---
*Generated for issue #1408 — Migrate to native spec-kit core*
