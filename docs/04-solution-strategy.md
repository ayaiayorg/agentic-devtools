# 4. Solution Strategy

## 4.1 Technology Decisions

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| **Python** | Native CLI support, rich ecosystem, type hints, async/await | Node.js (complex approval), Bash (limited) |
| **argparse** | Standard library, no extra dependency, explicit flags | Click (extra dependency), Typer (overkill) |
| **JSON State File** | Simple, human-readable, no database | SQLite (overkill), YAML (parsing issues) |
| **Background Tasks** | Non-blocking AI agents, subprocess isolation | Threading (complex), Celery (heavyweight) |
| **Mermaid** | GitHub native, VS Code support, simple syntax | PlantUML (external), Graphviz (complex) |

## 4.2 Design Patterns

### 4.2.1 Command Pattern

All CLI commands follow a consistent pattern:

```mermaid
classDiagram
    class Command {
        <<interface>>
        +execute()
        +validate_state()
        +handle_errors()
    }
    
    class StateReader {
        +get_value(key)
        +load_state()
    }
    
    class ActionCommand {
        +spawn_background_task()
        +return_task_id()
    }
    
    class QueryCommand {
        +call_api()
        +write_output_file()
    }
    
    Command <|-- ActionCommand
    Command <|-- QueryCommand
    ActionCommand --> StateReader
    QueryCommand --> StateReader
```

### 4.2.2 State Management Pattern

Centralized state with namespaced keys:

```mermaid
graph LR
    subgraph "Command Layer"
        Cmd1[agdt-set]
        Cmd2[agdt-get]
        Cmd3[agdt-add-jira-comment]
    end
    
    subgraph "State Layer"
        Lock[File Lock]
        State[JSON State]
        Lock --> State
    end
    
    subgraph "Storage"
        File[agdt-state.json]
    end
    
    Cmd1 --> Lock
    Cmd2 --> Lock
    Cmd3 --> Lock
    State --> File
```

### 4.2.3 Background Task Pattern

Asynchronous execution with status tracking:

```mermaid
sequenceDiagram
    participant CLI
    participant Spawner
    participant Process
    participant State
    participant Output
    
    CLI->>Spawner: Execute action
    Spawner->>Process: subprocess.Popen()
    Process-->>Spawner: PID
    Spawner->>State: Save task metadata
    Spawner-->>CLI: Task ID
    
    Note over Process: Executes in background
    
    Process->>Output: Write stdout/stderr
    Process->>State: Update status
    Process->>Output: Write result file
```

## 4.3 Key Architectural Approaches

### 4.3.1 Auto-Approval Strategy

**Problem**: VS Code requires approval for each unique command

**Solution**: Generic commands with state-based parameters

```mermaid
graph TD
    A[❌ Bad: 100 Commands] -->|Requires| B[100 Approvals]
    C[✅ Good: Generic Commands] -->|Requires| D[~10 Approvals]
    
    B --> E[Bad UX]
    D --> F[Good UX]
    
    style A fill:#f99
    style C fill:#9f9
```

**Examples**:

- ❌ `agdt-add-pr-comment --pr-id 123 --message "..."` (unique per PR)
- ✅ `agdt-set pr_id 123` + `agdt-set content "..."` + `agdt-add-pr-comment` (reusable)

### 4.3.2 Multi-Worktree Strategy

**Problem**: Different branches may need different package versions

**Solution**: Auto-detect repo-local virtual environment

```mermaid
flowchart TD
    Start[Command Executed] --> Check{Local venv exists?}
    Check -->|Yes| UseLocal[Use .agdt-venv]
    Check -->|No| UseGlobal[Use global pip]
    UseLocal --> Execute[Execute Command]
    UseGlobal --> Execute
    Execute --> End[Return]
    
    style UseLocal fill:#9f9
    style UseGlobal fill:#ff9
```

### 4.3.3 Workflow Orchestration Strategy

**Problem**: Complex multi-step workflows are hard to manage

**Solution**: Step-based workflows with state transitions

```mermaid
stateDiagram-v2
    [*] --> Initiate
    Initiate --> Setup: Event: Started
    Setup --> Retrieve: Event: Worktree Ready
    Retrieve --> Planning: Event: Issue Loaded
    Planning --> ChecklistCreation: Event: Plan Posted
    ChecklistCreation --> Implementation: Event: Checklist Ready
    Implementation --> Verification: Event: Code Complete
    Verification --> Commit: Event: Tests Pass
    Commit --> PullRequest: Event: Changes Committed
    PullRequest --> Completion: Event: PR Created
    Completion --> [*]: Event: Comment Posted
```

## 4.4 Module Organization

```mermaid
graph TB
    subgraph "CLI Layer"
        State[state.py]
        Git[git/]
        ADO[azure_devops/]
        Jira[jira/]
        Tasks[tasks/]
        Workflows[workflows/]
    end
    
    subgraph "Core Layer"
        Dispatcher[dispatcher.py]
        BG[background_tasks.py]
        TaskState[task_state.py]
        Lock[file_locking.py]
    end
    
    subgraph "Data Layer"
        StateFile[agdt-state.json]
        OutputFiles[temp/*.json]
        Logs[logs/*.log]
    end
    
    State --> Dispatcher
    Git --> Dispatcher
    ADO --> Dispatcher
    Jira --> Dispatcher
    Tasks --> TaskState
    Workflows --> State
    
    Dispatcher --> Lock
    BG --> TaskState
    TaskState --> Lock
    
    Lock --> StateFile
    BG --> OutputFiles
    BG --> Logs
```

## 4.5 Quality Strategies

| Quality Goal | Strategy | Implementation |
|--------------|----------|----------------|
| **Usability** | Consistent command patterns | All commands follow same structure |
| **Reliability** | Comprehensive testing | 95%+ coverage, integration tests |
| **Performance** | Background execution | Long operations don't block |
| **Maintainability** | Modular packages | Each service in separate package |
| **Security** | Environment variables | No secrets in code or state |

## 4.6 Integration Strategy

```mermaid
flowchart LR
    subgraph "Integration Layers"
        CLI[CLI Commands]
        Helpers[Helper Functions]
        API[API Clients]
    end
    
    subgraph "External Services"
        ADO_API[Azure DevOps API]
        Jira_API[Jira API]
        Git_CLI[Git CLI]
    end
    
    CLI --> Helpers
    Helpers --> API
    API --> ADO_API
    API --> Jira_API
    API --> Git_CLI
    
    style CLI fill:#e1f5ff
    style Helpers fill:#fff4e1
    style API fill:#f5e1ff
```

## 4.7 Deployment Strategy

- **Distribution**: PyPI package (`pip install agentic-devtools`)
- **Installation**: Global via pip/pipx, or local via `.agdt-venv`
- **Configuration**: Environment variables for credentials
- **Updates**: Version from Git tags via hatch-vcs
- **CI/CD**: GitHub Actions for test, lint, publish
