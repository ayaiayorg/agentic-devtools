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


@pytest.fixture(autouse=True)
def _mock_resolve_pr_body_legacy(request):
    """Mock resolve_pr_body so create_pull_request tests use state description.

    This preserves the existing test semantics where description comes from
    state. Only applies to tests that exercise create_pull_request.
    """
    skip_classes = ("TestCreatePullRequestActualCall", "TestCreatePullRequest")
    if not any(cls in request.node.nodeid for cls in skip_classes):
        yield
        return

    with patch("agentic_devtools.cli.pr_template.resolve_pr_body") as mock:

        def _from_state():
            return state.get_value("description") or ""

        mock.side_effect = _from_state
        yield mock
