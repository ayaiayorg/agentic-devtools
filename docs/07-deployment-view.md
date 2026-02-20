# 7. Deployment View

## 7.1 Installation Options

```mermaid
graph TB
    subgraph "Installation Methods"
        Pipx[pipx install<br/>Recommended]
        PipGlobal[pip install<br/>Global]
        PipUser[pip install --user<br/>Not recommended]
        DevInstall[pip install -e .<br/>Development]
    end
    
    subgraph "Execution Environments"
        GlobalEnv[Global Python<br/>Site-packages]
        PipxEnv[Isolated pipx venv]
    end
    
    Pipx --> PipxEnv
    PipGlobal --> GlobalEnv
    PipUser --> GlobalEnv
    DevInstall --> GlobalEnv
    
    style Pipx fill:#9f9
```

## 7.2 Runtime Environment

### 7.2.1 Single Worktree Deployment

```mermaid
graph TB
    subgraph "Developer Machine"
        User[Developer]
        VSCode[VS Code + Copilot]
        Terminal[Terminal/Shell]
    end
    
    subgraph "Global Environment"
        Python[Python 3.8+]
        AgdtPkg[agentic-devtools<br/>Global install]
    end
    
    subgraph "Repository"
        Repo[Git Repository]
        State[scripts/temp/<br/>agdt-state.json]
        Temp[scripts/temp/<br/>Output files]
    end
    
    subgraph "External Services"
        Git[Git/GitHub]
        ADO[Azure DevOps]
        Jira[Jira Cloud]
    end
    
    User --> VSCode
    VSCode --> Terminal
    Terminal --> AgdtPkg
    AgdtPkg --> Python
    AgdtPkg --> State
    AgdtPkg --> Temp
    AgdtPkg --> Git
    AgdtPkg --> ADO
    AgdtPkg --> Jira
    
    State -.->|Excluded| Repo
    Temp -.->|Excluded| Repo
```

### 7.2.2 Multi-Worktree Deployment

```mermaid
graph TB
    subgraph "Developer Machine"
        User[Developer]
        Shell[Shell]
    end
    
    subgraph "Global Environment"
        Python[Python 3.8+]
        GlobalAgdt[agentic-devtools<br/>Global]
    end
    
    subgraph "Main Worktree"
        MainRepo[main branch]
        MainState[agdt-state.json]
    end
    
    subgraph "Feature Worktree 1"
        WT1[feature/DFLY-1234]
        WT1State[agdt-state.json]
    end
    
    subgraph "Feature Worktree 2"
        WT2[feature/DFLY-5678]
        WT2State[agdt-state.json]
    end
    
    User --> Shell
    Shell --> GlobalAgdt
    GlobalAgdt --> Python
    
    GlobalAgdt --> MainState
    GlobalAgdt --> WT1State
    GlobalAgdt --> WT2State
    
    style GlobalAgdt fill:#9f9
```

## 7.3 CI/CD Deployment

```mermaid
graph TB
    subgraph "Developer"
        Dev[Developer]
        LocalGit[Local Git]
    end
    
    subgraph "GitHub"
        Repo[GitHub Repository]
        Actions[GitHub Actions]
    end
    
    subgraph "Workflows"
        Test[Test Workflow]
        Lint[Lint Workflow]
        Publish[Publish Workflow]
        Release[Release Workflow]
    end
    
    subgraph "PyPI"
        PyPI[PyPI Package Index]
    end
    
    Dev -->|Push| LocalGit
    LocalGit -->|Push| Repo
    Repo -->|Trigger| Actions
    Actions --> Test
    Actions --> Lint
    Actions --> Publish
    Actions --> Release
    
    Publish -->|Upload| PyPI
    
    Test -.->|Block if fail| Publish
    Lint -.->|Block if fail| Publish
```

## 7.4 GitHub Actions Workflow Deployment

```mermaid
flowchart TD
    Push[Git Push] --> Trigger{Event Type}
    
    Trigger -->|Push to main| Test[test.yml]
    Trigger -->|Push to main| Lint[lint.yml]
    Trigger -->|Release created| Publish[publish.yml]
    
    Test --> RunTests[Run pytest]
    RunTests --> Coverage[Check coverage ≥91%]
    Coverage -->|Pass| TestPass[✓ Tests Pass]
    Coverage -->|Fail| TestFail[✗ Tests Fail]
    
    Lint --> RunMarkdown[markdownlint]
    Lint --> RunPython[Python linters]
    RunMarkdown --> LintPass[✓ Lint Pass]
    RunPython --> LintPass
    
    Publish --> FetchTags[Checkout with tags]
    FetchTags --> Build[Build package]
    Build --> Extract[Extract version]
    Extract --> Validate[twine check]
    Validate --> CheckPyPI{Version exists<br/>on PyPI?}
    CheckPyPI -->|No| Upload[Upload to PyPI]
    CheckPyPI -->|Yes| Skip[Skip upload]
    Upload --> Published[✓ Published]
    
    TestFail --> Notify[Notify @copilot]
    
    style TestPass fill:#9f9
    style LintPass fill:#9f9
    style Published fill:#9f9
    style TestFail fill:#f99
    style Skip fill:#ff9
```

## 7.5 State File Deployment

