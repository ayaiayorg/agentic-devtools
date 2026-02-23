"""Tests for PyPI release command behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agentic_devtools.cli.release import commands
from agentic_devtools.state import set_value
from agentic_devtools.task_state import TaskStatus


def _set_release_state(
    *,
    package: str = "agentic-devtools",
    version: str = "0.1.0",
    repository: str = "pypi",
) -> None:
    set_value("pypi.package_name", package)
    set_value("pypi.version", version)
    set_value("pypi.repository", repository)
    set_value("pypi.dry_run", False)


def test_release_aborts_on_test_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_release_state()

    monkeypatch.setattr(commands.helpers, "pypi_version_exists", Mock(return_value=False))
    monkeypatch.setattr(commands, "_run_tests_and_wait", Mock(return_value=1))

    with pytest.raises(commands.helpers.ReleaseError):
        commands._release_pypi_sync()


def test_release_summary_includes_package_and_version(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _set_release_state(package="agentic-devtools", version="1.2.3")

    monkeypatch.setattr(commands.helpers, "pypi_version_exists", Mock(return_value=False))
    monkeypatch.setattr(commands, "_run_tests_and_wait", Mock(return_value=0))
    monkeypatch.setattr(commands.helpers, "build_distribution", Mock())
    monkeypatch.setattr(commands.helpers, "validate_distribution", Mock())
    monkeypatch.setattr(commands.helpers, "upload_distribution", Mock())

    commands._release_pypi_sync()

    output = capsys.readouterr().out
    assert "Package: agentic-devtools" in output
    assert "Version: 1.2.3" in output


def test_release_aborts_when_version_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_release_state()

    monkeypatch.setattr(commands.helpers, "pypi_version_exists", Mock(return_value=True))

    with pytest.raises(commands.helpers.ReleaseError):
        commands._release_pypi_sync()


def test_release_dry_run_skips_upload(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _set_release_state()
    set_value("pypi.dry_run", True)

    monkeypatch.setattr(commands.helpers, "pypi_version_exists", Mock(return_value=False))
    monkeypatch.setattr(commands, "_run_tests_and_wait", Mock(return_value=0))
    monkeypatch.setattr(commands.helpers, "build_distribution", Mock())
    monkeypatch.setattr(commands.helpers, "validate_distribution", Mock())
    upload_mock = Mock()
    monkeypatch.setattr(commands.helpers, "upload_distribution", upload_mock)

    commands._release_pypi_sync()

    output = capsys.readouterr().out
    assert "Dry-run enabled" in output
    upload_mock.assert_not_called()


def test_require_pypi_value_raises_system_exit(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        commands._require_pypi_value(None, "package_name", "agdt-set pypi.package_name <name>")

    error = capsys.readouterr().err
    assert "pypi.package_name" in error


def test_normalize_repository_rejects_invalid() -> None:
    with pytest.raises(commands.helpers.ReleaseError):
        commands._normalize_repository("invalid")


def test_run_tests_and_wait_returns_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    task = SimpleNamespace(id="task-123")
    monkeypatch.setattr(commands, "run_function_in_background", Mock(return_value=task))
    monkeypatch.setattr(
        commands,
        "get_task_by_id",
        Mock(return_value=SimpleNamespace(status=TaskStatus.COMPLETED, exit_code=0)),
    )

    assert commands._run_tests_and_wait(timeout_seconds=1) == 0


def test_run_tests_and_wait_defaults_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    task = SimpleNamespace(id="task-999")
    monkeypatch.setattr(commands, "run_function_in_background", Mock(return_value=task))
    monkeypatch.setattr(
        commands,
        "get_task_by_id",
        Mock(return_value=SimpleNamespace(status=TaskStatus.COMPLETED, exit_code=None)),
    )

    assert commands._run_tests_and_wait(timeout_seconds=1) == 1


def test_run_tests_and_wait_sleeps_between_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = SimpleNamespace(id="task-sleep")
    monkeypatch.setattr(commands, "run_function_in_background", Mock(return_value=task))
    statuses = [None, SimpleNamespace(status=TaskStatus.COMPLETED, exit_code=0)]
    monkeypatch.setattr(commands, "get_task_by_id", Mock(side_effect=statuses))

    times = iter([0, 0, 1])
    monkeypatch.setattr(commands.time, "time", lambda: next(times))
    sleep_mock = Mock()
    monkeypatch.setattr(commands.time, "sleep", sleep_mock)

    assert commands._run_tests_and_wait(timeout_seconds=10) == 0
    sleep_mock.assert_called_once_with(2)


def test_run_tests_and_wait_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    task = SimpleNamespace(id="task-456")
    monkeypatch.setattr(commands, "run_function_in_background", Mock(return_value=task))
    monkeypatch.setattr(commands, "get_task_by_id", Mock(return_value=None))

    times = iter([0, 2])
    monkeypatch.setattr(commands.time, "time", lambda: next(times))
    monkeypatch.setattr(commands.time, "sleep", lambda _s: None)

    with pytest.raises(commands.helpers.ReleaseError):
        commands._run_tests_and_wait(timeout_seconds=1)


def test_release_pypi_async_starts_background_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(commands, "get_pypi_package_name", Mock(return_value="agentic-devtools"))
    monkeypatch.setattr(commands, "get_pypi_version", Mock(return_value="1.0.0"))
    task = SimpleNamespace(id="task-789")
    run_mock = Mock(return_value=task)
    print_mock = Mock()

    monkeypatch.setattr(commands, "run_function_in_background", run_mock)
    monkeypatch.setattr(commands, "print_task_tracking_info", print_mock)

    commands.release_pypi_async()

    run_mock.assert_called_once()
    print_mock.assert_called_once_with(task, "Releasing agentic-devtools 1.0.0")
