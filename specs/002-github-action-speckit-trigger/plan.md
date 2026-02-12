# Implementation Plan: GitHub Action SpecKit Trigger

**Branch**: `002-github-action-speckit-trigger` | **Date**: 2026-02-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from
`/specs/002-github-action-speckit-trigger/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See
`.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Repository maintainers want to automatically trigger the Specification-Driven
Development (SDD) process when a GitHub issue is assigned to a designated agent
(e.g., `speckit-agent`). The solution involves creating a GitHub Actions
workflow that listens for `issues.assigned` events, validates the assignee
against a configurable list, extracts issue content, invokes the SpecKit
`/speckit.specify` process, and provides feedback via issue comments and
optional PR creation.

## Technical Context

**Language/Version**: YAML (GitHub Actions), Bash scripts, Node.js 20 (for
actions/github-script)
**Primary Dependencies**: GitHub Actions (`actions/checkout@v4`,
`actions/github-script@v7`), gh CLI
**Storage**: N/A (specifications stored in `specs/` directory via git)
**Testing**: Manual testing via issue creation; automated via act (local GitHub
Actions runner)
**Target Platform**: GitHub.com, GitHub Enterprise Server
**Project Type**: single (GitHub Actions workflow + helper scripts)
**Performance Goals**: Acknowledge within 30 seconds, complete within 5 minutes
**Constraints**: Must work within GitHub Actions runtime limits, API rate limits
**Scale/Scope**: Single issue trigger at a time, idempotent execution

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Auto-Approval Friendly Design**: PASS — Workflow uses configurable inputs

  with sensible defaults; no interactive prompts.
  with sensible defaults; no interactive prompts.

- **Single Source of Truth**: PASS — Configuration via workflow inputs and

  repository variables; spec output in `specs/` directory.
  repository variables; spec output in `specs/` directory.

- **Background Task Architecture**: N/A — GitHub Actions handles async

  execution natively.
  execution natively.

- **Test-Driven Development**: PARTIAL — Manual testing via issue creation;

  recommend adding workflow testing via `act`.
  recommend adding workflow testing via `act`.

- **Code Quality & Maintainability**: PASS — YAML follows GitHub Actions best

  practices; scripts include error handling.
  practices; scripts include error handling.

- **User Experience Consistency**: PASS — Feedback comments follow consistent

  format; errors explain resolution steps.
  format; errors explain resolution steps.

- **Performance & Responsiveness**: PASS — NFR-001 specifies 30-second

  acknowledgment; NFR-002 specifies 5-minute completion.
  acknowledgment; NFR-002 specifies 5-minute completion.

- **Python Package Best Practices**: N/A — This feature is YAML/Bash-based, not

  Python.
  Python.

## Project Structure

### Documentation (this feature)

```text
specs/002-github-action-speckit-trigger/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── tasks.md             # Phase 2 output (/speckit.tasks command)
└── checklists/
    └── requirements.md  # Spec quality checklist
```text

### Source Code (repository root)

```text
.github/
├── workflows/
│   └── speckit-issue-trigger.yml    # Main workflow file (NEW)
└── scripts/
    └── speckit-trigger/             # Helper scripts (NEW)
        ├── validate-assignee.sh     # Check if assignee triggers SDD
        ├── sanitize-branch-name.sh  # Convert issue title to valid branch name
        ├── post-issue-comment.sh    # Post status comments to issue
        └── generate-spec-from-issue.sh  # Invoke SpecKit specify process
```text

**Structure Decision**: Single workflow file with modular helper scripts for
testability and reusability. Scripts follow existing patterns in
`.github/workflows/scripts/`.

## Architecture Decisions

### AD-001: Workflow Trigger Mechanism

**Decision**: Use `issues.assigned` event with conditional assignee check in the
workflow.

**Rationale**:

- GitHub Actions natively supports `issues.assigned` event type
- Checking assignee in workflow (vs. repository dispatch) avoids external

  webhook setup
  webhook setup

- Allows filtering before any compute resources are used

**Alternatives Considered**:

- Repository dispatch with external webhook: More complex setup, requires

  additional infrastructure
  additional infrastructure

- Issue comment trigger (e.g., `/speckit`): Requires parsing comments, less

  intuitive UX
  intuitive UX

### AD-002: AI Provider Integration

**Decision**: Use environment-based AI provider selection with Claude as
default.

**Rationale**:

- Supports multiple AI providers (Claude, Copilot, etc.) through configuration
- Aligns with existing SpecKit agent architecture in `.github/agents/`
- Secrets managed via GitHub repository secrets

**Implementation**:

- Workflow input `ai_provider` selects provider
- Provider-specific API keys stored as repository secrets (e.g.,

  `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`)
  `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`)

- Helper script invokes appropriate agent based on selection

### AD-003: Spec Generation Approach

**Decision**: Invoke existing SpecKit scripts and templates rather than
reimplementing spec generation.

**Rationale**:

- Reuses tested, proven specification workflow
- Ensures consistency with manual `/speckit.specify` invocations
- Reduces maintenance burden

**Implementation**:

- Call `.specify/scripts/bash/create-new-feature.sh` for directory setup
- Use spec template from `.specify/templates/spec-template.md`
- Invoke AI agent with issue content as input

### AD-004: Feedback Mechanism

