"""Tests for ``check_version_guard`` in ``version_guard``."""

from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_devtools.cli.setup.version_guard import check_version_guard


class TestCheckVersionGuard:
    """Tests for the version guard orchestration function."""

    def test_returns_none_when_git_root_is_none(self) -> None:
        assert check_version_guard(None, force_old_version=False) is None

    def test_returns_none_when_no_project_json(self, tmp_path: Path) -> None:
        """FR-010: no project.json → proceed normally."""
        with patch("agentic_devtools.cli.config.project_config.load_project_config", return_value={}):
            assert check_version_guard(tmp_path, force_old_version=False) is None

    def test_returns_none_when_no_agdt_version_key(self, tmp_path: Path) -> None:
        """FR-010: no agdt_version key → proceed normally."""
        with patch(
            "agentic_devtools.cli.config.project_config.load_project_config",
            return_value={"some_other_key": "value"},
        ):
            assert check_version_guard(tmp_path, force_old_version=False) is None

    def test_returns_none_on_malformed_empty_version(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """FR-011: empty agdt_version → warning + proceed normally."""
        with patch(
            "agentic_devtools.cli.config.project_config.load_project_config",
            return_value={"agdt_version": ""},
        ):
            result = check_version_guard(tmp_path, force_old_version=False)
        assert result is None
        assert "Malformed" in capsys.readouterr().err

    def test_returns_none_on_malformed_garbage_version(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """FR-011: garbage agdt_version → warning + proceed normally."""
        with patch(
            "agentic_devtools.cli.config.project_config.load_project_config",
            return_value={"agdt_version": "not-a-version!!!"},
        ):
            result = check_version_guard(tmp_path, force_old_version=False)
        assert result is None
        assert "Malformed" in capsys.readouterr().err

    def test_returns_none_on_equal_version(self, tmp_path: Path) -> None:
        with (
            patch(
                "agentic_devtools.cli.config.project_config.load_project_config",
                return_value={"agdt_version": "0.2.69"},
            ),
            patch("agentic_devtools.__version__", "0.2.69"),
        ):
            assert check_version_guard(tmp_path, force_old_version=False) is None

    def test_returns_none_on_newer_version(self, tmp_path: Path) -> None:
        with (
            patch(
                "agentic_devtools.cli.config.project_config.load_project_config",
                return_value={"agdt_version": "0.2.69"},
            ),
            patch("agentic_devtools.__version__", "0.2.70"),
        ):
            assert check_version_guard(tmp_path, force_old_version=False) is None

    def test_returns_block_on_older_no_force(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """FR-005: older version + no force → block."""
        with (
            patch(
                "agentic_devtools.cli.config.project_config.load_project_config",
                return_value={"agdt_version": "0.2.69"},
            ),
            patch("agentic_devtools.__version__", "0.2.64"),
        ):
            result = check_version_guard(tmp_path, force_old_version=False)
        assert result == "block"
        err = capsys.readouterr().err
        assert "0.2.64" in err
        assert "0.2.69" in err
        assert "setup-dev-tools.py" in err
        assert "--force-old-version" in err

    def test_returns_force_on_older_with_force(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """FR-009: older version + force → warn + return 'force'."""
        with (
            patch(
                "agentic_devtools.cli.config.project_config.load_project_config",
                return_value={"agdt_version": "0.2.69"},
            ),
            patch("agentic_devtools.__version__", "0.2.64"),
        ):
            result = check_version_guard(tmp_path, force_old_version=True)
        assert result == "force"
        err = capsys.readouterr().err
        assert "not recommended" in err
        assert "repo files will NOT be modified" in err

    def test_force_with_equal_version_is_noop(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """US3/AS4: --force-old-version + equal version → None silently."""
        with (
            patch(
                "agentic_devtools.cli.config.project_config.load_project_config",
                return_value={"agdt_version": "0.2.69"},
            ),
            patch("agentic_devtools.__version__", "0.2.69"),
        ):
            result = check_version_guard(tmp_path, force_old_version=True)
        assert result is None
        assert capsys.readouterr().err == ""

    def test_force_with_newer_version_is_noop(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """US3/AS4: --force-old-version + newer version → None silently."""
        with (
            patch(
                "agentic_devtools.cli.config.project_config.load_project_config",
                return_value={"agdt_version": "0.2.69"},
            ),
            patch("agentic_devtools.__version__", "0.2.70"),
        ):
            result = check_version_guard(tmp_path, force_old_version=True)
        assert result is None
        assert capsys.readouterr().err == ""

    def test_proceeds_when_packaging_unavailable(self, tmp_path: Path) -> None:
        """When packaging is not installed, pinned version validation is skipped and comparison proceeds."""
        with (
            patch(
                "agentic_devtools.cli.config.project_config.load_project_config",
                return_value={"agdt_version": "0.2.69"},
            ),
            patch("agentic_devtools.__version__", "0.2.70"),
        ):
            # Make the packaging import fail inside check_version_guard
            original_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

            def _mock_import(name, *args, **kwargs):
                if name == "packaging.version":
                    raise ImportError("mocked")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=_mock_import):
                result = check_version_guard(tmp_path, force_old_version=False)
        assert result is None
