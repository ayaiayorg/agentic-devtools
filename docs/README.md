# agentic-devtools Architecture Documentation

This directory contains the architecture documentation for the **agentic-devtools** project, structured according to the [arc42 template](https://arc42.org/).

## Overview

**agentic-devtools** is a Python CLI package that provides auto-approvable commands for AI assistants (GitHub Copilot) to interact with Git, Azure DevOps,
Jira, and other services in the Dragonfly platform development workflow.

## Documentation Structure

The documentation follows the arc42 template and is organized into the following sections:

1. [Introduction and Goals](01-introduction-and-goals.md)
2. [Architecture Constraints](02-architecture-constraints.md)
3. [System Context](03-system-context.md)
4. [Solution Strategy](04-solution-strategy.md)
5. [Building Blocks View](05-building-blocks.md)
6. [Runtime View](06-runtime-view.md)
7. [Deployment View](07-deployment-view.md)
8. [Cross-cutting Concepts](08-cross-cutting-concepts.md)
9. [Architecture Decisions](09-architecture-decisions.md)
10. [Quality Requirements](10-quality-requirements.md)
11. [Risks and Technical Debt](11-risks-and-technical-debt.md)
12. [Glossary](12-glossary.md)

## Quick Links

- **Getting Started**: See [Introduction and Goals](01-introduction-and-goals.md)
- **High-Level Architecture**: See [System Context](03-system-context.md) and [Building Blocks](05-building-blocks.md)
- **Key Design Decisions**: See [Architecture Decisions](09-architecture-decisions.md)
- **Integration Patterns**: See [Runtime View](06-runtime-view.md)

## Diagrams

This documentation uses [Mermaid](https://mermaid.js.org/) for all diagrams, which can be rendered in:

- GitHub markdown preview
- VS Code with Mermaid extension
- Documentation sites (GitBook, MkDocs, etc.)

## Contributing

When updating the architecture documentation:

1. Follow the arc42 template structure
2. Use Mermaid for all diagrams
3. Keep diagrams simple and focused
4. Update the glossary for new terms
5. Cross-reference related sections
6. Follow markdownlint rules (see `.markdownlint-cli2.jsonc` for CI config, `.markdownlint.json` for local checks)
