"""Shared test utilities for agentic_devtools tests.

This module provides reusable factory functions and helper utilities
for common test operations, reducing duplication across test modules.

Usage example::

    from tests.helpers import create_git_repo, make_mock_popen, make_mock_response, make_mock_task

    def test_something(tmp_path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        create_git_repo(repo_dir)

        mock_process = make_mock_popen(pid=99)
        assert mock_process.pid == 99
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock


def create_git_repo(repo_dir: Path) -> None:
    """Set up a minimal git repository with an initial commit.

    Configures a git user, disables GPG signing so commits work even
    when ``commit.gpgsign=true`` is set globally, and makes a single
    initial commit with a README file.

    Args:
        repo_dir: Path to an existing directory in which to initialise
            the repository.
    """
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
    # Disable GPG signing so commits work even when commit.gpgsign=true
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


def make_mock_popen(pid: int = 12345) -> MagicMock:
    """Create a mock ``subprocess.Popen`` object with a fixed PID.

    Args:
        pid: Process ID to assign to the mock process (default: ``12345``).

    Returns:
        A ``MagicMock`` whose ``.pid`` attribute equals *pid*.
    """
    mock_process = MagicMock()
    mock_process.pid = pid
    return mock_process


def make_mock_response(
    json_data: dict | None = None,
    status_code: int = 200,
) -> MagicMock:
    """Create a mock HTTP response object.

    The returned mock is pre-configured so that:
    - ``.json()`` returns *json_data* (or a default Jira-like payload).
    - ``.status_code`` equals *status_code*.
    - ``.raise_for_status()`` is a no-op (does not raise).

    Args:
        json_data: Mapping returned by ``.json()``.  Defaults to
            ``{"key": "DFLY-9999", "id": "12345"}``.
        status_code: HTTP status code (default: ``200``).

    Returns:
        A ``MagicMock`` configured as a successful HTTP response.
    """
    if json_data is None:
        json_data = {"key": "DFLY-9999", "id": "12345"}
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data
    mock_response.raise_for_status = MagicMock()
    return mock_response


def make_mock_task(
    task_id: str = "test-task-id",
    command: str = "test-command",
) -> MagicMock:
    """Create a mock ``BackgroundTask`` object.

    Args:
        task_id: Unique task identifier (default: ``"test-task-id"``).
        command: Command display name (default: ``"test-command"``).

    Returns:
        A ``MagicMock`` with ``.id`` and ``.command`` attributes set.
    """
    mock_task = MagicMock()
    mock_task.id = task_id
    mock_task.command = command
    return mock_task
