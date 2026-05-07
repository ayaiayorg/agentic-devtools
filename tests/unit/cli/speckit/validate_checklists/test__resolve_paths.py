"""Tests for _resolve_paths() function."""

from __future__ import annotations

import os

import pytest

from agentic_devtools.cli.speckit.validate_checklists import _resolve_paths


class TestResolvePaths:
    """Tests for _resolve_paths helper."""

    def test_explicit_file_exists(self, tmp_path) -> None:
        f = tmp_path / "file.md"
        f.write_text("content")
        result = _resolve_paths([str(f)])
        assert len(result) == 1
        assert result[0] == os.path.abspath(str(f))

    def test_explicit_file_not_found_exits(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            _resolve_paths(["/nonexistent/file.md"])
        assert exc_info.value.code == 2

    def test_glob_expansion(self, tmp_path) -> None:
        (tmp_path / "a.md").write_text("a")
        (tmp_path / "b.md").write_text("b")
        (tmp_path / "c.txt").write_text("c")
        pattern = str(tmp_path / "*.md")
        result = _resolve_paths([pattern])
        assert len(result) == 2

    def test_glob_no_match_warning(self, tmp_path, capsys) -> None:
        pattern = str(tmp_path / "nonexistent-*.md")
        result = _resolve_paths([pattern])
        assert result == []
        captured = capsys.readouterr()
        assert "WARNING" in captured.err

    def test_deduplication(self, tmp_path) -> None:
        f = tmp_path / "file.md"
        f.write_text("content")
        result = _resolve_paths([str(f), str(f)])
        assert len(result) == 1

    def test_multi_directory_collision(self, tmp_path) -> None:
        # Create two spec directories with same issue prefix
        dir1 = tmp_path / "specs" / "123-foo" / "checklists"
        dir1.mkdir(parents=True)
        (dir1 / "a.md").write_text("content")
        dir2 = tmp_path / "specs" / "123-bar" / "checklists"
        dir2.mkdir(parents=True)
        (dir2 / "b.md").write_text("content")

        pattern = str(tmp_path / "specs" / "123-*" / "checklists" / "*.md")
        with pytest.raises(SystemExit) as exc_info:
            _resolve_paths([pattern], issue_number=123)
        assert exc_info.value.code == 1

    def test_3_digit_safety_check_no_marker(self, tmp_path) -> None:
        # Create spec dir without Source Issue marker
        spec_dir = tmp_path / "specs" / "456-feature" / "checklists"
        spec_dir.mkdir(parents=True)
        (spec_dir / "requirements.md").write_text("# Just a title\n")

        pattern = str(tmp_path / "specs" / "456-*" / "checklists" / "*.md")
        with pytest.raises(SystemExit) as exc_info:
            _resolve_paths([pattern], issue_number=456)
        assert exc_info.value.code == 1

    def test_3_digit_safety_check_with_marker(self, tmp_path) -> None:
        # Create spec dir with valid Source Issue marker
        spec_dir = tmp_path / "specs" / "456-feature" / "checklists"
        spec_dir.mkdir(parents=True)
        (spec_dir / "requirements.md").write_text("**Source Issue**: #456\n- [ ] Item\n")

        pattern = str(tmp_path / "specs" / "456-*" / "checklists" / "*.md")
        result = _resolve_paths([pattern], issue_number=456)
        assert len(result) == 1

    def test_non_3_digit_skips_safety_check(self, tmp_path) -> None:
        # Issue number > 999 should skip the 3-digit safety check
        spec_dir = tmp_path / "specs" / "1203-feature" / "checklists"
        spec_dir.mkdir(parents=True)
        (spec_dir / "requirements.md").write_text("# No marker needed\n")

        pattern = str(tmp_path / "specs" / "1203-*" / "checklists" / "*.md")
        result = _resolve_paths([pattern], issue_number=1203)
        assert len(result) == 1
