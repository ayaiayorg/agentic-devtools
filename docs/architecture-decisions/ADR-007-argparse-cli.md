# ADR-007: Argparse-Based CLI

**Status**: Accepted

**Context**: Need robust, auto-approvable CLI with good help text, simple parameter handling, and zero additional runtime dependencies

**Decision**: Use Python's built-in `argparse` module for all CLI commands,
dispatched through a single `run_as_script` entry point that routes to
per-command functions via a `COMMAND_MAP` lookup table

**Rationale**:

- No third-party dependency required (stdlib only)
- Argparse provides structured parsing, validation, and help generation
- Works well with many small, parameterless commands designed for AI auto-approval
- Easier to reason about and debug than a heavier framework
- Single entry point avoids redundant console_script wiring per command

**Consequences**:

- ✅ Consistent, explicit CLI behavior across all `agdt-*` commands
- ✅ Auto-generated `--help` output from argparse without extra libraries
- ✅ Simple integration with the background task system and state management
- ✅ Easier to vendor or run in constrained environments (no extra dependencies)
- ⚠️ More manual wiring needed for subcommands and shared options compared to
  a full-featured framework like Click

**Example**:

All `agdt-*` console scripts in `pyproject.toml` point to the same entry
point (`agentic_devtools.cli.runner:run_as_script`), which derives the
command name from `sys.argv[0]` and dispatches via `COMMAND_MAP`:

```python
# agentic_devtools/cli/runner.py (simplified)
COMMAND_MAP = {
    "agdt-set": ("agentic_devtools.cli.state", "set_cmd"),
    "agdt-add-pull-request-comment": (
        "agentic_devtools.cli.azure_devops",
        "add_pull_request_comment_async",
    ),
    # ... one entry per agdt-* command
}

def run_as_script() -> None:
    command = os.path.basename(sys.argv[0])
    module_name, func_name = COMMAND_MAP[command]
    module = importlib.import_module(module_name)
    func = getattr(module, func_name)
    func()
```

Each target function uses argparse internally for its own flags:

```python
def add_pull_request_comment_async():
    """CLI handler for adding PR comment."""
    parser = argparse.ArgumentParser(description='Add comment to pull request')
    parser.add_argument('--pull-request-id', type=int, help='PR ID')
    parser.add_argument('--content', help='Comment content')
    args = parser.parse_args()
    # ... implementation
```
