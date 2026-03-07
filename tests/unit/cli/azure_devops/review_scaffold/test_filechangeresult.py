"""Tests for FileChangeResult dataclass."""

from agentic_devtools.cli.azure_devops.review_scaffold import FileChangeResult


class TestFileChangeResult:
    """Tests for FileChangeResult dataclass."""

    def test_default_empty_lists(self):
        """All fields default to empty lists."""
        result = FileChangeResult()
        assert result.new_files == []
        assert result.modified_files == []
        assert result.deleted_files == []
        assert result.unchanged_files == []
        assert result.validation_warnings == []

    def test_fields_are_mutable(self):
        """Fields can be appended to."""
        result = FileChangeResult()
        result.new_files.append("/src/new.ts")
        result.modified_files.append("/src/mod.ts")
        result.deleted_files.append("/src/del.ts")
        result.unchanged_files.append("/src/same.ts")
        result.validation_warnings.append("warning")

        assert len(result.new_files) == 1
        assert len(result.modified_files) == 1
        assert len(result.deleted_files) == 1
        assert len(result.unchanged_files) == 1
        assert len(result.validation_warnings) == 1

    def test_independent_instances(self):
        """Two instances do not share list references."""
        r1 = FileChangeResult()
        r2 = FileChangeResult()
        r1.new_files.append("/a")
        assert r2.new_files == []
