"""
Shared fixtures for Azure DevOps tests.
"""

import pytest


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
