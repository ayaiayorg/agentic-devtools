"""Tests for the get_workspace_root function."""

from pathlib import Path

import pytest

from agentic_devtools.cli import testing


class TestGetWorkspaceRoot:
    """Tests for get_workspace_root function."""

    def test_returns_path(self, tmp_path, monkeypatch):
        """Should return a Path object."""
        (tmp_path / "pyproject.toml").write_text("")
        monkeypatch.chdir(tmp_path)
        result = testing.get_workspace_root()
        assert isinstance(result, Path)

    def test_returns_current_working_directory(self, tmp_path, monkeypatch):
        """Should return the current working directory."""
        (tmp_path / "pyproject.toml").write_text("")
        monkeypatch.chdir(tmp_path)
        result = testing.get_workspace_root()
        assert result == tmp_path

    def test_raises_error_when_pyproject_toml_missing(self, tmp_path, monkeypatch):
        """Should raise FileNotFoundError when pyproject.toml is not in CWD."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError, match="pyproject.toml not found in current directory"):
            testing.get_workspace_root()
