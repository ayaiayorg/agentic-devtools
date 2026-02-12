# SpecKit Issue Workflow Sequence Diagram

This diagram illustrates the complete flow of the SpecKit Issue as
Starter Action workflow, showing the interactions between different
actors and systems when a GitHub issue triggers the Spec-Driven
Development (SDD) process.

## Overview

The SpecKit workflow automates the creation of feature specifications
from GitHub issues, following the SDD pattern. This diagram shows:

- **Who**: The actors involved (User, GitHub, AI Provider, Repository)
- **What**: The actions and processes that occur
- **When**: The sequence and timing of events
- **Why**: The purpose behind each step

## Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    
    actor User as Repository Maintainer
    participant GH as GitHub
    participant Action as SpecKit Action
    participant API as AI Provider<br/>(Claude/OpenAI)
    participant Repo as Repository
    participant Issue as Issue Thread
    
    Note over User,Issue: Phase 1: Initiation
    
    User->>GH: Create GitHub issue with feature request
    activate GH
    Note right of User: Issue contains:<br/>- Title<br/>- Description<br/>- Context
    
    User->>Issue: Add "speckit" label to issue
    GH->>Action: Trigger workflow (issues.labeled event)
    deactivate GH
    
    activate Action
    Note over Action: Workflow starts<br/>(within seconds)
    
    Action->>Issue: Post "🚀 Started" comment
    Note right of Action: Quick acknowledgment<br/>(< 30 seconds target)
    
    Action->>Issue: Replace "speckit" label with "speckit:processing"
    
    Note over User,Issue: Phase 2: Validation & Setup
    
    Action->>Repo: Checkout repository
    Action->>Repo: Check for existing spec (idempotency)
    
    alt Specification already exists
        Action->>Issue: Post "ℹ️ Already Exists" comment
        Note right of Action: Prevents duplicates
        Action->>Issue: Remove "speckit:processing" label
        Action-->>User: Workflow complete (no-op)
    else No existing specification
        Action->>Action: Sanitize issue title for branch name
        Note right of Action: Creates valid branch name<br/>from issue title
        
        Action->>Action: Calculate next feature number
        Note right of Action: Finds highest number<br/>from branches & specs
        
        Action->>Repo: Create spec directory<br/>specs/NNN-feature-name/
        
        Note over User,Issue: Phase 3: AI Specification Generation
        
        Action->>Action: Load spec template
        Note right of Action: From .specify/templates/<br/>
spec-template.md
        
        Action->>Action: Build AI prompt
        Note right of Action: Includes:<br/>- Issue details<br/>
- Template structure<br/>- SDD guidelines
        
        Action->>API: Request spec generation
        activate API
        Note right of API: Uses Claude Sonnet 4<br/>or GPT-4o
        
        API->>API: Generate specification
        Note right of API: Creates:<br/>- User stories (P1-P3)<br/>
- Requirements<br/>- Success criteria<br/>- Edge cases
        
        API-->>Action: Return generated specification
        deactivate API
        
        alt AI API succeeds
            Action->>Action: Validate generated content
        else AI API fails
            Action->>Action: Generate basic spec template
            Note right of Action: Fallback: Creates<br/>
minimal spec with<br/>[NEEDS CLARIFICATION]<br/>markers
        end
        
        Note over User,Issue: Phase 4: Artifact Creation
        
        Action->>Repo: Write spec.md
        Note right of Action: specs/NNN-feature-name/<br/>spec.md
        
        Action->>Repo: Create requirements checklist
        Note right of Action: specs/NNN-feature-name/<br/>
checklists/<br/>requirements.md
        
        Action->>Repo: Create feature branch
        Note right of Action: Branch: NNN-feature-name
        
        Action->>Repo: Commit specification files
        Note right of Action: Commit message:<br/>
"spec: Add specification<br/>for issue #N"
        
        Action->>Repo: Push feature branch
        
        Note over User,Issue: Phase 5: Pull Request Creation
        
        Action->>GH: Create Pull Request
        activate GH
        Note right of Action: PR contains:<br/>- Spec files<br/>
