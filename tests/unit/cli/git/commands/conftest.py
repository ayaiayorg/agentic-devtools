"""Shared fixtures for tests/unit/cli/git/commands/."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.git import core


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


@pytest.fixture
def mock_run_safe():
    """Mock subprocess.run for git commands."""
    with patch.object(core, "run_safe") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        yield mock_run


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
