"""
Shared fixtures for Azure DevOps tests.
"""

from unittest.mock import patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state.clear_state()
    yield


@pytest.fixture(autouse=True)
def mock_git_remote_detection(request, monkeypatch):
    """
    Auto-mock git remote detection for all Azure DevOps tests except
    tests in TestRepositoryDetection class which specifically test that function.

    This prevents the git remote detection from interfering with test mocks
    by making it always return None (which causes fallback to DEFAULT_REPOSITORY).
    """
    # Skip this fixture for tests in TestRepositoryDetection class
    if "TestRepositoryDetection" in request.node.nodeid:
        yield
        return

    from agentic_devtools.cli.azure_devops import config

    monkeypatch.setattr(config, "get_repository_name_from_git_remote", lambda: None)
    yield
