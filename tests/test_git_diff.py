"""
Tests for git diff helper module.
"""

from unittest.mock import MagicMock, patch

from dfly_ai_helpers.cli.git.diff import (
    AddedLine,
    AddedLinesInfo,
    DiffEntry,
    get_added_lines_info,
    get_diff_entries,
    get_diff_patch,
    normalize_ref_name,
    sync_git_ref,
)


class TestNormalizeRefName:
    """Tests for normalize_ref_name function."""

    def test_strips_refs_heads_prefix(self):
        """Should strip refs/heads/ prefix from ref names."""
        result = normalize_ref_name("refs/heads/main")
        assert result == "main"

    def test_strips_refs_heads_prefix_with_slashes(self):
        """Should handle ref names with slashes."""
        result = normalize_ref_name("refs/heads/feature/my-branch")
        assert result == "feature/my-branch"

    def test_returns_unchanged_if_no_prefix(self):
        """Should return ref unchanged if no prefix."""
        result = normalize_ref_name("main")
        assert result == "main"

    def test_returns_none_for_none(self):
        """Should return None for None input."""
        result = normalize_ref_name(None)
        assert result is None

    def test_returns_none_for_empty_string(self):
        """Should return None for empty string."""
        result = normalize_ref_name("")
        assert result is None


class TestDataClasses:
    """Tests for data classes."""

    def test_diff_entry_creation(self):
        """Should create DiffEntry with all fields."""
        entry = DiffEntry(path="src/main.py", status="M", change_type="M", original_path=None)
        assert entry.path == "src/main.py"
        assert entry.status == "M"
        assert entry.change_type == "M"
        assert entry.original_path is None

    def test_diff_entry_with_rename(self):
        """Should create DiffEntry for rename with original path."""
        entry = DiffEntry(
            path="src/new_name.py",
            status="R100",
            change_type="R",
            original_path="src/old_name.py",
        )
        assert entry.path == "src/new_name.py"
        assert entry.original_path == "src/old_name.py"
        assert entry.change_type == "R"

    def test_added_line_creation(self):
        """Should create AddedLine with line number and content."""
        line = AddedLine(line_number=42, content="def hello():")
        assert line.line_number == 42
        assert line.content == "def hello():"

    def test_added_lines_info_creation(self):
        """Should create AddedLinesInfo with lines and binary flag."""
        lines = [AddedLine(1, "line 1"), AddedLine(2, "line 2")]
        info = AddedLinesInfo(lines=lines, is_binary=False)
        assert len(info.lines) == 2
        assert info.is_binary is False

    def test_added_lines_info_binary(self):
        """Should create AddedLinesInfo for binary file."""
        info = AddedLinesInfo(lines=[], is_binary=True)
        assert len(info.lines) == 0
        assert info.is_binary is True


class TestSyncGitRef:
    """Tests for sync_git_ref function."""

    def test_returns_false_for_empty_ref(self):
        """Should return False for empty ref."""
        assert sync_git_ref("") is False

    def test_returns_false_for_none_ref(self):
        """Should return False for None ref."""
        assert sync_git_ref(None) is False

    def test_returns_true_when_ref_exists_locally(self):
        """Should return True when ref exists locally."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = sync_git_ref("main")
            assert result is True

    def test_fetches_from_origin_when_not_local(self):
        """Should fetch from origin when ref doesn't exist locally."""
        # First call fails (doesn't exist), second succeeds (fetch works)
        mock_fail = MagicMock()
        mock_fail.returncode = 1
        mock_success = MagicMock()
        mock_success.returncode = 0

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", side_effect=[mock_fail, mock_success]) as mock_run:
            result = sync_git_ref("feature-branch")

            assert result is True
            # Second call should be git fetch origin feature-branch
            assert mock_run.call_count == 2
            fetch_call = mock_run.call_args_list[1]
            assert "fetch" in fetch_call[0][0]

    def test_strips_origin_prefix_when_fetching(self):
        """Should strip origin/ prefix when fetching."""
        mock_fail = MagicMock()
        mock_fail.returncode = 1
        mock_success = MagicMock()
        mock_success.returncode = 0

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", side_effect=[mock_fail, mock_success]) as mock_run:
            result = sync_git_ref("origin/main")

            assert result is True
            # Fetch should use "main" not "origin/main"
            fetch_call = mock_run.call_args_list[1]
            assert "main" in fetch_call[0][0]
            assert "origin/main" not in fetch_call[0][0]

    def test_returns_false_when_fetch_fails(self):
        """Should return False when both local check and fetch fail."""
        mock_fail = MagicMock()
        mock_fail.returncode = 1

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_fail):
            result = sync_git_ref("nonexistent-branch")
            assert result is False


