# 6. Runtime View

## 6.1 Scenario: Work on Jira Issue (Complete Workflow)

This scenario demonstrates the full workflow from issue retrieval to PR creation.

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Copilot as GitHub Copilot
    participant State as State Manager
    participant Jira as Jira API
    participant Git as Git
    participant ADO as Azure DevOps

    Dev->>Copilot: /agdt.work-on-jira-issue.initiate
    Copilot->>State: set_workflow_state(name="work-on-jira-issue", status="active", step="initiate")
    Copilot-->>Dev: Prompt: Enter issue key

    Dev->>Copilot: DFLY-1234
    Copilot->>State: set_value("jira.issue_key", "DFLY-1234")

    Note over Copilot: Step 1: Setup Worktree
    Copilot->>Git: git worktree add
    Copilot->>Git: git checkout -b feature/DFLY-1234
    Copilot->>State: update_workflow_step("retrieve")

    Note over Copilot: Step 2: Retrieve Issue
    Copilot->>State: get_value("jira.issue_key")
    Copilot->>Jira: GET /issue/DFLY-1234
    Jira-->>Copilot: Issue details
    Copilot->>State: Save issue metadata
    Copilot->>State: update_workflow_step("planning")

    Note over Copilot: Step 3: Create Plan
    Copilot->>Copilot: Analyze issue
    Copilot->>State: set_value("jira.comment", "Plan...")
    Copilot->>Jira: POST /issue/DFLY-1234/comment
    Copilot->>State: update_workflow_step("checklist-creation")

    Note over Copilot: Step 4: Generate Checklist
    Copilot->>Copilot: Create implementation checklist
    Copilot->>State: Save checklist
    Copilot->>State: update_workflow_step("implementation")

    Note over Copilot: Step 5-6: Implementation
    loop For each checklist item
        Copilot->>Copilot: Write code
        Copilot->>Git: Stage changes
    end
    Copilot->>State: update_workflow_step("verification")

    Note over Copilot: Step 7: Verification
    Copilot->>Git: Run tests
    Copilot->>State: update_workflow_step("commit")

    Note over Copilot: Step 8: Commit
    Copilot->>State: set_value("commit_message", "feat: ...")
    Copilot->>Git: git commit
    Copilot->>Git: git push
    Copilot->>State: update_workflow_step("pull-request")

    Note over Copilot: Step 9: Create PR
    Copilot->>State: set_value("title", "feat(DFLY-1234): ...")
    Copilot->>ADO: POST /pullrequests
    ADO-->>Copilot: PR created
    Copilot->>State: update_workflow_step("completion")

    Note over Copilot: Step 10: Completion
    Copilot->>Jira: POST /issue/DFLY-1234/comment
    Copilot->>State: clear_workflow_state()
    Copilot-->>Dev: Workflow complete!
```

## 6.2 Scenario: Add Jira Comment (Background Task)

```mermaid
sequenceDiagram
    participant Copilot as GitHub Copilot
    participant CLI as CLI Command
    participant State as State File
    participant Spawner as Task Spawner
    participant Process as Background Process
    participant Jira as Jira API
    participant TaskState as Task State
    participant Log as Log File

    Copilot->>CLI: agdt-add-jira-comment
    CLI->>State: get_value("jira.issue_key")
    State-->>CLI: "DFLY-1234"
    CLI->>State: get_value("jira.comment")
    State-->>CLI: "Implementation complete"

    CLI->>Spawner: spawn_task(add_comment, ...)
    Spawner->>TaskState: create_task("add-jira-comment")
    TaskState-->>Spawner: task_id
    Spawner->>Process: subprocess.Popen()
    Process-->>Spawner: PID
    Spawner-->>CLI: task_id
    CLI-->>Copilot: Task started: 550e8400-e29b-41d4-a716-446655440000

    Note over Process: Executes in background

    Process->>Log: Write progress logs
    Process->>TaskState: update_status("running")
    Process->>Jira: POST /issue/DFLY-1234/comment
    Jira-->>Process: Comment created
    Process->>TaskState: update_status("completed")
    Process->>Log: Write success message

    Note over Copilot: Later...

    Copilot->>CLI: agdt-task-status
    CLI->>State: get_value("background.task_id")
    CLI->>TaskState: get_task(task_id)
    TaskState-->>CLI: Task metadata
    CLI-->>Copilot: Status: completed ✓
