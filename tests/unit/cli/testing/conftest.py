"""Shared fixtures and constants for testing module tests."""

import pytest

# Shared error message used across workspace-root validation tests.
# Kept here to avoid embedding the same literal (including the /tmp path)
# in every test file that exercises the FileNotFoundError path.
WORKSPACE_ROOT_ERROR_MSG = (
    "pyproject.toml not found in current directory (/tmp). "
    "Run agdt-test commands from the workspace root."
)


@pytest.fixture()
def workspace_root_error_msg() -> str:
    """Return the standard workspace-root error message for test mocks."""
    return WORKSPACE_ROOT_ERROR_MSG
