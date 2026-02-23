"""Shared fixtures for tests/unit/cli/git/commands/."""

from unittest.mock import patch

import pytest


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