```mermaid
graph TB
    subgraph "Repository Structure"
        Root[Repository Root]
        Scripts[scripts/]
        Temp[scripts/temp/]
        State[agdt-state.json]
        Output[Output files<br/>*.json]
        Logs[scripts/temp/background-tasks/logs/]
    end
    
    subgraph "Git Tracking"
        Tracked[Tracked Files]
        Gitignore[.gitignore]
        Ignored[Ignored Files]
    end
    
    Root --> Scripts
    Scripts --> Temp
    Temp --> State
    Temp --> Output
    Temp --> Logs
    
    State --> Ignored
    Output --> Ignored
    Logs --> Ignored
    Gitignore --> Ignored
    
    Scripts --> Tracked
    
    style Ignored fill:#f99
    style Tracked fill:#9f9
```

**State File Locations**:

- Default: `scripts/temp/agdt-state.json`
- Excluded from Git via `.gitignore`
- One state file per worktree
- Background task logs in `scripts/temp/background-tasks/logs/`
- Output files in `scripts/temp/`

## 7.6 Configuration Deployment

```mermaid
graph TB
    subgraph "Configuration Sources"
        EnvVars[Environment Variables]
        StateFile[State File]
        CLI[CLI Arguments]
    end
    
    subgraph "Configuration Keys"
        ADO_PAT[AZURE_DEV_OPS_COPILOT_PAT<br/>AZURE_DEVOPS_EXT_PAT]
        Jira_Token[JIRA_COPILOT_PAT]
        Jira_Email[JIRA_EMAIL/JIRA_USERNAME]
    end
    
    subgraph "Command Execution"
        Commands[agdt-* Commands]
    end
    
    EnvVars --> ADO_PAT
    EnvVars --> Jira_Token
    EnvVars --> Jira_Email
    
    StateFile --> Commands
    CLI --> Commands
    
    ADO_PAT --> Commands
    Jira_Token --> Commands
    Jira_Email --> Commands
    
    style EnvVars fill:#9cf
    style StateFile fill:#9f9
    style CLI fill:#ff9
```

## 7.7 Network Communication

```mermaid
graph TB
    subgraph "Local Machine"
        CLI[agdt-* Commands]
    end
    
    subgraph "External APIs"
        ADO_API[Azure DevOps REST API<br/>HTTPS]
        Jira_API[Jira REST API<br/>HTTPS]
        PyPI_API[PyPI Upload API<br/>HTTPS]
        Git_SSH[Git Remote<br/>SSH/HTTPS]
    end
    
    CLI -->|PAT Auth| ADO_API
    CLI -->|Token + Email Auth| Jira_API
    CLI -->|Token Auth| PyPI_API
    CLI -->|SSH/HTTPS| Git_SSH
    
    style CLI fill:#9cf
    style ADO_API fill:#f99
    style Jira_API fill:#f99
    style PyPI_API fill:#f99
    style Git_SSH fill:#f99
```

**Network Requirements**:

- Internet connectivity for external APIs
- HTTPS/TLS for all API communication
- SSH or HTTPS for Git operations
- Proxy support via standard environment variables

## 7.8 Security Deployment

```mermaid
graph TB
    subgraph "Credential Storage"
        EnvFile[.env file<br/>NOT in repo]
        System[System environment<br/>variables]
        KeyStore[OS keystore<br/>optional]
    end
    
    subgraph "Protection Mechanisms"
        Gitignore[.gitignore]
        FilePerm[File permissions]
        NoLog[No secrets in logs]
    end
    
    subgraph "Usage"
        Commands[agdt-* Commands]
    end
    
    EnvFile -.->|Load into| System
    KeyStore -.->|Load into| System
    System --> Commands
    
    Gitignore -->|Excludes| EnvFile
    FilePerm -->|Protects| EnvFile
    NoLog -->|Filters| Commands
    
    style EnvFile fill:#f99
    style Gitignore fill:#9f9
    style NoLog fill:#9f9
```

**Security Best Practices**:

1. **Credentials**: Store in environment variables only
2. **State File**: Excluded from Git, contains no secrets
3. **Logs**: Sanitize sensitive data before writing
4. **Output Files**: Excluded from Git, may contain temporary data
5. **File Permissions**: Restrict access to state and temp directories

## 7.9 Package Dependencies

```mermaid
graph TB
    subgraph "Runtime Dependencies"
        Requests[requests>=2.28]
        Jinja2[Jinja2>=3.0]
        AzureMonitor[azure-monitor-query]
        AzureIdentity[azure-identity]
    end
    
    subgraph "Build Dependencies"
        Hatch[hatch-vcs]
        Build[build>=1.2.2]
        Twine[twine>=5.0.0]
    end
    
    subgraph "Dev Dependencies"
        Pytest[pytest>=7.0]
        Coverage[pytest-cov]
        Black[black]
        MyPy[mypy]
        Ruff[ruff]
    end
    
    subgraph "agentic-devtools"
        Package[Package Code]
    end
    
    Package --> Requests
    Package --> Jinja2
    Package --> AzureMonitor
    Package --> AzureIdentity
    
    Build --> Hatch
    Build --> Twine
    
    style Package fill:#9cf
    style Requests fill:#9f9
    style Jinja2 fill:#9f9
```
