# 3. System Context

## 3.1 Business Context

**agentic-devtools** acts as a bridge between AI assistants (GitHub Copilot) and external development services, enabling automated workflow execution in the Dragonfly platform development process.

```mermaid
C4Context
    title System Context Diagram - agentic-devtools

    Person(dev, "Developer", "Dragonfly platform developer")
    Person(ai, "AI Assistant", "GitHub Copilot Chat")
    
    System(agdt, "agentic-devtools", "CLI package for AI workflow automation")
    
    System_Ext(git, "Git/GitHub", "Version control")
    System_Ext(ado, "Azure DevOps", "Project management & CI/CD")
    System_Ext(jira, "Jira Cloud", "Issue tracking")
    System_Ext(pypi, "PyPI", "Python package index")
    System_Ext(azure, "Azure Cloud", "Cloud infrastructure")
    
    Rel(dev, ai, "Uses")
    Rel(ai, agdt, "Executes commands")
    Rel(agdt, git, "Commits, pushes, branches")
    Rel(agdt, ado, "PRs, comments, reviews")
    Rel(agdt, jira, "Issues, comments, updates")
    Rel(agdt, pypi, "Publishes packages")
    Rel(agdt, azure, "Manages resources")
```

## 3.2 External Interfaces

### 3.2.1 Git/GitHub

**Purpose**: Version control and repository management

**Interface**:

- Local Git commands (`git commit`, `git push`, `git worktree`)
- GitHub API for repository operations

**Data Flow**:

- **Outbound**: Commits, branches, tags
- **Inbound**: Branch status, commit history

### 3.2.2 Azure DevOps

**Purpose**: Pull requests, code reviews, CI/CD pipelines

**Interface**:

- Azure DevOps REST API v7.0
- Authentication via Personal Access Token (PAT)
- Endpoints: PRs, threads, comments, pipelines, work items

**Data Flow**:

- **Outbound**: PR comments, review approvals, thread replies, pipeline triggers
- **Inbound**: PR details, diffs, threads, pipeline status

### 3.2.3 Jira Cloud

**Purpose**: Issue tracking and project management

**Interface**:

- Jira REST API (Cloud, primarily v2 endpoints)
- Authentication via API token (bearer or basic with email/username)
- Endpoints: Issues, comments, transitions, custom fields

**Data Flow**:

- **Outbound**: Comments, status updates, field modifications
- **Inbound**: Issue details, metadata, subtasks, epics

### 3.2.4 PyPI

**Purpose**: Python package distribution

**Interface**:

- PyPI upload API (via Twine)
- Authentication via API token

**Data Flow**:

- **Outbound**: Package distributions (wheel, sdist)
- **Inbound**: Upload status, version existence checks

### 3.2.5 Azure Cloud

**Purpose**: Azure resource management (optional)

**Interface**:

- Azure CLI (`az` command)
- Azure REST APIs

**Data Flow**:

- **Outbound**: Resource configurations, deployments
- **Inbound**: Resource status, logs

## 3.3 User Interaction Model

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Copilot as GitHub Copilot
    participant CLI as agdt CLI
    participant State as State File
    participant API as External API
    
    Dev->>Copilot: "@workspace work on DFLY-1234"
    Copilot->>CLI: agdt-set jira.issue_key DFLY-1234
    CLI->>State: Write state
    State-->>CLI: OK
    CLI-->>Copilot: State saved
    
    Copilot->>CLI: agdt-get-jira-issue
    CLI->>State: Read state
    State-->>CLI: issue_key
    CLI->>API: GET /issue/DFLY-1234
    API-->>CLI: Issue details
    CLI->>State: Save metadata
    CLI-->>Copilot: Issue details (formatted)
    
    Copilot->>Dev: "Ready to work on issue..."
```

## 3.4 Command Approval Flow

```mermaid
stateDiagram-v2
    [*] --> FirstUse: Command executed
    FirstUse --> ApprovalPrompt: Not approved yet
    ApprovalPrompt --> Approved: User approves
    ApprovalPrompt --> Denied: User denies
    Approved --> Executed: All future invocations
    Denied --> [*]
    Executed --> [*]
    
    note right of ApprovalPrompt
        VS Code shows approval dialog
        once per unique command
    end note
    
    note right of Approved
        Generic commands (agdt-set)
        work for all keys after
        single approval
    end note
```

## 3.5 Background Task Execution Model

```mermaid
sequenceDiagram
    participant AI as AI Assistant
    participant Cmd as Command
    participant BG as Background Task
    participant File as Output File
    
    AI->>Cmd: Execute action command
    Cmd->>BG: Spawn background process
    BG-->>Cmd: Task ID
    Cmd-->>AI: Immediate return with task ID
    
    Note over AI: AI continues with other work
    
    AI->>Cmd: agdt-task-status
    Cmd->>BG: Check status
    BG-->>Cmd: Running/Complete/Failed
    Cmd-->>AI: Status info
    
    BG->>File: Write results
    BG->>BG: Update task state
    
    AI->>Cmd: agdt-task-wait
    Cmd->>BG: Poll until complete
    BG-->>Cmd: Complete
    Cmd-->>AI: Results location
```

## 3.6 Multi-Worktree Model

```mermaid
graph TB
    subgraph "Global Environment"
        Global[Global pip install]
    end
    
    subgraph "Repository"
        Main[main worktree]
        WT1[worktree-1]
        WT2[worktree-2]
    end
    
    subgraph "Local Environments"
        MainVenv[main/.agdt-venv]
        WT1Venv[worktree-1/.agdt-venv]
    end
    
    Main -->|Uses| MainVenv
    WT1 -->|Uses| WT1Venv
    WT2 -->|Uses| Global
    
    MainVenv -.->|Fallback| Global
    WT1Venv -.->|Fallback| Global
```