**Decision**: Post structured comments to the originating GitHub issue using
`actions/github-script`.

**Rationale**:

- Native GitHub integration, no external dependencies
- Supports rich markdown formatting
- Easy to implement status updates (started, completed, failed)

**Comment Format**:

```markdown
## 🚀 SpecKit: Specification Creation Started

I'm creating a feature specification based on this issue.

**Status**: In Progress
**Branch**: `NNN-feature-name` (will be created)
**Triggered by**: Assignment to @speckit-agent

---
_This comment was posted by the SpecKit GitHub Action._
```text

### AD-005: Branch and PR Creation

**Decision**: Create branch using existing `create-new-feature.sh` script;
create PR using `gh` CLI.

**Rationale**:

- Leverages existing branch naming logic (NNN-feature-name)
- `gh` CLI is pre-installed in GitHub Actions runners
- Consistent with existing release workflow patterns

## Workflow Diagram

```text
┌─────────────────────────────────────────────────────────────────────┐
│                    GitHub Issue Assigned Event                       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 1: Validate Assignee                                           │
│  - Check if assignee matches configured speckit_assignees            │
│  - If no match → Exit silently                                       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 2: Post Acknowledgment Comment (< 30 seconds)                  │
│  - "SpecKit: Specification Creation Started"                         │
│  - Include triggered-by info and expected branch name                │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 3: Sanitize Issue Title → Branch Name                          │
│  - Remove special characters                                         │
│  - Determine next feature number                                     │
│  - Create valid branch name (NNN-feature-name)                       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 4: Check Idempotency                                           │
│  - Check if spec already exists for this issue                       │
│  - If exists → Post "already processed" comment and exit             │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 5: Generate Specification                                       │
│  - Create feature branch                                             │
│  - Invoke AI provider with issue title + body                        │
│  - Write spec.md to specs/NNN-feature-name/                          │
│  - Include source issue reference                                    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 6: Create PR (if enabled)                                       │
│  - Push branch to remote                                             │
│  - Create PR with spec summary                                       │
│  - Apply issue labels to PR                                          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 7: Post Completion Comment                                     │
│  - "SpecKit: Specification Created Successfully"                     │
│  - Include link to spec file and PR                                  │
│  - Or post error message if failed                                   │
└─────────────────────────────────────────────────────────────────────┘
```text

## Configuration Schema

### Workflow Inputs

| Input | Type | Required | Default | Description |
| ------- | ------ | ---------- | --------- | ------------- |
| `speckit_assignees` | string | No | `speckit-agent` | Comma-separated GitHub usernames that trigger SDD |
| `create_pr` | boolean | No | `true` | Create a PR with the generated specification |
| `create_branch` | boolean | No | `true` | Create a feature branch for the specification |
| `spec_base_path` | string | No | `specs` | Base directory for specification files |
| `comment_on_issue` | boolean | No | `true` | Post status comments on the originating issue |
| `ai_provider` | string | No | `claude` | AI provider for spec generation (claude, copilot, openai) |
| `base_branch` | string | No | `main` | Target branch for PRs |

### Repository Secrets

| Secret | Required For | Description |
| -------- | -------------- | ------------- |
| `ANTHROPIC_API_KEY` | ai_provider=claude | Claude API key for spec generation |
| `OPENAI_API_KEY` | ai_provider=openai | OpenAI API key for spec generation |
| `GITHUB_TOKEN` | Always | Auto-provided; used for issue comments and PR creation |

## Constitution Check (Post-Design)

- **Auto-Approval Friendly Design**: PASS — All inputs have defaults; no user

  interaction required during execution.
  interaction required during execution.

- **Single Source of Truth**: PASS — Configuration in workflow file; outputs in

  `specs/` directory.
  `specs/` directory.

- **Background Task Architecture**: N/A — GitHub Actions handles execution

  lifecycle.
  lifecycle.

- **Test-Driven Development**: PASS — Recommend testing with `act` and test

  issues.
  issues.

- **Code Quality & Maintainability**: PASS — Modular scripts with error

  handling and logging.
  handling and logging.

- **User Experience Consistency**: PASS — Structured comment templates with

  clear status indicators.
  clear status indicators.

- **Performance & Responsiveness**: PASS — Acknowledgment within 30 seconds;

  completion within 5 minutes.
  completion within 5 minutes.

- **Python Package Best Practices**: N/A — This feature is YAML/Bash-based.

## Complexity Tracking

No violations against the constitution identified. The feature is self-contained
within GitHub Actions and helper scripts, following established patterns from
the existing release workflow.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| ------ | ------------ | -------- | ------------ |
| AI API rate limits | Medium | Medium | Implement retry with backoff; document limits |
| GitHub API rate limits | Low | Low | Use conditional requests; cache where possible |
| Spec generation timeout | Low | Medium | Set explicit 5-minute timeout; post partial results |
| Concurrent issue assignments | Low | Low | Use issue-level lock via comment marker |
| Invalid branch name from title | Medium | Low | Robust sanitization in helper script |

## Next Steps

1. Run `/speckit.tasks` to break down implementation into actionable tasks
2. Implement workflow file with basic assignee validation (US1)
3. Add issue comment feedback (US3)
4. Implement spec generation with AI provider (US1)
5. Add PR creation capability (US4)
6. Test with various issue formats and edge cases
