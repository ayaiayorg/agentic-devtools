"""Tests for validate_checklists_command() CLI entry point."""

from __future__ import annotations

import json

import pytest

from agentic_devtools.cli.speckit.validate_checklists import (
    validate_checklists_command,
)


class TestValidateChecklistsCommand:
    """Tests for the CLI entry point."""

    def test_valid_file_exits_zero(self, tmp_path) -> None:
        f = tmp_path / "checklist.md"
        f.write_text("- [ ] A\n- [ ] B\n- [ ] C\n")
        with pytest.raises(SystemExit) as exc_info:
            validate_checklists_command([str(f)])
        assert exc_info.value.code == 0

    def test_invalid_file_exits_one(self, tmp_path) -> None:
        f = tmp_path / "checklist.md"
        f.write_text("Only prose content.\n")
        with pytest.raises(SystemExit) as exc_info:
            validate_checklists_command([str(f)])
        assert exc_info.value.code == 1

    def test_min_items_override(self, tmp_path) -> None:
        f = tmp_path / "checklist.md"
        f.write_text("- [ ] A\n- [ ] B\n")  # 2 items
        with pytest.raises(SystemExit) as exc_info:
            validate_checklists_command([str(f), "--min-items", "2"])
        assert exc_info.value.code == 0

    def test_json_output(self, tmp_path, capsys) -> None:
        f = tmp_path / "checklist.md"
        f.write_text("- [ ] A\n- [ ] B\n- [ ] C\n")
        with pytest.raises(SystemExit) as exc_info:
            validate_checklists_command([str(f), "--json"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["passed"] is True
        assert len(data["files"]) == 1

    def test_no_paths_no_issue_number_exits(self, monkeypatch, tmp_path) -> None:
        monkeypatch.delenv("ISSUE_NUMBER", raising=False)
        monkeypatch.setenv("AGENTIC_DEVTOOLS_STATE_DIR", str(tmp_path))
        with pytest.raises(SystemExit) as exc_info:
            validate_checklists_command([])
        assert exc_info.value.code == 1

    def test_pipeline_mode_with_issue_number(self, tmp_path, monkeypatch) -> None:
        # Set up spec directory structure
        spec_dir = tmp_path / "specs" / "42-feature" / "checklists"
        spec_dir.mkdir(parents=True)
        (spec_dir / "requirements.md").write_text("- [ ] A\n- [ ] B\n- [ ] C\n")

        monkeypatch.setenv("SPEC_BASE_PATH", str(tmp_path / "specs"))
        monkeypatch.delenv("ISSUE_NUMBER", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            validate_checklists_command(["--issue-number", "42"])
        assert exc_info.value.code == 0

    def test_pipeline_mode_env_issue_number(self, tmp_path, monkeypatch) -> None:
        spec_dir = tmp_path / "specs" / "99-feature" / "checklists"
        spec_dir.mkdir(parents=True)
        (spec_dir / "requirements.md").write_text("- [ ] A\n- [ ] B\n- [ ] C\n")

        monkeypatch.setenv("SPEC_BASE_PATH", str(tmp_path / "specs"))
        monkeypatch.setenv("ISSUE_NUMBER", "99")

        with pytest.raises(SystemExit) as exc_info:
            validate_checklists_command([])
        assert exc_info.value.code == 0

    def test_min_items_zero_exits_two(self, tmp_path) -> None:
        f = tmp_path / "checklist.md"
        f.write_text("- [ ] A\n- [ ] B\n- [ ] C\n")
        with pytest.raises(SystemExit) as exc_info:
            validate_checklists_command([str(f), "--min-items", "0"])
        assert exc_info.value.code == 2

    def test_min_items_negative_exits_two(self, tmp_path) -> None:
        f = tmp_path / "checklist.md"
        f.write_text("- [ ] A\n- [ ] B\n- [ ] C\n")
        with pytest.raises(SystemExit) as exc_info:
            validate_checklists_command([str(f), "--min-items", "-1"])
        assert exc_info.value.code == 2

    def test_glob_zero_match_exits_zero(self, tmp_path) -> None:
        pattern = str(tmp_path / "nonexistent-*.md")
        with pytest.raises(SystemExit) as exc_info:
            validate_checklists_command([pattern])
        assert exc_info.value.code == 0
