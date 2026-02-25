"""
Shared fixtures for tests/unit/cli/git/.
"""

from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.git import core
from tests.helpers import create_git_repo


@pytest.fixture
def mock_run_safe():
    """Mock core.run_safe for git commands."""
    with patch.object(core, "run_safe") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        yield mock_run


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary git repository for testing git operations.

    Sets up a minimal git repo with an initial commit so that git
    commands can be exercised without touching the real repository.

    Yields:
        Path to the temporary git repository.
    """
    repo_dir = tmp_path / "test-repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    create_git_repo(repo_dir)
    yield repo_dir
