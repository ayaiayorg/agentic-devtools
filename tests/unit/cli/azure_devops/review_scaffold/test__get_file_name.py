"""Tests for _get_file_name helper."""

from agentic_devtools.cli.azure_devops.review_scaffold import _get_file_name


class TestGetFileName:
    """Tests for _get_file_name helper."""

    def test_nested_path(self):
        """Returns the base file name from a nested path."""
        assert _get_file_name("/src/app/component.ts") == "component.ts"

    def test_root_level_file(self):
        """Returns the file name for a root-level file."""
        assert _get_file_name("/README.md") == "README.md"

    def test_path_without_leading_slash(self):
        """Works when path has no leading slash."""
        assert _get_file_name("src/app/file.ts") == "file.ts"
