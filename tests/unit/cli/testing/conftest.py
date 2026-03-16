"""Shared fixtures and constants for testing module tests."""

# Message template for workspace-root validation errors.
# Does not include a specific path so it remains portable across
# platforms and test environments. Use make_workspace_root_error()
# to build the full message for a concrete path.
WORKSPACE_ROOT_ERROR_TEMPLATE = (
    "pyproject.toml not found in current directory ({cwd}). "
    "Run agdt-test commands from the workspace root."
)


def make_workspace_root_error(cwd: object) -> str:
    """Build the expected workspace-root error message for a given CWD.

    Args:
        cwd: The directory path (converted to str via format).

    Returns:
        The full error string as produced by get_workspace_root().
    """
    return WORKSPACE_ROOT_ERROR_TEMPLATE.format(cwd=cwd)
