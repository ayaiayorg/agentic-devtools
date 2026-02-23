"""Tests for find_workspace_file."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import find_workspace_file


class TestFindWorkspaceFile:
    """Tests for find_workspace_file function."""

    def test_returns_none_when_no_workspace_file(self, tmp_path):
        """Returns None when no .code-workspace file exists."""
        result = find_workspace_file(str(tmp_path))
        assert result is None

    def test_finds_workspace_file_with_any_prefix(self, tmp_path):
        """Finds a .code-workspace file regardless of its prefix."""
        workspace = tmp_path / "dfly-platform-management.code-workspace"
        workspace.write_text("{}")

        result = find_workspace_file(str(tmp_path))

        assert result == str(workspace)

    def test_finds_workspace_file_with_agdt_prefix(self, tmp_path):
        """Finds a .code-workspace file that starts with agdt-."""
        workspace = tmp_path / "agdt-platform-management.code-workspace"
        workspace.write_text("{}")

        result = find_workspace_file(str(tmp_path))

        assert result == str(workspace)

    def test_ignores_non_workspace_files(self, tmp_path):
        """Does not return non-.code-workspace files."""
        (tmp_path / "README.md").write_text("# readme")
        (tmp_path / "some.workspace").write_text("{}")

        result = find_workspace_file(str(tmp_path))

        assert result is None

    def test_returns_none_for_nonexistent_directory(self, tmp_path):
        """Returns None when the directory does not exist."""
        missing = tmp_path / "nonexistent_dir"
        result = find_workspace_file(str(missing))
        assert result is None

    def test_returns_alphabetically_first_workspace_file(self, tmp_path):
        """Returns the alphabetically first workspace file when multiple exist."""
        (tmp_path / "b.code-workspace").write_text("{}")
        (tmp_path / "a.code-workspace").write_text("{}")

        result = find_workspace_file(str(tmp_path))

        assert result == str(tmp_path / "a.code-workspace")

    def test_prints_warning_on_unexpected_os_error(self, tmp_path, capsys):
        """Prints a warning to stderr on unexpected OSError (e.g., PermissionError)."""
        with patch("os.scandir", side_effect=PermissionError("Access denied")):
            result = find_workspace_file(str(tmp_path))

        assert result is None
        captured = capsys.readouterr()
        assert "Warning: unexpected OS error" in captured.err
        assert "Access denied" in captured.err
