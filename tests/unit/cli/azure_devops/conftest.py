"""
Shared fixtures for Azure DevOps tests.
"""

from unittest.mock import patch

import pytest


@pytest.fixture
def mock_azure_devops_env():
    """Set up environment variables for Azure DevOps API calls."""
    with patch.dict(
        "os.environ",
        {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"},
    ):
        yield


@pytest.fixture(autouse=True)
def mock_git_remote_detection(request, monkeypatch):
    """
    Auto-mock git remote detection for all Azure DevOps tests except
    tests in TestRepositoryDetection / TestGetAzureDevOpsContextFromGitRemote
    classes which specifically test those functions.

    This prevents the git remote detection from interfering with test mocks
    by making it always return None (which causes fallback to defaults).
    """
    # Skip this fixture for tests that specifically test git remote detection
    skip_classes = ("TestRepositoryDetection", "TestGetAzureDevOpsContextFromGitRemote")
    if any(cls in request.node.nodeid for cls in skip_classes):
        yield
        return

    from agentic_devtools.cli.azure_devops import config

    monkeypatch.setattr(config, "get_repository_name_from_git_remote", lambda: None)
    monkeypatch.setattr(config, "get_azure_devops_context_from_git_remote", lambda: None)
    yield
