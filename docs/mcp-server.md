# AGDT MCP Server

The **agentic-devtools MCP server** exposes AGDT tool adapter functions over
the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/), allowing
any MCP-compatible AI coding agent to discover and call them.

## Overview

When running, the MCP server advertises tools for:

| Category | Tools |
|----------|-------|
| **Jira** | `jira_create_issue`, `jira_create_epic`, `jira_create_subtask`, `jira_add_comment`, `jira_fetch_issue_context` |
| **Git** | `git_stage_changes`, `git_create_commit`, `git_amend_commit`, `git_push`, `git_force_push`, `git_publish_branch`, `git_save_work`, `git_get_recent_changes` |
| **Azure DevOps** | `azure_devops_create_pull_request`, `azure_devops_reply_to_thread`, `azure_devops_add_comment`, `azure_devops_update_review_narrative` |

Each tool maps directly to a stateless function in
`agentic_devtools/tools/` and returns structured JSON results.

## Prerequisites

- Python ≥ 3.10
- `agentic-devtools` installed (`pip install -e .` from the repo root)
- The `mcp` package (automatically installed as a dependency)

## Environment Variables

Configure the platforms you need before starting the server.
Missing variables produce a startup warning — the server still starts, but
tools for that platform return an error message when called.

### Jira

| Variable | Required | Description |
|----------|----------|-------------|
| `JIRA_BASE_URL` | Yes | Jira instance URL (e.g. `https://jira.example.com`) |
| `JIRA_API_TOKEN` | Yes | API token or PAT (falls back to `JIRA_COPILOT_PAT`) |
| `JIRA_USER_EMAIL` | No | When set, Basic auth is used instead of Bearer (falls back to `JIRA_EMAIL`, `JIRA_USERNAME`) |
| `JIRA_AUTH_SCHEME` | No | `basic` or `bearer` (default). When `basic`, an identity variable must also be set. |
| `JIRA_SSL_VERIFY` | No | `0` or `false` to disable SSL verification; path to CA bundle; default `true` |

### Azure DevOps

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_DEVOPS_ORG` | Yes | Organization URL (e.g. `https://dev.azure.com/myorg`) |
| `AZURE_DEVOPS_PROJECT` | Yes | Project name |
| `AZURE_DEVOPS_PAT` | Yes | Personal Access Token (falls back to `AZURE_DEV_OPS_COPILOT_PAT`, then `AZURE_DEVOPS_EXT_PAT`) |
| `AZURE_DEVOPS_REPOSITORY` | No* | Repository name (auto-detected from git remote if not set) |

> \*When `AZURE_DEVOPS_REPOSITORY` is not set, the MCP server attempts to
> infer the repository name from the current git remote (typically `origin`).
> If auto-detection fails (e.g. running outside a git repo or when the remote
> URL cannot be parsed), Azure DevOps tools will be treated as not configured.
> If the git remote points to a non-Azure DevOps host (for example GitHub),
> a repository name may still be inferred but Azure DevOps operations will
> typically fail at call time; in such cases, or in non-git contexts, set
> `AZURE_DEVOPS_REPOSITORY` explicitly to the Azure DevOps repository name.

### Git

Git tools operate on the local repository — no environment variables required.

## Starting the Server

```bash
agdt-mcp-server
```

The server communicates over **stdio** (stdin/stdout), which is the standard
MCP transport for local tool servers.

## Client Configuration

### Claude Desktop

Add to `claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "agentic-devtools": {
      "command": "agdt-mcp-server",
      "env": {
        "JIRA_BASE_URL": "https://jira.example.com",
        "JIRA_API_TOKEN": "your-token",
        "AZURE_DEVOPS_ORG": "https://dev.azure.com/yourorg",
        "AZURE_DEVOPS_PROJECT": "YourProject",
        "AZURE_DEVOPS_PAT": "your-pat"
      }
    }
  }
}
```

### VS Code (Copilot Chat)

Add to your VS Code `settings.json`:

```json
{
  "mcp": {
    "servers": {
      "agentic-devtools": {
        "command": "agdt-mcp-server",
        "env": {
          "JIRA_BASE_URL": "https://jira.example.com",
          "JIRA_API_TOKEN": "your-token",
          "AZURE_DEVOPS_ORG": "https://dev.azure.com/yourorg",
          "AZURE_DEVOPS_PROJECT": "YourProject",
          "AZURE_DEVOPS_PAT": "your-pat"
        }
      }
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "agentic-devtools": {
      "command": "agdt-mcp-server",
      "env": {
        "JIRA_BASE_URL": "https://jira.example.com",
        "JIRA_API_TOKEN": "your-token",
        "AZURE_DEVOPS_ORG": "https://dev.azure.com/yourorg",
        "AZURE_DEVOPS_PROJECT": "YourProject",
        "AZURE_DEVOPS_PAT": "your-pat"
      }
    }
  }
}
```

## Example Tool Call

An MCP client sends a `tools/call` request:

```json
{
  "method": "tools/call",
  "params": {
    "name": "jira_fetch_issue_context",
    "arguments": {
      "issue_key": "DFLY-1234"
    }
  }
}
```

Response:

```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"issue\": {...}, \"parent_issue\": null, \"epic_issue\": null, \"remote_links\": []}"
    }
  ]
}
```

## Troubleshooting

### Server won't start

- Ensure `agentic-devtools` is installed: `pip install -e .`
- Check that `agdt-mcp-server` is on your PATH
- Run `agdt-mcp-server` directly in a terminal to see startup errors

### Tools return "not configured" errors

- Verify environment variables are set correctly
- For Jira: both `JIRA_BASE_URL` and `JIRA_API_TOKEN` are required
- For Azure DevOps: `ORG`, `PROJECT`, and `PAT` are required, and the server must be able
  to determine the repository (either set `AZURE_DEVOPS_REPOSITORY` explicitly or run inside
  a git repo with an Azure DevOps remote so it can be auto-detected)
- Git tools require no configuration

### SSL certificate errors (Jira)

- Set `JIRA_SSL_VERIFY=0` to disable verification (development only)
- Or set `JIRA_SSL_VERIFY=/path/to/ca-bundle.pem` for custom CA certificates
