"""
Shared fixtures for tests/unit/cli/git/.
"""

import subprocess
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.git import core


@pytest.fixture
def mock_run_safe():
    """Mock core.run_safe for git commands."""
    with patch.object(core, "run_safe") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        yield mock_run


@pytest.fixture
def temp_git_repo(tmp_path) -> Generator:
    """Create a temporary git repository for testing git operations.

    Sets up a minimal git repo with an initial commit so that git
    commands can be exercised without touching the real repository.

    Yields:
        Path to the temporary git repository.
    """
    repo_dir = tmp_path / "test-repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    # Disable GPG signing so the fixture works even when commit.gpgsign=true
    # is set in the developer's or CI global Git config.
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    readme = repo_dir / "README.md"
    readme.write_text("# Test Repository\n")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "--no-verify", "-m", "Initial commit"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    yield repo_dir
