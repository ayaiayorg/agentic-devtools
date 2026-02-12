# Markdown Linting Configuration Guide

This document explains the markdown linting setup for the agentic-devtools repository.

## Overview

We use `markdownlint-cli2` to ensure consistent markdown formatting across all documentation files.
The configuration resolves all 887 initial linting errors through a combination of:

- Adjusted rule defaults
- Directory-specific overrides
- Strategic rule disabling for special file types

## Configuration Files

### Root Configuration (`.markdownlint.json`)

Base rules applied to all markdown files:

```json
{
  "MD013": { "line_length": 200 },  // Reasonable limit for documentation
  "MD060": false,                     // Table formatting is auto-generated
  "MD036": false,                     // Emphasis-as-heading is acceptable
  "MD033": { "allowed_elements": [...] }  // Allow common HTML elements
}
```

### Agent Directories (`.github/agents/`, `.github/prompts/`)

AI agent files have special needs:

- Contain YAML front matter → disable MD041 (first-line-heading)
- Contain long instructional prompts → disable MD013 (line-length)

### Template Directories (`.specify/templates/commands/`, `.github/scripts/speckit-trigger/templates/`)

Template files also have special requirements:

- Contain YAML front matter → disable MD041
- Contain long template instructions → disable MD013

## Adding New Files

### Agent Files (`.agent.md`)

No special action needed - the `.github/agents/.markdownlint.json` config will apply automatically.

### Prompt Files (`.prompt.md`)

No special action needed - the `.github/prompts/.markdownlint.json` config will apply automatically.

### Template Files

Place in appropriate template directory where MD041 and MD013 are disabled.

### Regular Documentation

Follow these guidelines:

- Keep lines under 200 characters
- Add blank lines around lists, headings, and code blocks
- Specify language for code blocks (use `text` for plain text)
- Wrap bare URLs in backticks or use markdown links

## Running the Linter

### Locally

```bash
npx markdownlint-cli2 "**/*.md"
```

### Auto-fix

Many issues can be auto-fixed:

```bash
npx markdownlint-cli2 --fix "**/*.md"
```

### CI/CD

The linter runs automatically on all PRs via `.github/workflows/lint.yml`.

## Common Issues and Solutions

### MD041: First line should be H1

**Problem**: File starts with YAML front matter or H2
**Solution**: Add `.markdownlint.json` to the directory with `"MD041": false`

### MD013: Line too long

**Problem**: Line exceeds 200 characters
**Solutions**:

1. Break the line naturally at a clause or phrase boundary
2. If in a template/agent file, ensure MD013 is disabled for that directory

### MD040: Code block needs language

**Problem**: Code block has ` ``` ` without language specifier
**Solution**: Add appropriate language:

- ` ```bash ` for shell commands
- ` ```python ` for Python code
- ` ```text ` for plain text or examples
- ` ```json ` for JSON data

### MD031/MD032: Missing blank lines

**Problem**: Lists or code blocks not surrounded by blank lines
**Solution**: Run `npx markdownlint-cli2 --fix "**/*.md"` - this is auto-fixable

## Configuration Rationale

### Why 200 character line limit?

- 120 was too restrictive for documentation
- 200 allows natural sentence flow while preventing excessive line length
- Code blocks and tables are excluded from the limit

### Why disable MD013 for agents/templates?

These files contain AI prompts and instructions that:

- Often need to be continuous for clarity
- Are optimized for AI readability, not human line-length preferences
- Would be awkward if artificially broken

### Why disable MD041 for files with YAML front matter?

YAML front matter is a standard pattern for:

- GitHub Copilot agent definitions
- Jekyll/Hugo/static site generators
- Metadata in markdown files

The first "content" line after front matter may legitimately be H2 or other elements.

## Future Maintenance

When adding new markdown files:

1. Run the linter: `npx markdownlint-cli2 "path/to/new/file.md"`
2. For one-off exceptions, add an HTML comment: `<!-- markdownlint-disable MD### -->`
3. For directory patterns, create a `.markdownlint.json` in that directory
4. Document the reason for any exceptions in this file
