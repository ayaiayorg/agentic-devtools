"""
Base workflow functions and utilities.

This module provides common functionality for all workflow commands:
- State validation
- Workflow initiation pattern
- Variable collection from state
- State clearing for fresh workflow starts
"""

import sys
from typing import Any, Dict, List, Optional

from ...prompts import TemplateValidationError, load_and_render_prompt
from ...state import clear_state, get_value, set_workflow_state


def clear_state_for_workflow_initiation() -> None:
    """
    Clear all state to ensure a fresh start for workflow initiation.

    This prevents leftover state from previous sessions (like pull_request_id,
    source_branch, worktree_setup) from interfering with new workflow runs.

    Should be called at the very beginning of each workflow initiation command,
    BEFORE parsing CLI arguments or accessing state.
    """
    clear_state()
    print("✓ Cleared previous workflow state")


def validate_required_state(required_keys: List[str]) -> Dict[str, Any]:
    """
    Validate that required state keys exist and return their values.

    Args:
        required_keys: List of state keys that must be present

    Returns:
        Dictionary mapping key names to their values

    Raises:
        SystemExit: If any required key is missing
    """
    values = {}
    missing = []

    for key in required_keys:
        value = get_value(key)
        if value is None:
            missing.append(key)
        else:
            values[key] = value

    if missing:
        print(f"ERROR: Missing required state keys: {', '.join(missing)}", file=sys.stderr)
        print("\nPlease set them using:", file=sys.stderr)
        for key in missing:
            print(f"  agdt-set {key} <value>", file=sys.stderr)
        sys.exit(1)

    return values


def collect_variables_from_state(variable_keys: List[str]) -> Dict[str, Any]:
    """
    Collect variable values from state.

    This collects values for variables that exist in state, but doesn't
    require them to exist. Use validate_required_state for required keys.

    Args:
        variable_keys: List of state keys to collect

    Returns:
        Dictionary mapping variable names to their values (only includes keys that exist)
    """
    variables = {}
    for key in variable_keys:
        value = get_value(key)
        if value is not None:
            # Convert dotted keys to underscore format for template variables
            # e.g., "jira.issue_key" -> "jira_issue_key"
            var_name = _state_key_to_variable_name(key)
            variables[var_name] = value
    return variables


def _state_key_to_variable_name(state_key: str) -> str:
    """
    Convert a state key to a template variable name.

    State keys may use dot notation (e.g., "jira.issue_key") which is converted
    to underscore format for template variables.

    Examples:
        "pull_request_id" -> "pull_request_id"
        "jira.issue_key" -> "jira_issue_key"
        "jira.comment" -> "jira_comment"

    Args:
        state_key: State key with underscores and/or dots

    Returns:
        Variable name with dots replaced by underscores
    """
    # Simply replace dots with underscores - the templates use underscore format
    return state_key.replace(".", "_")


def initiate_workflow(
    workflow_name: str,
    required_state_keys: Optional[List[str]] = None,
    optional_state_keys: Optional[List[str]] = None,
    additional_variables: Optional[Dict[str, Any]] = None,
    step_name: str = "initiate",
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Common workflow initiation logic.

    This function:
    1. Validates required state keys exist
    2. Collects variables from state
    3. Updates workflow state
    4. Loads and renders the prompt template
    5. Saves to temp and logs to console

    Args:
        workflow_name: Name of the workflow (e.g., "pull-request-review")
        required_state_keys: State keys that must exist
        optional_state_keys: State keys to include if they exist
        additional_variables: Extra variables to include (not from state)
        step_name: Name of the step (default "initiate")
        context: Workflow context to store in state

    Returns:
        The generated prompt content

    Raises:
        SystemExit: If required state keys are missing
        FileNotFoundError: If no template exists
        TemplateValidationError: If override template is invalid
    """
    # Validate required state
    required_values = {}
    if required_state_keys:
        required_values = validate_required_state(required_state_keys)

    # Collect all variables
    all_state_keys = (required_state_keys or []) + (optional_state_keys or [])
    variables = collect_variables_from_state(all_state_keys)

    # Add any additional variables
    if additional_variables:
        variables.update(additional_variables)

    # Build context from required values if not provided
    if context is None:
        context = {}
        for key, value in required_values.items():
            context[_state_key_to_variable_name(key)] = value

    # Update workflow state
    set_workflow_state(
        name=workflow_name,
        status="initiated",
        step=step_name,
        context=context,
    )

    # Load and render prompt
    try:
        content = load_and_render_prompt(
            workflow_name=workflow_name,
            step_name=step_name,
            variables=variables,
            save_to_temp=True,
            log_output=True,
        )
        return content
    except TemplateValidationError as e:  # pragma: no cover
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:  # pragma: no cover
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def advance_workflow_step(
    workflow_name: str,
    step_name: str,
    variables: Optional[Dict[str, Any]] = None,
    status: str = "in-progress",
) -> str:
    """
    Advance to a new step in an active workflow.

    Args:
        workflow_name: Name of the workflow
        step_name: Name of the new step
        variables: Variables for the step template
        status: New workflow status

    Returns:
        The generated prompt content
    """
    from ...state import get_workflow_state, is_workflow_active

    # Verify workflow is active
    if not is_workflow_active(workflow_name):
        print(f"ERROR: Workflow '{workflow_name}' is not active.", file=sys.stderr)
        print(f"Start it first with: agdt-initiate-{workflow_name}-workflow", file=sys.stderr)
        sys.exit(1)

    # Get existing context
    workflow = get_workflow_state()
    context = workflow.get("context", {}) if workflow else {}

    # Update workflow state
    set_workflow_state(
        name=workflow_name,
        status=status,
        step=step_name,
        context=context,
    )

    # Load and render prompt
    try:
        content = load_and_render_prompt(
            workflow_name=workflow_name,
            step_name=step_name,
            variables=variables or {},
            save_to_temp=True,
            log_output=True,
        )
        return content
    except (TemplateValidationError, FileNotFoundError) as e:  # pragma: no cover
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
