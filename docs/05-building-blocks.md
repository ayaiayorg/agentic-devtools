# 5. Building Blocks View

## 5.1 Level 1: System Overview

```mermaid
graph TB
    subgraph "agentic-devtools Package"
        CLI[CLI Layer]
        Core[Core Infrastructure]
        Integrations[Service Integrations]
    end

    CLI --> Core
    CLI --> Integrations
    Integrations --> Core

    style CLI fill:#e1f5ff
    style Core fill:#fff4e1
    style Integrations fill:#f5e1ff
```

## 5.2 Level 2: Package Structure

```mermaid
graph TB
    subgraph "CLI Layer"
        StateCmd[state.py<br/>Generic set/get/delete]
        GitCmd[git/<br/>Workflow commands]
        ADOCmd[azure_devops/<br/>PR & review commands]
        JiraCmd[jira/<br/>Issue commands]
        TaskCmd[tasks/<br/>Task monitoring]
        WorkflowCmd[workflows/<br/>Workflow orchestration]
    end

    subgraph "Core Infrastructure"
        Runner[cli/runner.py<br/>Command routing]
        State[state.py<br/>State management]
        BG[background_tasks.py<br/>Async execution]
        TaskState[task_state.py<br/>Task tracking]
        Lock[file_locking.py<br/>Concurrency control]
    end

    subgraph "Support"
        Prompts[prompts/<br/>Template system]
    end

    StateCmd --> State
    GitCmd --> BG
    ADOCmd --> BG
    JiraCmd --> BG
    TaskCmd --> TaskState
    WorkflowCmd --> State

    State --> Lock
    BG --> TaskState
    TaskState --> Lock
    WorkflowCmd --> Prompts

    Runner --> StateCmd
    Runner --> GitCmd
    Runner --> ADOCmd
    Runner --> JiraCmd
    Runner --> TaskCmd
    Runner --> WorkflowCmd
```

Note: `Runner` here refers to `cli/runner.py`, which provides programmatic access to all commands by name.
Console script entry points call `cli.runner:run_as_script`, which uses `COMMAND_MAP` to route to the
appropriate CLI implementation function and centralizes routing and `KeyboardInterrupt` handling.

## 5.3 Level 3: Core Components

### 5.3.1 State Management

**Note**: The diagrams below show conceptual class representations for clarity. The actual implementation uses module-level functions rather than class-based APIs.

```mermaid
classDiagram
    class State {
        <<module functions>>
        +get_value(key) dict
        +set_value(key, value)
        +delete_key(key)
        +clear_state()
        +load_state() dict
        +save_state(data)
    }

    class FileLock {
        <<context manager>>
        +locked_state_file(path, timeout)
    }

    class WorkflowState {
        <<module functions>>
        +get_workflow_state() dict
        +set_workflow_state(name, status, step, context)
        +update_workflow_step(step)
        +update_workflow_context(**kwargs)
        +clear_workflow_state()
    }

    State --> FileLock : uses
    WorkflowState --> State : extends
```

**Responsibilities**:

- Persistent key-value storage
- Namespace management (e.g., `jira.`, `file_review.`)
- Concurrent access protection
- Workflow state tracking

### 5.3.2 Background Tasks

**Note**: The diagram below shows conceptual relationships. `BackgroundTask` is a dataclass in `task_state.py`, while spawning/monitoring is handled by module-level functions in `background_tasks.py`.

```mermaid
classDiagram
    class BackgroundTask {
        <<dataclass>>
        +id: str
        +name: str
        +command: str
        +status: str
        +started_at: datetime
        +completed_at: datetime
        +exit_code: int
        +output_file: str
        +log_file: str
    }

    class TaskFunctions {
        <<module functions>>
        +spawn_task(func, args) TaskID
        +get_task_status(task_id) Status
        +wait_for_task(task_id, timeout) Result
        +clean_expired_tasks()
        +create_task(name, command) TaskID
        +update_task_status(task_id, status)
        +get_task(task_id) Task
        +list_tasks() List~Task~
    }

    TaskFunctions --> BackgroundTask : manages
```

**Responsibilities**:

- Spawn subprocess for long operations
- Track task status and metadata
- Capture stdout/stderr to log files
- Write results to output files
- Clean up expired tasks

### 5.3.3 Command Runner

```mermaid
flowchart TD
    Entry[Command Entry Point] --> Route[Route to<br/>command module]
    Route --> Exec[Execute command]
    Exec --> Exit[Return exit code]
```

**Responsibilities**:

- Map command names to implementation modules
- Import and invoke the appropriate command handler

## 5.4 Service Integration Modules

### 5.4.1 Azure DevOps Module

```mermaid
graph TB
    subgraph "azure_devops/"
        Config[config.py<br/>Constants & Config]
        Auth[auth.py<br/>PAT & headers]
        Helpers[helpers.py<br/>Utility functions]
        Commands[commands.py<br/>PR commands]
        FileReview[file_review_commands.py<br/>File-level review]
        ReviewCmds[review_commands.py<br/>PR review workflow]
        Mark[mark_reviewed.py<br/>Mark files reviewed]
    end

    Commands --> Auth
    Commands --> Helpers
    FileReview --> Commands
    ReviewCmds --> Commands
    ReviewCmds --> FileReview
    Mark --> Auth
    FileReview --> Mark

    Auth --> Config
    Helpers --> Config
```

