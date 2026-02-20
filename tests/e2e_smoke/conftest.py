"""
Pytest configuration for E2E smoke tests.

This module provides fixtures and configuration for end-to-end smoke tests
that validate CLI commands with mocked HTTP interactions.
"""

from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest


@pytest.fixture
def temp_state_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Create a temporary directory for state files during E2E tests.

    This fixture patches the state directory to isolate test state
    from the actual application state.

    Args:
        tmp_path: pytest's temporary directory fixture

    Yields:
        Path to the temporary state directory
    """
    from agentic_devtools import state

    # Ensure the temp directory exists
    tmp_path.mkdir(parents=True, exist_ok=True)

    # Patch get_state_dir in all relevant modules
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        # Also patch it in the jira module
        try:
            from agentic_devtools.cli import jira

            with patch("agentic_devtools.cli.jira.get_commands.get_state_dir", return_value=tmp_path):
                yield tmp_path
        except ImportError:
            yield tmp_path


@pytest.fixture
def clean_state(temp_state_dir: Path) -> None:
    """
    Clear state before each E2E test.

    Ensures tests start with a clean state to avoid cross-test pollution.

    Args:
        temp_state_dir: Temporary state directory fixture
    """
    from agentic_devtools.state import clear_state

    clear_state()


@pytest.fixture
def mock_jira_env() -> Generator[None, None, None]:
    """
    Set up mock environment variables for Jira authentication.

    Provides test credentials without exposing real tokens.

    Yields:
        None
    """
    with patch.dict(
        "os.environ",
        {
            "JIRA_COPILOT_PAT": "test-jira-token-redacted",
            "JIRA_BASE_URL": "https://test.atlassian.net",
        },
    ):
        yield


@pytest.fixture
def mock_azure_devops_env() -> Generator[None, None, None]:
    """
    Set up mock environment variables for Azure DevOps authentication.

    Provides test credentials without exposing real tokens.

    Yields:
        None
    """
    with patch.dict(
        "os.environ",
        {
            "AZURE_DEV_OPS_COPILOT_PAT": "test-azure-pat-redacted",
            "AZURE_DEVOPS_ORG": "test-org",
            "AZURE_DEVOPS_PROJECT": "test-project",
            "AZURE_DEVOPS_REPO": "test-repo",
        },
    ):
        yield


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Create a temporary git repository for testing git commands.

    Sets up a minimal git repo with initial commit for testing
    git workflow commands.

    Args:
        tmp_path: pytest's temporary directory fixture

    Yields:
        Path to the temporary git repository
    """
    import subprocess

    repo_dir = tmp_path / "test-repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Initialize git repo
    subprocess.run(
        ["git", "init"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    # Configure git user
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

    # Create initial commit
    test_file = repo_dir / "README.md"
    test_file.write_text("# Test Repository\n")
    subprocess.run(
        ["git", "add", "."],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    yield repo_dir
