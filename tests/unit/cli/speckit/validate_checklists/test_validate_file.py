"""Tests for validate_file() function."""

from __future__ import annotations

import pytest

from agentic_devtools.cli.speckit.validate_checklists import (
    FileClassification,
    Severity,
    validate_file,
)


class TestValidateFile:
    """Tests for validate_file function."""

    def test_valid_file(self, tmp_path) -> None:
        f = tmp_path / "checklist.md"
        f.write_text("- [ ] Item 1\n- [ ] Item 2\n- [x] Item 3\n")
        result = validate_file(str(f))
        assert result.classification == FileClassification.valid
        assert result.checkbox_count == 3
        assert result.severity == Severity.NONE
        assert "valid" in result.explanation

    def test_deficient_file(self, tmp_path) -> None:
        f = tmp_path / "checklist.md"
        f.write_text("- [ ] Only one item\n")
        result = validate_file(str(f))
        assert result.classification == FileClassification.deficient
        assert result.checkbox_count == 1
        assert result.severity == Severity.LOW
        assert "deficient" in result.explanation

    def test_prose_only_file(self, tmp_path) -> None:
        f = tmp_path / "checklist.md"
        f.write_text("# Heading\n\nSome prose description.\n\n- Regular item\n")
        result = validate_file(str(f))
        assert result.classification == FileClassification.prose_only
        assert result.checkbox_count == 0
        assert result.severity == Severity.MEDIUM
        assert "prose-only" in result.explanation

    def test_file_not_found_exits(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            validate_file("/nonexistent/path/file.md")
        assert exc_info.value.code == 2

    def test_path_stored_in_result(self, tmp_path) -> None:
        f = tmp_path / "my-checklist.md"
        f.write_text("- [ ] A\n- [ ] B\n- [ ] C\n")
        result = validate_file(str(f))
        assert result.path == str(f)

    def test_custom_min_items(self, tmp_path) -> None:
        f = tmp_path / "checklist.md"
        f.write_text("- [ ] A\n- [ ] B\n- [ ] C\n- [ ] D\n- [ ] E\n")
        result = validate_file(str(f), min_items=5)
        assert result.classification == FileClassification.valid
        assert result.checkbox_count == 5
