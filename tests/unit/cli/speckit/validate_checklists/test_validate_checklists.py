"""Tests for validate_checklists() orchestrator function."""

from __future__ import annotations

from agentic_devtools.cli.speckit.validate_checklists import (
    FileClassification,
    validate_checklists,
)


class TestValidateChecklists:
    """Tests for validate_checklists orchestrator."""

    def test_empty_paths_returns_warning(self) -> None:
        result = validate_checklists([])
        assert result.passed is True
        assert result.warning is not None
        assert "No checklist files" in result.warning

    def test_single_valid_file(self, tmp_path) -> None:
        f = tmp_path / "checklist.md"
        f.write_text("- [ ] A\n- [ ] B\n- [ ] C\n")
        result = validate_checklists([str(f)])
        assert result.passed is True
        assert len(result.files) == 1
        assert result.files[0].classification == FileClassification.valid

    def test_single_invalid_file(self, tmp_path) -> None:
        f = tmp_path / "checklist.md"
        f.write_text("Just prose.\n")
        result = validate_checklists([str(f)])
        assert result.passed is False
        assert len(result.files) == 1
        assert result.files[0].classification == FileClassification.prose_only

    def test_multiple_files_mixed(self, tmp_path) -> None:
        valid = tmp_path / "valid.md"
        valid.write_text("- [ ] A\n- [ ] B\n- [ ] C\n")
        invalid = tmp_path / "invalid.md"
        invalid.write_text("Just prose.\n")
        result = validate_checklists([str(valid), str(invalid)])
        assert result.passed is False
        assert len(result.files) == 2

    def test_all_valid_passes(self, tmp_path) -> None:
        f1 = tmp_path / "a.md"
        f1.write_text("- [ ] A\n- [ ] B\n- [ ] C\n")
        f2 = tmp_path / "b.md"
        f2.write_text("- [x] D\n- [ ] E\n- [X] F\n")
        result = validate_checklists([str(f1), str(f2)])
        assert result.passed is True

    def test_custom_min_items(self, tmp_path) -> None:
        f = tmp_path / "checklist.md"
        f.write_text("- [ ] A\n- [ ] B\n")  # 2 items
        result = validate_checklists([str(f)], min_items=2)
        assert result.passed is True

    def test_retry_triggers_remediation_for_invalid_file(self, tmp_path) -> None:
        f = tmp_path / "checklist.md"
        f.write_text("Just prose, no checkboxes.\n")
        result = validate_checklists([str(f)], retry=True)
        # File remains invalid because remediate_file is a stub
        assert result.passed is False
        assert len(result.files) == 1
        assert result.files[0].remediated is False
        assert result.files[0].retries_used == 0

    def test_retry_not_triggered_for_valid_file(self, tmp_path) -> None:
        f = tmp_path / "checklist.md"
        f.write_text("- [ ] A\n- [ ] B\n- [ ] C\n")
        result = validate_checklists([str(f)], retry=True)
        assert result.passed is True
        assert result.files[0].classification == FileClassification.valid
        # remediated should not be set for valid files
        assert result.files[0].remediated is False

    def test_aggregate_result_to_json(self, tmp_path) -> None:
        f = tmp_path / "checklist.md"
        f.write_text("- [ ] A\n- [ ] B\n- [ ] C\n")
        result = validate_checklists([str(f)])
        json_out = result.to_json()
        assert json_out["passed"] is True
        assert len(json_out["files"]) == 1
        assert json_out["files"][0]["classification"] == "valid"