**Responsibilities**:

- Authenticate with Azure DevOps PAT
- Create/update pull requests
- Add PR comments and thread replies
- Manage PR review workflow
- Mark files as reviewed
- Trigger pipelines

### 5.4.2 Jira Module

```mermaid
graph TB
    subgraph "jira/"
        Config[config.py<br/>Jira config & auth]
        Commands[commands.py<br/>Sync commands]
        UpdateCmds[update_commands.py<br/>Issue updates]
        AsyncCmds[async_commands.py<br/>Background wrappers]
    end

    Commands --> Config
    UpdateCmds --> Config
    AsyncCmds --> Commands
    AsyncCmds --> UpdateCmds
```

**Responsibilities**:

- Authenticate with Jira API token
- Fetch issue details
- Add comments to issues
- Update issue fields
- Create issues, epics, subtasks
- Manage project roles

### 5.4.3 Git Module

```mermaid
graph TB
    subgraph "git/"
        Core[core.py<br/>Git execution & state]
        Operations[operations.py<br/>Git operations]
        Commands[commands.py<br/>CLI commands]
    end

    Commands --> Operations
    Operations --> Core
```

**Responsibilities**:

- Execute git commands
- Stage, commit, push changes
- Manage branches and worktrees
- Smart commit/amend detection
- Checklist integration

## 5.5 Workflow System

```mermaid
graph TB
    subgraph "workflows/"
        Base[base.py<br/>Base utilities]
        Cmds[commands.py<br/>Workflow initiation]
        Preflight[preflight.py<br/>Pre-flight checks]
        Advance[advancement.py<br/>Auto-advancement]
    end

    subgraph "prompts/"
        Loader[loader.py<br/>Template loading]
    end

    Cmds --> Base
    Preflight --> Base
    Advance --> Base
    Cmds --> Loader
    Advance --> Loader
```

**Workflow Types**:

1. **work-on-jira-issue**: 11-step workflow from issue to PR
2. **pull-request-review**: 5-step PR review workflow
3. **apply-pr-suggestions**: Apply review feedback
4. **create-jira-issue/epic/subtask**: Jira item creation

**Workflow State Machine**:

```mermaid
stateDiagram-v2
    [*] --> Active: initiate_workflow
    Active --> Active: update_workflow_step
    Active --> [*]: clear_workflow_state

    state Active {
        [*] --> Step1
        Step1 --> Step2: advance_workflow
        Step2 --> Step3: advance_workflow
        Step3 --> [*]
    }
```

## 5.6 Data Flow

### 5.6.1 Command Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant State
    participant BG as Background Task
    participant API as External API
    participant File as Output File

    User->>CLI: agdt-set jira.issue_key DFLY-1234
    CLI->>State: set_value("jira.issue_key", "DFLY-1234")
    State-->>CLI: OK
    CLI-->>User: Value saved

    User->>CLI: agdt-get-jira-issue
    CLI->>State: get_value("jira.issue_key")
    State-->>CLI: "DFLY-1234"
    CLI->>BG: Spawn background task
    BG-->>CLI: Task ID
    CLI-->>User: Task started: 550e8400-e29b-41d4-a716-446655440000

    BG->>API: GET /issue/DFLY-1234
    API-->>BG: Issue data
    BG->>File: Write JSON
    BG->>State: Save metadata
```

### 5.6.2 Workflow Execution Flow

```mermaid
sequenceDiagram
    participant Agent as Copilot Agent
    participant CLI
    participant State
    participant Prompt as Prompt Loader

    Agent->>CLI: /agdt.work-on-jira-issue.initiate
    CLI->>State: set_workflow_state(...)
    CLI->>Prompt: load_template("initiate")
    Prompt-->>CLI: Prompt text
    CLI-->>Agent: Prompt for next step

    Agent->>CLI: Execute commands from prompt
    CLI->>State: Update workflow context

    Agent->>CLI: agdt-advance-workflow
    CLI->>State: update_workflow_step(next_step)
    CLI->>Prompt: load_template(next_step)
    Prompt-->>CLI: Next prompt
    CLI-->>Agent: Next step prompt
```

## 5.7 Key Interfaces

| Component | Public Interface | Consumers |
|-----------|-----------------|-----------|
| **state.py** | `get_value`, `set_value`, `delete_key`, `clear_state` | All CLI commands |
| **background_tasks.py** | `spawn_task`, `get_task_status`, `wait_for_task` | Action commands |
| **task_state.py** | `create_task`, `update_task_status`, `get_task`, `list_tasks` | Background tasks |
| **cli/runner.py** | Command routing | Entry points, programmatic use |
| **prompts/loader.py** | `load_template`, `substitute_variables`, `save_output` | Workflow commands |
