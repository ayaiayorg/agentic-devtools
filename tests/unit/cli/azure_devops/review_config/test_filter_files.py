"""Tests for filter_files function."""

from agentic_devtools.cli.azure_devops.review_config import (
    FileFilterConfig,
    filter_files,
)


class TestFilterFiles:
    """Tests for filter_files."""

    def test_no_filters_returns_all(self):
        """No include/exclude patterns returns all files."""
        files = ["src/a.ts", "lib/b.ts", "test/c.spec.ts"]
        result = filter_files(files, FileFilterConfig())
        assert result == files

    def test_include_only(self):
        """Include patterns filter to matching files only."""
        files = ["src/a.ts", "lib/b.ts", "docs/readme.md"]
        result = filter_files(files, FileFilterConfig(include=["src/**"]))
        assert result == ["src/a.ts"]

    def test_exclude_only(self):
        """Exclude patterns remove matching files."""
        files = ["src/a.ts", "src/a.test.ts", "src/b.ts"]
        result = filter_files(files, FileFilterConfig(exclude=["*.test.ts"]))
        assert result == ["src/a.ts", "src/b.ts"]

    def test_include_and_exclude(self):
        """Include filters first, then exclude removes from included set."""
        files = ["src/a.ts", "src/a.test.ts", "lib/b.ts", "lib/b.spec.ts"]
        result = filter_files(
            files,
            FileFilterConfig(
                include=["src/**", "lib/**"],
                exclude=["*.test.ts", "*.spec.ts"],
            ),
        )
        assert result == ["src/a.ts", "lib/b.ts"]

    def test_recursive_pattern(self):
        """** patterns match across directory levels."""
        files = ["src/deep/nested/file.ts", "src/file.ts", "other/file.ts"]
        result = filter_files(files, FileFilterConfig(include=["src/**"]))
        assert result == ["src/deep/nested/file.ts", "src/file.ts"]

    def test_exclude_generated(self):
        """Excludes generated directory files."""
        files = [
            "src/app/component.ts",
            "src/generated/api.ts",
            "src/generated/models.ts",
        ]
        result = filter_files(
            files,
            FileFilterConfig(exclude=["**/generated/**"]),
        )
        assert result == ["src/app/component.ts"]

    def test_empty_files_list(self):
        """Empty file list returns empty."""
        result = filter_files([], FileFilterConfig(include=["src/**"]))
        assert result == []
