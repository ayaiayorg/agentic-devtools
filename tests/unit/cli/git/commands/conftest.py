"""Shared fixtures for tests/unit/cli/git/commands/."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.git import operations


@pytest.fixture(autouse=True)
def mock_get_current_branch():
    """Mock get_current_branch in operations to return 'main' by default.

    stage_changes() calls get_current_branch() for branch-aware filtering.
    Without this mock, the run_safe mock returns empty stdout which triggers
    sys.exit(1) in get_current_branch().  Tests that need a specific branch
    can override with their own patch.
    """
    with patch.object(operations, "get_current_branch", return_value="main"):
        yield


@pytest.fixture(autouse=True)
def mock_persist_commit_message(request):
    """Mock _persist_effective_commit_message to avoid extra run_safe calls.

    Skipped for tests that specifically test _persist_effective_commit_message.
    """
    if "test__persist_effective_commit_message" in request.node.nodeid:
        yield
        return
    with patch("agentic_devtools.cli.git.commands._persist_effective_commit_message") as mock:
        yield mock


@pytest.fixture
def mock_should_amend():
    """Mock should_amend_instead_of_commit to always return False (new commit)."""
    with patch("agentic_devtools.cli.git.commands.should_amend_instead_of_commit") as mock:
        mock.return_value = False
        yield mock


@pytest.fixture
def mock_sync_with_main():
    """Mock _sync_with_main to skip fetch/rebase for simpler testing."""
    with patch("agentic_devtools.cli.git.commands._sync_with_main") as mock:
        mock.return_value = False
        yield mock
