"""Release command entry points."""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from typing import Optional

from agentic_devtools.background_tasks import run_function_in_background
from agentic_devtools.cli.release import helpers
from agentic_devtools.state import (
    get_pypi_dry_run,
    get_pypi_package_name,
    get_pypi_repository,
    get_pypi_version,
)
from agentic_devtools.task_state import (
    TaskStatus,
    get_task_by_id,
    print_task_tracking_info,
)


def _require_pypi_value(value: Optional[str], key: str, example: str) -> str:
    """Ensure required PyPI state value exists or exit."""
    if value:
        return value
    print(f"Error: pypi.{key} is required. Use: {example}", file=sys.stderr)
    sys.exit(1)


def release_pypi_async() -> None:
    """Run the PyPI release flow in a background task."""
    package_name = _require_pypi_value(
        get_pypi_package_name(), "package_name", "agdt-set pypi.package_name <name>"
    )
    version = _require_pypi_value(
        get_pypi_version(), "version", "agdt-set pypi.version <version>"
    )
    task = run_function_in_background(
        "agentic_devtools.cli.release.commands",
        "_release_pypi_sync",
        command_display_name="agdt-release-pypi",
    )
    print_task_tracking_info(task, f"Releasing {package_name} {version}")


def _run_tests_and_wait(timeout_seconds: int = 3600) -> int:
    """Run agdt-test in background and wait for completion."""
    task = run_function_in_background(
        "agentic_devtools.cli.testing",
        "_run_tests_sync",
        command_display_name="agdt-test",
    )
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        current = get_task_by_id(task.id)
        if current and current.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            return current.exit_code if current.exit_code is not None else 1
        time.sleep(2)
    raise helpers.ReleaseError("Test execution timed out.")


def _normalize_repository(value: Optional[str]) -> str:
    """Normalize repository setting and validate allowed values."""
    repo = (value or "pypi").lower()
    if repo not in {"pypi", "testpypi"}:
        raise helpers.ReleaseError(f"Unsupported repository: {value}")
    return repo


def _release_pypi_sync() -> None:
    """Sync implementation for the PyPI release flow."""
    package_name = _require_pypi_value(
        get_pypi_package_name(), "package_name", "agdt-set pypi.package_name <name>"
    )
    version = _require_pypi_value(
        get_pypi_version(), "version", "agdt-set pypi.version <version>"
    )
    repository = _normalize_repository(get_pypi_repository())
    dry_run = get_pypi_dry_run()

    start_time = datetime.now(timezone.utc)
    print(
        f"Starting PyPI release for {package_name} {version} (repo={repository}, dry_run={dry_run})"
    )

    if helpers.pypi_version_exists(package_name, version, repository=repository):
        raise helpers.ReleaseError(f"Version {version} already exists on {repository}")

    test_exit = _run_tests_and_wait()
    if test_exit != 0:
        raise helpers.ReleaseError("Test suite failed. Release aborted.")

    helpers.build_distribution("dist")
    helpers.validate_distribution("dist")

    if dry_run:
        publish_status = "skipped"
        print("Dry-run enabled. Skipping upload.")
    else:
        helpers.upload_distribution("dist", repository=repository)
        publish_status = "uploaded"

    end_time = datetime.now(timezone.utc)
    print("\nRelease summary")
    print(f"Package: {package_name}")
    print(f"Version: {version}")
    print("Test status: passed")
    print(f"Publish status: {publish_status}")
    print(f"Started: {start_time.isoformat()}")
    print(f"Finished: {end_time.isoformat()}")
