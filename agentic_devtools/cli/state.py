"""
Generic state management CLI commands.

These commands provide a universal interface for setting/getting state values.
Once auto-approved, they work for any key-value pair.

Key insight: Python CLI handles special characters and multiline content
natively, so we don't need replacement tokens or line-by-line builders!
"""

import json
import sys

from ..state import (
    CONTEXT_SWITCH_KEYS,
    clear_state,
    delete_value,
    get_value,
    load_state,
    set_context_value,
    set_value,
)


def set_cmd() -> None:
    """
    Set a state value: agdt-set <key> <value>

    Supports:
    - Simple strings: agdt-set pull_request_id 23046
    - Special characters: agdt-set content "Text with (parens) and [brackets]"
    - Multiline content: agdt-set content "Line 1
      Line 2
      Line 3"
    - JSON for complex types: agdt-set config '{"key": "value"}'
    - Stdin input: echo "content" | agdt-set content -

    Context-switching keys (pull_request_id, jira.issue_key):
        When these are set to a NEW value, the temp folder is cleared
        to provide a fresh context. If set to the same value, no clearing occurs.
        Cross-lookup is triggered to find related context values.

    Examples:
        agdt-set pull_request_id 23046
        agdt-set thread_id 139474
        agdt-set dry_run true
        agdt-set content "Thanks for the feedback!

        I've made the changes you suggested."
    """
    if len(sys.argv) < 3:
        print("Usage: agdt-set <key> <value>", file=sys.stderr)
        print("       agdt-set <key> -  (read value from stdin)", file=sys.stderr)
        sys.exit(1)

    key = sys.argv[1]

    # Handle stdin input
    if sys.argv[2] == "-":
        value = sys.stdin.read()
    else:
        # Join remaining args as the value (allows spaces without quotes in some cases)
        value = " ".join(sys.argv[2:])

    # Try to parse as JSON for complex types (booleans, numbers, arrays, objects)
    try:
        parsed = json.loads(value)
        final_value = parsed
    except json.JSONDecodeError:
        # Store as string
        final_value = value

    # For context-switching keys, use set_context_value to trigger clearing + cross-lookup
    if key in CONTEXT_SWITCH_KEYS:
        changed = set_context_value(key, final_value, verbose=True, trigger_cross_lookup=True)
        if changed:
            print(f"Set {key} (context switched)")
        else:
            print(f"Set {key}")
    else:
        set_value(key, final_value)
        print(f"Set {key}")


def get_cmd() -> None:
    """
    Get a state value: agdt-get <key>

    Examples:
        agdt-get pull_request_id
        agdt-get content
    """
    if len(sys.argv) < 2:
        print("Usage: agdt-get <key>", file=sys.stderr)
        sys.exit(1)

    key = sys.argv[1]
    value = get_value(key)

    if value is None:
        print(f"Key not found: {key}", file=sys.stderr)
        sys.exit(1)

    # Pretty print JSON for complex types
    if isinstance(value, (dict, list)):
        print(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        print(value)


def delete_cmd() -> None:
    """
    Delete a state value: agdt-delete <key>
    """
    if len(sys.argv) < 2:
        print("Usage: agdt-delete <key>", file=sys.stderr)
        sys.exit(1)

    key = sys.argv[1]
    if delete_value(key):
        print(f"Deleted {key}")
    else:
        print(f"Key not found: {key}", file=sys.stderr)


def clear_cmd() -> None:
    """
    Clear all state: agdt-clear
    """
    clear_state()
    print("State cleared")


def show_cmd() -> None:
    """
    Show all state: agdt-show
    """
    state = load_state()
    if not state:
        print("(empty state)")
    else:
        print(json.dumps(state, indent=2, ensure_ascii=False))


def get_workflow_cmd() -> None:
    """
    Show current workflow state: agdt-get-workflow

    Displays the active workflow, status, step, started time, and context.
    """
    from ..state import get_workflow_state

    workflow = get_workflow_state()
    if workflow is None:
        print("No workflow is currently active.")
    else:
        print(json.dumps(workflow, indent=2, ensure_ascii=False))


def clear_workflow_cmd() -> None:
    """
    Clear workflow state: agdt-clear-workflow

    Ends the current workflow by clearing its state.
    """
    from ..state import clear_workflow_state, get_workflow_state

    workflow = get_workflow_state()
    if workflow is None:
        print("No workflow is currently active.")
    else:
        workflow_name = workflow.get("active", "unknown")
        clear_workflow_state()
        print(f"Workflow '{workflow_name}' cleared.")
