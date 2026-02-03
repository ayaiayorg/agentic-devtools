"""Integration-style tests for PyPI release flow."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from agentic_devtools.cli.release import commands
from agentic_devtools.state import set_value


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


def test_release_flow_runs_build_and_upload(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_release_state()

    monkeypatch.setattr(
        commands.helpers, "pypi_version_exists", Mock(return_value=False)
    )
    monkeypatch.setattr(commands, "_run_tests_and_wait", Mock(return_value=0))
    build_mock = Mock()
    validate_mock = Mock()
    upload_mock = Mock()
    monkeypatch.setattr(commands.helpers, "build_distribution", build_mock)
    monkeypatch.setattr(commands.helpers, "validate_distribution", validate_mock)
    monkeypatch.setattr(commands.helpers, "upload_distribution", upload_mock)

    commands._release_pypi_sync()

    build_mock.assert_called_once()
    validate_mock.assert_called_once()
    upload_mock.assert_called_once()


def test_release_flow_skips_upload_on_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_release_state()
    set_value("pypi.dry_run", True)

    monkeypatch.setattr(
        commands.helpers, "pypi_version_exists", Mock(return_value=False)
    )
    monkeypatch.setattr(commands, "_run_tests_and_wait", Mock(return_value=0))
    monkeypatch.setattr(commands.helpers, "build_distribution", Mock())
    monkeypatch.setattr(commands.helpers, "validate_distribution", Mock())
    upload_mock = Mock()
    monkeypatch.setattr(commands.helpers, "upload_distribution", upload_mock)

    commands._release_pypi_sync()

    upload_mock.assert_not_called()


def test_release_blocks_upload_on_test_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_release_state()

    monkeypatch.setattr(
        commands.helpers, "pypi_version_exists", Mock(return_value=False)
    )
    monkeypatch.setattr(commands, "_run_tests_and_wait", Mock(return_value=1))
    monkeypatch.setattr(commands.helpers, "build_distribution", Mock())
    monkeypatch.setattr(commands.helpers, "validate_distribution", Mock())
    upload_mock = Mock()
    monkeypatch.setattr(commands.helpers, "upload_distribution", upload_mock)

    with pytest.raises(commands.helpers.ReleaseError):
        commands._release_pypi_sync()

    upload_mock.assert_not_called()


def test_release_summary_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _set_release_state()

    monkeypatch.setattr(
        commands.helpers, "pypi_version_exists", Mock(return_value=False)
    )
    monkeypatch.setattr(commands, "_run_tests_and_wait", Mock(return_value=0))
    monkeypatch.setattr(commands.helpers, "build_distribution", Mock())
    monkeypatch.setattr(commands.helpers, "validate_distribution", Mock())
    monkeypatch.setattr(commands.helpers, "upload_distribution", Mock())

    commands._release_pypi_sync()

    output = capsys.readouterr().out
    assert "Release summary" in output
