"""Tests for _verify_source_issue_marker() helper."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agentic_devtools.cli.speckit.validate_checklists import _verify_source_issue_marker


class TestVerifySourceIssueMarker:
    """Tests for _verify_source_issue_marker."""

    def test_marker_found_in_requirements_md(self, tmp_path) -> None:
        checklists = tmp_path / "checklists"
        checklists.mkdir()
        (checklists / "requirements.md").write_text("**Source Issue** #123\nSome content\n")
        # Should not raise or exit
        _verify_source_issue_marker(str(tmp_path), 123)

    def test_marker_found_in_spec_md(self, tmp_path) -> None:
        (tmp_path / "spec.md").write_text("**Source Issue** - see #456\n", encoding="utf-8")
        _verify_source_issue_marker(str(tmp_path), 456)

    def test_no_marker_exits(self, tmp_path) -> None:
        checklists = tmp_path / "checklists"
        checklists.mkdir()
        (checklists / "requirements.md").write_text("No marker here.\n")
        (tmp_path / "spec.md").write_text("Also no marker.\n")
        with pytest.raises(SystemExit) as exc_info:
            _verify_source_issue_marker(str(tmp_path), 999)
        assert exc_info.value.code == 1

    def test_no_candidate_files_exits(self, tmp_path) -> None:
        # No checklists/requirements.md or spec.md exist
        with pytest.raises(SystemExit) as exc_info:
            _verify_source_issue_marker(str(tmp_path), 100)
        assert exc_info.value.code == 1

    def test_oserror_on_read_continues_to_next(self, tmp_path) -> None:
        checklists = tmp_path / "checklists"
        checklists.mkdir()
        req_file = checklists / "requirements.md"
        req_file.write_text("**Source Issue** #200\n")

        # Patch Path.read_text to raise OSError on first call, then succeed
        original_read_text = type(req_file).read_text

        call_count = {"n": 0}

        def patched_read_text(self, *args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise OSError("permission denied")
            return original_read_text(self, *args, **kwargs)

        # Put the marker in spec.md as fallback
        (tmp_path / "spec.md").write_text("**Source Issue** #200\n")

        with patch.object(type(req_file), "read_text", patched_read_text):
            # Should not exit — falls through to spec.md
            _verify_source_issue_marker(str(tmp_path), 200)

    def test_oserror_on_all_candidates_exits(self, tmp_path) -> None:
        checklists = tmp_path / "checklists"
        checklists.mkdir()
        (checklists / "requirements.md").write_text("dummy")
        (tmp_path / "spec.md").write_text("dummy")

        with patch("pathlib.Path.read_text", side_effect=OSError("fail")):
            with pytest.raises(SystemExit) as exc_info:
                _verify_source_issue_marker(str(tmp_path), 300)
            assert exc_info.value.code == 1
