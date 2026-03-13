# 9. Architecture Decisions

All Architecture Decision Records (ADRs) are stored as standalone files under
[`docs/architecture-decisions/`](architecture-decisions/).

## 9.1 Decision Summary Table

| ADR | Decision | Status | Impact |
|-----|----------|--------|--------|
| 001 | [Single JSON state file](architecture-decisions/ADR-001-state-management-single-json-file.md) | 🔄 Superseded | Core architecture |
| 002 | [Parameterless commands](architecture-decisions/ADR-002-parameterless-command-pattern.md) | ✅ Accepted | UX foundation |
| 003 | [Background tasks](architecture-decisions/ADR-003-background-task-execution.md) | ✅ Accepted | Performance critical |
| 004 | [Multi-worktree support](architecture-decisions/ADR-004-multi-worktree-support.md) | ✅ Accepted | Developer experience |
| 005 | [Workflow state machine](architecture-decisions/ADR-005-workflow-state-machine-pattern.md) | ✅ Accepted | Workflow orchestration |
| 006 | [Mermaid diagrams](architecture-decisions/ADR-006-mermaid-diagrams.md) | ✅ Accepted | Documentation |
| 007 | [argparse CLI](architecture-decisions/ADR-007-argparse-cli.md) | ✅ Accepted | CLI foundation |
| 008 | [pyproject.toml](architecture-decisions/ADR-008-pyproject-toml.md) | ✅ Accepted | Package configuration |
| 009 | [Dynamic versioning](architecture-decisions/ADR-009-dynamic-versioning-git-tags.md) | ✅ Accepted | Release management |
| 010 | [Azure DevOps primary](architecture-decisions/ADR-010-azure-devops-primary.md) | ✅ Accepted | Service integration |
| 011 | [100% test coverage](architecture-decisions/ADR-011-test-coverage-requirement.md) | ✅ Accepted | Quality assurance |
| 012 | [Cross-platform locking](architecture-decisions/ADR-012-cross-platform-file-locking.md) | ✅ Accepted | Concurrency control |
| 013 | [Orchestration framework selection](architecture-decisions/ADR-013-orchestration-framework-selection.md) | ✅ Accepted | Core architecture |
