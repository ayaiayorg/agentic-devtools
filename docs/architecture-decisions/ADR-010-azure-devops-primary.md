# ADR-010: Azure DevOps as Primary VCS

**Status**: Accepted

**Context**: Dragonfly team uses Azure DevOps for repositories and project management

**Decision**: Azure DevOps integration is first-class; GitHub is secondary

**Rationale**:

- Team's primary platform
- PR reviews in Azure DevOps
- CI/CD pipelines in Azure DevOps
- Work items in Azure DevOps

**Consequences**:

- ✅ Full Azure DevOps feature parity
- ✅ Custom PR review workflow
- ✅ Pipeline trigger commands
- ⚠️ GitHub integration is limited
- ⚠️ Requires Azure DevOps PAT