- Checklist<br/>- Link to issue
        
        GH->>GH: Generate PR number
        GH-->>Action: Return PR URL
        deactivate GH
        
        Action->>GH: Apply labels to PR
        Note right of Action: Labels:<br/>- From original issue<br/>- speckit:spec
        
        Note over User,Issue: Phase 6: Completion & Feedback
        
        Action->>Issue: Post "✅ Success" comment
        Note right of Action: Includes:<br/>- Branch name<br/>
- Spec file path<br/>- PR link<br/>- Next steps
        
        Action->>Issue: Update labels
        Note right of Action: Remove: speckit:processing<br/>Add: speckit:completed
        
        deactivate Action
        
        GH-->>User: Notification (Issue & PR)
        
        Note over User,Issue: Phase 7: Review & Iteration
        
        User->>Repo: Review generated spec.md
        User->>Repo: Review requirements checklist
        
        alt Clarifications needed
            User->>Issue: Comment with questions
            User->>Repo: Update spec manually
            User->>Repo: Commit changes to PR
            Note right of User: Refine specification<br/>as needed
        else Specification approved
            User->>GH: Approve PR
            User->>Repo: Merge PR
            Note right of User: Spec merged to main
        end
    end
    
    Note over User,Issue: Phase 8: Next Steps (Manual)
    
    User->>User: Run /speckit.plan command
    Note right of User: AI creates implementation<br/>plan with technical details
    
    User->>User: Run /speckit.tasks command  
    Note right of User: AI generates task<br/>breakdown organized<br/>by user stories
    
    User->>User: Run /speckit.implement command
    Note right of User: AI executes tasks<br/>following the plan

    Note over User,Issue: Workflow Complete
