"""Tests for remediate_file() function."""

from __future__ import annotations

from agentic_devtools.cli.speckit.validate_checklists import (
    FileClassification,
    remediate_file,
)


class TestRemediateFile:
    """Tests for remediate_file stub."""

    def test_returns_unremediated_for_prose_only(self, tmp_path) -> None:
        f = tmp_path / "prose.md"
        f.write_text("# Just prose\n\nNo checkboxes here.\n")
        result = remediate_file(str(f))
        assert result.remediated is False
        assert result.retries_used == 0
        assert result.file_result.classification == FileClassification.prose_only

    def test_returns_unremediated_for_deficient(self, tmp_path) -> None:
        f = tmp_path / "deficient.md"
        f.write_text("- [ ] Only one\n")
        result = remediate_file(str(f))
        assert result.remediated is False
        assert result.retries_used == 0
        assert result.file_result.classification == FileClassification.deficient

    def test_valid_file_returns_valid(self, tmp_path) -> None:
        f = tmp_path / "valid.md"
        f.write_text("- [ ] A\n- [ ] B\n- [ ] C\n")
        result = remediate_file(str(f))
        assert result.file_result.classification == FileClassification.valid
