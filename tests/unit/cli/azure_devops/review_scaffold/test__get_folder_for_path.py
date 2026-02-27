"""Tests for _get_folder_for_path helper."""

from agentic_devtools.cli.azure_devops.review_scaffold import _get_folder_for_path


class TestGetFolderForPath:
    """Tests for _get_folder_for_path helper."""

    def test_path_with_folder(self):
        """Extracts top-level folder from a nested path."""
        assert _get_folder_for_path("/src/app/file.ts") == "src"

    def test_root_level_file(self):
        """Returns 'root' for a file at the repo root."""
        assert _get_folder_for_path("/README.md") == "root"

    def test_path_without_leading_slash(self):
        """Works correctly when path has no leading slash."""
        assert _get_folder_for_path("src/app/file.ts") == "src"

    def test_two_segment_path(self):
        """Extracts folder from a two-segment path."""
        assert _get_folder_for_path("/utils/helpers.py") == "utils"
