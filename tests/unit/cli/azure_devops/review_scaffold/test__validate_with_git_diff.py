"""Tests for _validate_with_git_diff helper function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.review_scaffold import FileChangeResult, _validate_with_git_diff

# run_safe is imported locally inside _validate_with_git_diff, so we
# patch it at the source module.
_RUN_SAFE_PATH = "agentic_devtools.cli.subprocess_utils.run_safe"


class TestValidateWithGitDiff:
    """Tests for _validate_with_git_diff."""

    def test_no_warnings_when_results_match(self):
        """No warnings when git diff matches iterations API result."""
        result = FileChangeResult()
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "/src/a.ts\n"

        with patch(_RUN_SAFE_PATH, return_value=mock_proc):
            _validate_with_git_diff(
                result,
                "old",
                "new",
                iteration_changed_files={"/src/a.ts"},
                current_file_set={"/src/a.ts"},
            )

        assert result.validation_warnings == []

    def test_warning_when_git_diff_has_extra_file(self):
        """Warning when git diff shows a changed file not in iterations API."""
        result = FileChangeResult()
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "/src/a.ts\n/src/b.ts\n"

        with patch(_RUN_SAFE_PATH, return_value=mock_proc):
            _validate_with_git_diff(
                result,
                "old",
                "new",
                iteration_changed_files={"/src/a.ts"},
                current_file_set={"/src/a.ts", "/src/b.ts"},
            )

        assert any("/src/b.ts" in w for w in result.validation_warnings)

    def test_warning_when_iterations_api_has_extra_file(self):
        """Warning when iterations API shows a changed file not in git diff."""
        result = FileChangeResult()
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "/src/a.ts\n"

        with patch(_RUN_SAFE_PATH, return_value=mock_proc):
            _validate_with_git_diff(
                result,
                "old",
                "new",
                iteration_changed_files={"/src/a.ts", "/src/b.ts"},
                current_file_set={"/src/a.ts", "/src/b.ts"},
            )

        assert any("/src/b.ts" in w for w in result.validation_warnings)

    def test_git_diff_failure_adds_unavailable_warning(self):
        """When git diff fails (non-zero exit), adds 'git diff unavailable' warning."""
        result = FileChangeResult()
        mock_proc = MagicMock()
        mock_proc.returncode = 128

        with patch(_RUN_SAFE_PATH, return_value=mock_proc):
            _validate_with_git_diff(result, "old", "new", set(), set())

        assert "git diff unavailable" in result.validation_warnings

    def test_git_diff_exception_adds_unavailable_warning(self):
        """When run_safe raises an exception, adds 'git diff unavailable' warning."""
        result = FileChangeResult()

        with patch(_RUN_SAFE_PATH, side_effect=FileNotFoundError("git not found")):
            _validate_with_git_diff(result, "old", "new", set(), set())

        assert "git diff unavailable" in result.validation_warnings

    def test_ignores_files_not_in_current_file_set(self):
        """Files in git diff but not in current_file_set are ignored (not warned about)."""
        result = FileChangeResult()
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "/old/removed.ts\n"

        with patch(_RUN_SAFE_PATH, return_value=mock_proc):
            _validate_with_git_diff(
                result,
                "old",
                "new",
                iteration_changed_files=set(),
                current_file_set={"/src/a.ts"},
            )

        # /old/removed.ts is not in current_file_set, so no warning
        assert result.validation_warnings == []
