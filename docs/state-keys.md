# State Key Naming Convention

This document defines the naming convention for keys stored in AGDT's
runtime state (`agdt-state.json`).

## Top-Level Categories

All **new** state keys MUST be placed under one of three top-level
namespaces.  Each namespace represents a category of external system,
named in a technology-agnostic way so the same key structure works
regardless of the specific tool in use.

| Category | Abstraction | Current Implementation |
|---|---|---|
| `versionControl` | Version control system | Git |
| `sourceCodeHostingPlatform` | Code hosting / PR platform | Azure DevOps (GitHub, Bitbucket planned) |
| `issueManagement` | Issue / work-item tracking | Jira (GitHub Issues planned) |

Keys that are AGDT-internal (not tied to an external system) live at
the top level without a category prefix (e.g., `agdt_run_id`,
`dry_run`).

## Naming Rules

- **Dot-separated nesting**: `category.subcategory.leafKey`
- **camelCase** for leaf keys and subcategories:
  `versionControl.currentBranch`, not `version_control.current_branch`
- **Singular nouns** for subcategories representing a single entity:
  `sourceCodeHostingPlatform.pullRequest.sourceBranch`
- Keep nesting depth ≤ 4 levels where possible.

## Registered Keys

### AGDT Internal (no category prefix)

| Key | Type | Description | Introduced |
|---|---|---|---|
| `agdt_run_id` | `str` | Short UUID identifying the current workflow run (for commit amend logic) | [#841](https://github.com/ayaiayorg/agentic-devtools/issues/841) |
| `dry_run` | `bool` | When `true`, commands log actions without side effects | pre-existing |

### `versionControl`

| Key | Type | Description | Introduced |
|---|---|---|---|
| `versionControl.currentBranch` | `str` | The git branch checked out when the workflow was initiated | [#841](https://github.com/ayaiayorg/agentic-devtools/issues/841) |
| `versionControl.commitMessageType` | `str` | Explicit conventional commit type prefix (e.g., `feat`, `fix`, `chore`). Overrides Jira type mapping. | [#1829](https://github.com/ayaiayorg/agentic-devtools/issues/1829) |
| `versionControl.commitMessageTitle` | `str` | Commit message summary/title line for template rendering. | [#1829](https://github.com/ayaiayorg/agentic-devtools/issues/1829) |
| `versionControl.commitMessageBodyFile` | `str` | Path to file containing commit body text. Relative paths resolve against git root. | [#1829](https://github.com/ayaiayorg/agentic-devtools/issues/1829) |

### `sourceCodeHostingPlatform`

| Key | Type | Description | Introduced |
|---|---|---|---|
| `sourceCodeHostingPlatform.pullRequest.sourceBranch` | `str` | PR source branch name | planned (not yet implemented) |
| `sourceCodeHostingPlatform.pullRequest.targetBranch` | `str` | PR target branch name | planned (not yet implemented) |

### `issueManagement`

| Key | Type | Description | Introduced |
|---|---|---|---|
| `issueManagement.issueLink` | `str` | Explicit issue link URL. Overrides auto-derived GitHub issue link. | [#1829](https://github.com/ayaiayorg/agentic-devtools/issues/1829) |
| `issueManagement.issueKey` | `str` | Planned provider-agnostic issue key alias for `issue_key` (documented target; not yet consumed by runtime code). | [#1829](https://github.com/ayaiayorg/agentic-devtools/issues/1829) |
| `issueManagement.issueType` | `str` | Issue type for commit type mapping (e.g., `Bug`, `Story`, `Task`). | [#1829](https://github.com/ayaiayorg/agentic-devtools/issues/1829) |

Existing `jira.*` keys will be migrated to `issueManagement.*` in a future refactoring.

## Legacy Keys (pre-convention)

The following keys predate this convention and remain at their current
paths for backward compatibility.  They will be migrated in a future
refactoring effort.

| Current Key | Future Key | Notes |
|---|---|---|
| `pull_request_id` | `sourceCodeHostingPlatform.pullRequest.id` | |
| `jira.issue_key` | `issueManagement.issueKey` | |
| `jira.comment` | `issueManagement.comment` | |
| `jira.summary` | `issueManagement.summary` | |
| `jira.description` | `issueManagement.description` | |
| `jira.project_key` | `issueManagement.projectKey` | |
| `jira.issue_type` | `issueManagement.issueType` | |
| `jira.user_request` | `issueManagement.userRequest` | |

> **Note:** Do NOT rename legacy keys as part of other issues.
> A dedicated migration issue will handle the rename + update of all
> consumers in a single coordinated change.