```

## 6.3 Scenario: Pull Request Review

```mermaid
sequenceDiagram
    participant Agent as Review Agent
    participant CLI as CLI Commands
    participant State as State Manager
    participant ADO as Azure DevOps API
    participant Queue as Review Queue

    Agent->>CLI: /agdt.pull-request-review.initiate
    CLI->>State: set_workflow_state(name="pull-request-review", status="active", step="initiate")
    CLI->>State: set_value("pull_request_id", "123")

    Agent->>CLI: agdt-get-pull-request-details
    CLI->>ADO: GET /pullrequests/123
    CLI->>ADO: GET /pullrequests/123/threads
    CLI->>ADO: GET /pullrequests/123/iterations
    ADO-->>CLI: PR details + diff
    CLI->>State: Save PR metadata
    CLI->>Queue: Create review queue

    Note over Agent: Step 2: File Review
    loop For each file in PR
        Agent->>CLI: agdt-set file_review.file_path "src/app.py"
        Agent->>Agent: Analyze file

        alt File approved
            Agent->>CLI: agdt-approve-file
            CLI->>ADO: POST /pullrequests/123/threads (comment)
            CLI->>ADO: PUT mark file as reviewed
            CLI->>Queue: Remove from queue
        else Changes requested
            Agent->>CLI: agdt-request-changes --line 42
            CLI->>ADO: POST /pullrequests/123/threads (at line 42)
            CLI->>ADO: PUT mark file as reviewed
            CLI->>Queue: Remove from queue
        end
    end

    Agent->>CLI: agdt-submit-file-review
    CLI->>State: update_workflow_step("summary")

    Note over Agent: Step 3: Generate Summary
    Agent->>CLI: agdt-generate-pr-summary
    CLI->>ADO: POST /pullrequests/123/threads (summary)
    CLI->>State: update_workflow_step("decision")

    Note over Agent: Step 4: Decision
    alt No blocking issues
        Agent->>CLI: agdt-approve-pull-request
        CLI->>ADO: POST /pullrequests/123/reviewers (approve)
    else Blocking issues found
        Agent->>CLI: agdt-mark-pull-request-draft
        CLI->>ADO: PATCH /pullrequests/123 (isDraft: true)
    end

    CLI->>State: clear_workflow_state()
    CLI-->>Agent: Review complete!
```

## 6.4 Scenario: Smart Git Commit (Amend Detection)

```mermaid
flowchart TD
    Start[agdt-git-save-work] --> GetMsg[Read commit_message from state]
    GetMsg --> GetKey{Has issue key<br/>in message?}
    GetKey -->|No| NewCommit[Create new commit]
    GetKey -->|Yes| CheckBranch{Branch has commits<br/>ahead of origin/main?}

    CheckBranch -->|No| NewCommit
    CheckBranch -->|Yes| CheckLast{Last commit has<br/>same issue key?}

    CheckLast -->|No| NewCommit
    CheckLast -->|Yes| Amend[Amend last commit]

    NewCommit --> StageAll[git add .]
    Amend --> StageAll

    StageAll --> CommitOp{New or Amend?}
    CommitOp -->|New| DoCommit[git commit -m]
    CommitOp -->|Amend| DoAmend[git commit --amend --no-edit]

    DoCommit --> Publish[git push -u origin branch]
    DoAmend --> ForcePush[git push --force-with-lease]

    Publish --> UpdateState[Update task state]
    ForcePush --> UpdateState
    UpdateState --> End[Return success]

    style Amend fill:#9f9
    style DoAmend fill:#9f9
    style ForcePush fill:#ff9
```

## 6.5 Scenario: Workflow Auto-Advancement

```mermaid
sequenceDiagram
    participant Cmd as Command
    participant State as State Manager
    participant Advance as Advancement Handler
    participant Prompt as Prompt Loader

    Cmd->>State: Complete operation
    Cmd->>Advance: trigger_event("CHECKLIST_CREATED")
    Advance->>State: get_workflow_state()
    State-->>Advance: Current workflow state

    Advance->>Advance: Check transition table
    Note over Advance: CHECKLIST_CREATED -> implementation

    alt auto_advance=true, no required_tasks
        Advance->>State: update_workflow_step("implementation")
        Advance->>Prompt: load_template("implementation")
        Prompt-->>Advance: Next prompt
        Advance-->>Cmd: Prompt printed to console
    else auto_advance=true, has required_tasks
        Advance->>State: Save pending_transition
        Advance-->>Cmd: Wait for background tasks
        Note over Cmd: Later: agdt-get-next-workflow-prompt
        Cmd->>Advance: Check pending transition
        Advance->>State: Check background tasks
        alt All tasks complete
            Advance->>State: update_workflow_step("next")
            Advance->>Prompt: load_template("next")
            Prompt-->>Cmd: Next prompt
        else Tasks still running
            Advance-->>Cmd: Wait longer
        end
    else auto_advance=false
        Advance-->>Cmd: Manual advancement required
    end
```

## 6.6 Error Handling Patterns

```mermaid
flowchart TD
    Start[Command Execution] --> Try{Try}
    Try -->|Success| Return[Return 0]
    Try -->|Error| Catch[Catch Exception]

    Catch --> Log[Log error details]
    Log --> Type{Error Type}

    Type -->|API Error| APIHandle[Format API response]
    Type -->|State Error| StateHandle[Show state key]
    Type -->|Validation Error| ValidHandle[Show missing values]
    Type -->|Unknown| GenHandle[Generic error message]

    APIHandle --> Print[Print to stderr]
    StateHandle --> Print
    ValidHandle --> Print
    GenHandle --> Print

    Print --> Update[Update task state if background]
    Update --> ReturnErr[Return non-zero exit code]
```

## 6.7 State Locking During Concurrent Access

```mermaid
sequenceDiagram
    participant Cmd1 as Command 1
    participant Cmd2 as Command 2
    participant Lock as File Lock
    participant State as State File

    par Command 1
        Cmd1->>Lock: acquire()
        Lock->>Lock: Wait for lock
        Lock-->>Cmd1: Lock acquired
        Cmd1->>State: Read/Write
        Cmd1->>Lock: release()
    and Command 2
        Cmd2->>Lock: acquire()
        Lock->>Lock: Wait (blocked by Cmd1)
        Note over Cmd2: Waiting...
        Lock-->>Cmd2: Lock acquired (after Cmd1 releases)
        Cmd2->>State: Read/Write
        Cmd2->>Lock: release()
    end
```