```

## Key Actors

| Actor | Role | Responsibilities |
| ------- | ------ | ----------------- |
| **Repository Maintainer** | Human | Creates issue, adds label, reviews spec |
| **GitHub** | Platform | Hosts repo, manages webhooks, triggers workflows |
| **SpecKit Action** | Automation | Orchestrates workflow, generates artifacts |
| **AI Provider** | Intelligence | Generates spec content (Claude/OpenAI) |
| **Repository** | Storage | Stores code, specs, branches |
| **Issue Thread** | Communication | Provides feedback and status updates |

## Workflow Phases

### Phase 1: Initiation (Steps 1-5)

**Purpose**: User triggers the workflow by adding a label to an issue.

**Key Events**:

- User creates issue with feature description
- User adds `speckit` label
- Workflow triggers immediately
- Quick acknowledgment posted (< 30 seconds)

### Phase 2: Validation & Setup (Steps 6-11)

**Purpose**: Validate inputs and prepare the repository structure.

**Key Events**:

- Check for existing specifications (idempotency)
- Sanitize issue title for branch naming
- Calculate next sequential feature number
- Create spec directory structure

### Phase 3: AI Specification Generation (Steps 12-19)

**Purpose**: Generate comprehensive specification using AI.

**Key Events**:

- Load specification template
- Build AI prompt with context
- Call AI provider API (Claude or OpenAI)
- Validate or fallback to basic template

### Phase 4: Artifact Creation (Steps 20-26)

**Purpose**: Create and commit specification files.

**Key Events**:

- Write spec.md with generated content
- Create requirements checklist
- Create and checkout feature branch
- Commit and push changes

### Phase 5: Pull Request Creation (Steps 27-31)

**Purpose**: Open PR for specification review.

**Key Events**:

- Create PR with spec files
- Apply labels from issue
- Add speckit-specific labels
- Link PR to source issue

### Phase 6: Completion & Feedback (Steps 32-36)

**Purpose**: Notify user and update issue status.

**Key Events**:

- Post success comment with details
- Update issue labels
- Send GitHub notifications
- Provide next steps guidance

### Phase 7: Review & Iteration (Steps 37-44)

**Purpose**: Human review and refinement of specification.

**Key Events**:

- User reviews generated specification
- User addresses clarification markers
- User approves or requests changes
- User merges PR when ready

### Phase 8: Next Steps (Steps 45-47)

**Purpose**: Continue SDD workflow with subsequent commands.

**Key Events**:

- User runs `/speckit.plan` for technical planning
- User runs `/speckit.tasks` for task breakdown
- User runs `/speckit.implement` for execution

## Decision Points

### Idempotency Check (Step 8)

- **Condition**: Does a spec already exist for this issue?
- **If Yes**: Exit gracefully with informative message
- **If No**: Proceed with generation

### AI Generation Success (Step 19)

- **Condition**: Did the AI API call succeed?
- **If Yes**: Use generated specification
- **If No**: Fallback to basic template with clarification markers

### Clarification Needs (Step 42)

- **Condition**: Does the spec have `[NEEDS CLARIFICATION]` markers?
- **If Yes**: User updates spec manually
- **If No**: User approves and merges

## SDD Pattern Alignment

This workflow follows the Spec-Driven Development (SDD) pattern
by:

1. **Intent-Driven**: Focuses on "what" (user needs) before "how"
   (implementation)
2. **Rich Specifications**: Generates detailed, structured
   specifications
3. **Multi-Step Refinement**: Supports iterative improvement through PR
   reviews
4. **AI-Native**: Designed for AI assistant collaboration at every
   phase

## Configuration Options

The workflow behavior can be customized via repository variables:

| Variable | Default | Purpose |
| ---------- | --------- | --------- |
| `SPECKIT_TRIGGER_LABEL` | `speckit` | Label that triggers workflow |
| `SPECKIT_CREATE_PR` | `true` | Create PR automatically |
| `SPECKIT_CREATE_BRANCH` | `true` | Create feature branch |
| `SPECKIT_COMMENT_ON_ISSUE` | `true` | Post status comments |
| `SPECKIT_AI_PROVIDER` | `claude` | AI provider (claude/openai) |

## Error Handling

The workflow handles errors gracefully:

- **AI API Failure**: Falls back to basic template
- **Missing API Keys**: Posts error comment with troubleshooting
  steps
- **Permission Issues**: Logs error and posts failure comment
- **Duplicate Specs**: Exits with informative message (idempotent)

## Performance Targets

| Metric | Target | Purpose |
| -------- | -------- | --------- |
| Initial acknowledgment | < 30 seconds | User confidence |
| Full workflow completion | < 5 minutes | Reasonable wait time |
| Idempotency check | < 5 seconds | Fast duplicate detection |

## Integration Points

### With GitHub

- **Webhooks**: `issues.labeled` event
- **API**: Issue comments, PR creation, label management
- **Authentication**: Uses `GITHUB_TOKEN`

### With AI Providers

- **Claude**: Anthropic API (claude-sonnet-4-20250514)
- **OpenAI**: Chat completions API (gpt-4o)
- **Authentication**: Requires `ANTHROPIC_API_KEY` or
  `OPENAI_API_KEY`

### With SDD Workflow

- **Inputs**: Issue title and body
- **Outputs**: Specification file and checklist
- **Next Steps**: `/speckit.plan`, `/speckit.tasks`, `/speckit.implement`

## Success Criteria

The workflow is successful when:

1. ✅ Specification file created in correct location
2. ✅ Requirements checklist generated
3. ✅ Feature branch created and pushed
4. ✅ Pull request opened with proper labels
5. ✅ Issue updated with status and next steps
6. ✅ User receives clear guidance on what to do next

## Future Enhancements

Potential improvements to the workflow:

- [ ] Automatic specification validation before PR creation
- [ ] Integration with project management tools (Jira, Azure
      DevOps)
- [ ] Slack/Discord notifications
- [ ] Automatic assignment of reviewers based on CODEOWNERS
- [ ] Template customization per repository
- [ ] Multi-language specification generation

## Related Documentation

- [Spec-Driven Development Guide](../../SPEC_DRIVEN_DEVELOPMENT.md)
- [SpecKit Workflow Source](.github/workflows/speckit-issue-trigger.yml)
- [Feature Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Task Breakdown](./tasks.md)
