"""Tests for the _try_get_workspace_root helper function."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli import testing

from .conftest import make_workspace_root_error


class TestTryGetWorkspaceRoot:
    """Tests for _try_get_workspace_root helper."""

    def test_returns_path_on_success(self, tmp_path, monkeypatch):
        """Should return workspace root Path when pyproject.toml exists."""
        (tmp_path / "pyproject.toml").write_text("")
        monkeypatch.chdir(tmp_path)
        result = testing._try_get_workspace_root()
        assert isinstance(result, Path)
        assert result == tmp_path

    def test_returns_none_on_missing_sentinel(self, tmp_path, monkeypatch, capsys):
        """Should return None and print error when pyproject.toml is missing."""
        monkeypatch.chdir(tmp_path)
        result = testing._try_get_workspace_root()
        assert result is None
        captured = capsys.readouterr()
        assert "pyproject.toml not found" in captured.err

    def test_prints_clean_error_without_traceback(self, tmp_path, capsys):
        """Should print a single-line error, not a traceback."""
        error_msg = make_workspace_root_error(tmp_path)
        with patch.object(
            testing,
            "get_workspace_root",
            side_effect=FileNotFoundError(error_msg),
        ):
            result = testing._try_get_workspace_root()
            assert result is None
            captured = capsys.readouterr()
            assert f"Error: {error_msg}" in captured.err
            # Should NOT contain traceback markers
            assert "Traceback" not in captured.err
