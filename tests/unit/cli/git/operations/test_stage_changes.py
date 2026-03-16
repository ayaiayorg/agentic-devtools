"""Tests for agentic_devtools.cli.git.operations.stage_changes."""

from unittest.mock import MagicMock, patch

from agentic_devtools.agdt_gitignore import AGDT_GITIGNORE_ENTRIES
from agentic_devtools.cli.git import operations


class TestStageChanges:
    """Tests for stage_changes function."""

    def test_stage_changes(self, mock_run_safe):
        """Test staging all changes calls git add . then unstages excluded files."""
        with patch.object(operations, "get_current_branch", return_value="main"):
            operations.stage_changes(dry_run=False)
        calls = mock_run_safe.call_args_list
        # First call is git add .
        assert calls[0][0][0] == ["git", "add", "."]
        # Subsequent calls are git reset HEAD -- <excluded_file> for each excluded file
        for i, excluded in enumerate(operations.STAGE_EXCLUDE_FILES):
            assert calls[i + 1][0][0] == ["git", "reset", "HEAD", "--", excluded]

    def test_stage_changes_dry_run(self, mock_run_safe, capsys):
        """Test dry run calls get_current_branch but no git commands."""
        with patch.object(operations, "get_current_branch", return_value="main"):
            operations.stage_changes(dry_run=True)
        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out

    def test_stage_changes_dry_run_mentions_excluded_files(self, mock_run_safe, capsys):
        """Test dry run output mentions each excluded file."""
        with patch.object(operations, "get_current_branch", return_value="main"):
            operations.stage_changes(dry_run=True)
        captured = capsys.readouterr()
        for excluded in operations.STAGE_EXCLUDE_FILES:
            assert excluded in captured.out

    def test_stage_changes_version_file_excluded(self, mock_run_safe):
        """Test that _version.py is in the exclude list."""
        assert "agentic_devtools/_version.py" in operations.STAGE_EXCLUDE_FILES

    def test_agdt_gitignore_entries_imported(self):
        """Test that AGDT_GITIGNORE_ENTRIES is accessible from operations module."""
        assert operations.AGDT_GITIGNORE_ENTRIES is AGDT_GITIGNORE_ENTRIES

    def test_stage_changes_excludes_all_entries_on_non_agdt_branch(self, mock_run_safe):
        """Test that all AGDT_GITIGNORE_ENTRIES are unstaged on non -agdt branches."""
        with patch.object(operations, "get_current_branch", return_value="feature/DFLY-1234"):
            operations.stage_changes(dry_run=False)
        calls = [c[0][0] for c in mock_run_safe.call_args_list]
        for entry in AGDT_GITIGNORE_ENTRIES:
            assert ["git", "reset", "HEAD", "--", f".agdt/{entry}"] in calls

    def test_stage_changes_includes_entries_on_agdt_branch(self, mock_run_safe):
        """Test that AGDT_GITIGNORE_ENTRIES stay staged on -agdt branches."""
        with patch.object(operations, "get_current_branch", return_value="feature/DFLY-1234-agdt"):
            operations.stage_changes(dry_run=False)
        calls = [c[0][0] for c in mock_run_safe.call_args_list]
        for entry in AGDT_GITIGNORE_ENTRIES:
            assert ["git", "reset", "HEAD", "--", f".agdt/{entry}"] not in calls

    def test_stage_changes_dry_run_non_agdt_branch(self, mock_run_safe, capsys):
        """Test dry run prints unstage message on non -agdt branch."""
        with patch.object(operations, "get_current_branch", return_value="feature/DFLY-1234"):
            operations.stage_changes(dry_run=True)
        captured = capsys.readouterr()
        for entry in AGDT_GITIGNORE_ENTRIES:
            assert f"[DRY RUN] Would unstage .agdt/{entry}" in captured.out
            assert "not on -agdt branch" in captured.out

    def test_stage_changes_dry_run_agdt_branch(self, mock_run_safe, capsys):
        """Test dry run prints keep-staged message on -agdt branch."""
        with patch.object(operations, "get_current_branch", return_value="feature/DFLY-1234-agdt"):
            operations.stage_changes(dry_run=True)
        captured = capsys.readouterr()
        for entry in AGDT_GITIGNORE_ENTRIES:
            assert f".agdt/{entry} will stay staged" in captured.out
            assert "on -agdt branch" in captured.out
        assert "[DRY RUN] Would remove .agdt/.gitignore (on -agdt branch)" in captured.out

    def test_stage_changes_existing_exclude_files_unchanged(self, mock_run_safe):
        """Regression: STAGE_EXCLUDE_FILES resets still happen in same positions."""
        with patch.object(operations, "get_current_branch", return_value="feature/DFLY-1234"):
            operations.stage_changes(dry_run=False)
        calls = [c[0][0] for c in mock_run_safe.call_args_list]
        # First call is git add .
        assert calls[0] == ["git", "add", "."]
        # STAGE_EXCLUDE_FILES resets come immediately after git add .
        for i, excluded in enumerate(operations.STAGE_EXCLUDE_FILES):
            assert calls[i + 1] == ["git", "reset", "HEAD", "--", excluded]
        # AGDT_GITIGNORE_ENTRIES resets come after STAGE_EXCLUDE_FILES resets
        n = len(operations.STAGE_EXCLUDE_FILES)
        for i, entry in enumerate(AGDT_GITIGNORE_ENTRIES):
            assert calls[n + 1 + i] == ["git", "reset", "HEAD", "--", f".agdt/{entry}"]

    def test_stage_changes_deletes_gitignore_on_agdt_branch(self, mock_run_safe, tmp_path):
        """On -agdt branch, verify .agdt/.gitignore deletion."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        gi_path = agdt_dir / ".gitignore"
        gi_path.write_text("# test\n", encoding="utf-8")

        toplevel_result = MagicMock(returncode=0, stdout=str(tmp_path))
        mock_run_safe.return_value = toplevel_result

        with patch.object(operations, "get_current_branch", return_value="feature/DFLY-1234-agdt"):
            operations.stage_changes(dry_run=False)

        assert not gi_path.exists()

    def test_stage_changes_no_gitignore_deletion_on_non_agdt_branch(self, mock_run_safe, tmp_path):
        """On non-agdt branch, verify no .gitignore deletion."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        gi_path = agdt_dir / ".gitignore"
        gi_path.write_text("# test\n", encoding="utf-8")

        with patch.object(operations, "get_current_branch", return_value="feature/DFLY-1234"):
            operations.stage_changes(dry_run=False)

        # File should still exist
        assert gi_path.exists()