class TestGetDiffEntries:
    """Tests for get_diff_entries function."""

    def test_returns_empty_list_on_error(self):
        """Should return empty list when git command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")
            assert result == []

    def test_returns_empty_list_on_empty_output(self):
        """Should return empty list when no changes."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")
            assert result == []

    def test_parses_modified_file(self):
        """Should parse modified file status."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "M\tsrc/main.py"

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")

            assert len(result) == 1
            assert result[0].path == "src/main.py"
            assert result[0].status == "M"
            assert result[0].change_type == "M"

    def test_parses_added_file(self):
        """Should parse added file status."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "A\tnew_file.py"

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")

            assert len(result) == 1
            assert result[0].path == "new_file.py"
            assert result[0].change_type == "A"

    def test_parses_deleted_file(self):
        """Should parse deleted file status."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "D\told_file.py"

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")

            assert len(result) == 1
            assert result[0].path == "old_file.py"
            assert result[0].change_type == "D"

    def test_parses_renamed_file(self):
        """Should parse renamed file with original path."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "R100\told_name.py\tnew_name.py"

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")

            assert len(result) == 1
            assert result[0].path == "new_name.py"
            assert result[0].original_path == "old_name.py"
            assert result[0].change_type == "R"

    def test_parses_multiple_files(self):
        """Should parse multiple file changes."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "M\tfile1.py\nA\tfile2.py\nD\tfile3.py"

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")

            assert len(result) == 3
            assert result[0].path == "file1.py"
            assert result[1].path == "file2.py"
            assert result[2].path == "file3.py"

    def test_skips_empty_lines(self):
        """Should skip empty lines in output."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "M\tfile1.py\n\nA\tfile2.py"

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")

            assert len(result) == 2

    def test_skips_malformed_lines(self):
        """Should skip lines without tab separator."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "M\tfile1.py\nmalformed line\nA\tfile2.py"

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_entries("main", "feature")

            assert len(result) == 2


class TestGetAddedLinesInfo:
    """Tests for get_added_lines_info function."""

    def test_returns_empty_on_error(self):
        """Should return empty info on git command failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_added_lines_info("main", "feature", "file.py")

            assert result.lines == []
            assert result.is_binary is False

    def test_returns_empty_on_no_changes(self):
        """Should return empty info when no changes."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_added_lines_info("main", "feature", "file.py")

            assert result.lines == []
            assert result.is_binary is False

    def test_detects_binary_file(self):
        """Should detect binary files."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Binary files a/image.png and b/image.png differ"

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_added_lines_info("main", "feature", "image.png")

            assert result.lines == []
            assert result.is_binary is True

    def test_parses_added_lines(self):
        """Should parse added lines from diff output."""
        diff_output = """diff --git a/file.py b/file.py
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 line 1
+new line 2
 line 3
 line 4"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = diff_output

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_added_lines_info("main", "feature", "file.py")

            assert len(result.lines) == 1
            assert result.lines[0].content == "new line 2"
            assert result.is_binary is False

    def test_parses_multiple_hunks(self):
        """Should parse multiple hunks correctly."""
        diff_output = """@@ -1,2 +1,3 @@
 line 1
+new at line 2
 line 2
@@ -10,2 +11,3 @@
 line 10
+new at line 12
 line 11"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = diff_output

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_added_lines_info("main", "feature", "file.py")

            assert len(result.lines) == 2
            assert result.lines[0].content == "new at line 2"
            assert result.lines[1].content == "new at line 12"

    def test_ignores_removed_lines(self):
        """Should not count removed lines."""
        diff_output = """@@ -1,3 +1,2 @@
 line 1
-removed line
 line 3"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = diff_output

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_added_lines_info("main", "feature", "file.py")

            assert len(result.lines) == 0

    def test_uses_repo_root_relative_path(self):
        """Should use :/ prefix to make path repo-root-relative."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result) as mock_run:
            get_added_lines_info("main", "feature", "src/file.py")

            # Verify the path argument uses :/ prefix for repo-root-relative
            call_args = mock_run.call_args[0][0]
            assert ":/src/file.py" in call_args


class TestGetDiffPatch:
    """Tests for get_diff_patch function."""

    def test_returns_none_on_error(self):
        """Should return None on git command failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_patch("main", "feature", "file.py")
            assert result is None

    def test_returns_none_on_empty_output(self):
        """Should return None when no changes."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_patch("main", "feature", "file.py")
            assert result is None

    def test_returns_stripped_patch(self):
        """Should return stripped diff patch."""
        patch_content = """diff --git a/file.py b/file.py
--- a/file.py
+++ b/file.py
@@ -1,2 +1,3 @@
 line 1
+new line
 line 2
"""

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = patch_content

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result):
            result = get_diff_patch("main", "feature", "file.py")

            assert result is not None
            assert "diff --git" in result
            assert "+new line" in result

    def test_uses_repo_root_relative_path(self):
        """Should use :/ prefix to make path repo-root-relative."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("dfly_ai_helpers.cli.git.diff.run_safe", return_value=mock_result) as mock_run:
            get_diff_patch("main", "feature", "src/file.py")

            # Verify the path argument uses :/ prefix for repo-root-relative
            call_args = mock_run.call_args[0][0]
            assert ":/src/file.py" in call_args
