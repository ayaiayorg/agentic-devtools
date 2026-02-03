"""Tests for PyPI release helper utilities."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agentic_devtools.cli.release import helpers


class TestNormalizePackageName:
    def test_normalizes_pep503(self) -> None:
        assert helpers.normalize_package_name("My_Package.Name") == "my-package-name"


class TestPypiVersionExists:
    def test_returns_true_on_200(self, monkeypatch: pytest.MonkeyPatch) -> None:
        response = SimpleNamespace(status_code=200)
        get_mock = Mock(return_value=response)
        monkeypatch.setattr(
            helpers, "_get_requests", lambda: SimpleNamespace(get=get_mock)
        )

        assert helpers.pypi_version_exists("My_Package", "1.0.0") is True
        get_mock.assert_called_once()
        called_url = get_mock.call_args[0][0]
        assert called_url.endswith("/my-package/1.0.0/json")

    def test_returns_false_on_404(self, monkeypatch: pytest.MonkeyPatch) -> None:
        response = SimpleNamespace(status_code=404)
        get_mock = Mock(return_value=response)
        monkeypatch.setattr(
            helpers, "_get_requests", lambda: SimpleNamespace(get=get_mock)
        )

        assert helpers.pypi_version_exists("my-package", "1.0.0") is False

    def test_raises_on_error_status(self, monkeypatch: pytest.MonkeyPatch) -> None:
        response = SimpleNamespace(status_code=500)
        get_mock = Mock(return_value=response)
        monkeypatch.setattr(
            helpers, "_get_requests", lambda: SimpleNamespace(get=get_mock)
        )

        with pytest.raises(helpers.ReleaseError):
            helpers.pypi_version_exists("my-package", "1.0.0")

    def test_raises_on_request_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*_args, **_kwargs):
            raise RuntimeError("network down")

        monkeypatch.setattr(
            helpers, "_get_requests", lambda: SimpleNamespace(get=_raise)
        )

        with pytest.raises(helpers.ReleaseError):
            helpers.pypi_version_exists("my-package", "1.0.0")


class TestBuildValidateUpload:
    def test_build_distribution_runs_build(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        completed = subprocess.CompletedProcess(
            args=["python"], returncode=0, stdout="", stderr=""
        )
        run_mock = Mock(return_value=completed)
        monkeypatch.setattr(helpers, "run_safe", run_mock)

        helpers.build_distribution("dist")

        run_mock.assert_called_once()
        assert run_mock.call_args[0][0][:3] == ["python", "-m", "build"]

    def test_validate_distribution_runs_twine_check(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        completed = subprocess.CompletedProcess(
            args=["python"], returncode=0, stdout="", stderr=""
        )
        run_mock = Mock(return_value=completed)
        monkeypatch.setattr(helpers, "run_safe", run_mock)

        helpers.validate_distribution("dist")

        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        assert args[:3] == ["python", "-m", "twine"]
        assert "check" in args

    def test_upload_distribution_runs_twine_upload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        completed = subprocess.CompletedProcess(
            args=["python"], returncode=0, stdout="", stderr=""
        )
        run_mock = Mock(return_value=completed)
        monkeypatch.setattr(helpers, "run_safe", run_mock)

        helpers.upload_distribution("dist", repository="testpypi")

        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        assert args[:3] == ["python", "-m", "twine"]
        assert "upload" in args
        assert "--repository" in args
