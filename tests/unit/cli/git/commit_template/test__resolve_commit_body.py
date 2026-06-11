"""Tests for _resolve_commit_body."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.git.commit_template import _resolve_commit_body

_MOD = "agentic_devtools.cli.git.commit_template"


class TestResolveCommitBody:
    """Tests for _resolve_commit_body."""

    @patch(f"{_MOD}.get_value", return_value=None)
    def test_returns_none_when_no_state(self, mock_get):
        """Returns None when versionControl.commitMessageBodyFile is not set."""
        result = _resolve_commit_body(Path("/repo"))
        assert result is None

    @patch(f"{_MOD}.get_value", return_value="")
    def test_returns_none_for_empty_string(self, mock_get):
        """Returns None for empty string value."""
        result = _resolve_commit_body(Path("/repo"))
        assert result is None

    @patch(f"{_MOD}.get_value", return_value="body.md")
    def test_reads_relative_path(self, mock_get, tmp_path):
        """Resolves relative path against git root and reads file."""
        body_file = tmp_path / "body.md"
        body_file.write_text("commit body content", encoding="utf-8")
        result = _resolve_commit_body(tmp_path)
        assert result == "commit body content"

    @patch(f"{_MOD}.get_value")
    def test_reads_absolute_path(self, mock_get, tmp_path):
        """Reads file at absolute path within repo."""
        body_file = tmp_path / "subdir" / "body.md"
        body_file.parent.mkdir(parents=True)
        body_file.write_text("absolute body", encoding="utf-8")
        mock_get.return_value = str(body_file)
        result = _resolve_commit_body(tmp_path)
        assert result == "absolute body"

    @patch(f"{_MOD}.get_value", return_value="nonexistent.md")
    def test_returns_none_for_missing_file(self, mock_get, tmp_path):
        """Returns None when file does not exist."""
        result = _resolve_commit_body(tmp_path)
        assert result is None

    @patch(f"{_MOD}.get_value", return_value="empty.md")
    def test_returns_none_for_empty_file(self, mock_get, tmp_path):
        """Returns None when file is empty or whitespace-only."""
        body_file = tmp_path / "empty.md"
        body_file.write_text("   \n  ", encoding="utf-8")
        result = _resolve_commit_body(tmp_path)
        assert result is None

    @patch(f"{_MOD}.get_value", return_value="../outside/body.md")
    def test_path_traversal_returns_none(self, mock_get, tmp_path, capsys):
        """Returns None when path escapes repo root."""
        # Create file outside repo root
        outside = tmp_path.parent / "outside"
        outside.mkdir(exist_ok=True)
        (outside / "body.md").write_text("escaped!", encoding="utf-8")
        result = _resolve_commit_body(tmp_path)
        assert result is None
        assert "escapes repository root" in capsys.readouterr().err

    @patch(f"{_MOD}.get_value", return_value=123)
    def test_returns_none_for_non_string(self, mock_get):
        """Returns None for non-string value."""
        result = _resolve_commit_body(Path("/repo"))
        assert result is None

    @patch(f"{_MOD}.get_value", return_value="body.md")
    def test_returns_none_on_resolve_os_error(self, mock_get, tmp_path):
        """Returns None when path.resolve() raises OSError."""
        with patch("pathlib.Path.resolve", side_effect=OSError("permission denied")):
            result = _resolve_commit_body(tmp_path)
        assert result is None

    @patch(f"{_MOD}.get_value")
    def test_returns_none_when_git_root_resolve_raises_os_error(self, mock_get, tmp_path):
        """Returns None when git_root.resolve() raises OSError."""
        body_file = tmp_path / "body.md"
        body_file.write_text("body content", encoding="utf-8")
        mock_get.return_value = str(body_file)

        class BrokenRoot:
            def resolve(self):  # noqa: D401 - simple test double
                raise OSError("permission denied")

        result = _resolve_commit_body(BrokenRoot())  # type: ignore[arg-type]
        assert result is None
