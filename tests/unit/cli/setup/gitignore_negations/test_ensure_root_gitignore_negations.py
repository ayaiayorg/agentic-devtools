"""Tests for ``ensure_root_gitignore_negations`` in ``gitignore_negations``."""

from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_devtools.cli.setup.gitignore_negations import ensure_root_gitignore_negations


class TestEnsureRootGitignoreNegations:
    """Tests for inserting negation rules into root .gitignore."""

    def test_inserts_negations_after_agdt_rule(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("node_modules/\n.agdt/\n*.log\n")

        result = ensure_root_gitignore_negations(tmp_path)

        assert result is True
        content = gitignore.read_text()
        assert "!.agdt/config/" in content
        assert "!.agdt/config/project.json" in content
        # Negations should appear after .agdt/ line
        lines = content.splitlines()
        agdt_idx = lines.index(".agdt/")
        assert lines[agdt_idx + 1] == "!.agdt/config/"
        assert lines[agdt_idx + 2] == "!.agdt/config/project.json"

    def test_idempotent_when_already_present(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".agdt/\n!.agdt/config/\n!.agdt/config/project.json\n")

        result = ensure_root_gitignore_negations(tmp_path)

        assert result is False

    def test_returns_false_when_no_gitignore(self, tmp_path: Path) -> None:
        result = ensure_root_gitignore_negations(tmp_path)
        assert result is False

    def test_returns_false_when_no_agdt_rule(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("node_modules/\n*.log\n")

        result = ensure_root_gitignore_negations(tmp_path)
        assert result is False

    def test_partial_negation_rules_already_present(self, tmp_path: Path) -> None:
        """Only missing negation rules should be added."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".agdt/\n!.agdt/config/\n")

        result = ensure_root_gitignore_negations(tmp_path)

        assert result is True
        content = gitignore.read_text()
        lines = content.splitlines()
        # !.agdt/config/ should appear exactly once (not duplicated)
        assert lines.count("!.agdt/config/") == 1
        assert "!.agdt/config/project.json" in lines

    def test_handles_agdt_without_trailing_slash(self, tmp_path: Path) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".agdt\n")

        result = ensure_root_gitignore_negations(tmp_path)

        assert result is True
        content = gitignore.read_text()
        assert "!.agdt/config/" in content

    def test_file_permissions_error(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".agdt/\n")
        gitignore.chmod(0o000)

        try:
            result = ensure_root_gitignore_negations(tmp_path)
            assert result is False
        finally:
            gitignore.chmod(0o644)

    def test_read_oserror_returns_false(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Returns False and warns when .gitignore cannot be read."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".agdt/\n")

        import builtins

        _real_open = builtins.open

        def _failing_open(path, *args, **kwargs):
            if str(path) == str(gitignore):
                raise OSError("permission denied")
            return _real_open(path, *args, **kwargs)  # pragma: no cover

        with patch("builtins.open", side_effect=_failing_open):
            result = ensure_root_gitignore_negations(tmp_path)

        assert result is False
        assert "Cannot read" in capsys.readouterr().err

    def test_write_oserror_returns_false(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Returns False and warns when .gitignore cannot be written."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".agdt/\n")

        import builtins

        _real_open = builtins.open
        _call_count = 0

        def _failing_write_open(path, *args, **kwargs):
            nonlocal _call_count
            if str(path) == str(gitignore):
                _call_count += 1
                if _call_count > 1:
                    raise OSError("permission denied")
            return _real_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=_failing_write_open):
            result = ensure_root_gitignore_negations(tmp_path)

        assert result is False
        assert "Cannot write" in capsys.readouterr().err

    def test_agdt_line_without_trailing_newline(self, tmp_path: Path) -> None:
        """Handles .agdt/ line without trailing newline (last line of file)."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".agdt/")  # No trailing newline

        result = ensure_root_gitignore_negations(tmp_path)

        assert result is True
        content = gitignore.read_text()
        assert "!.agdt/config/" in content
        # Verify the .agdt/ line got a newline appended
        lines = content.splitlines()
        assert ".agdt/" in lines

    def test_partial_negation_preserves_ordering(self, tmp_path: Path) -> None:
        """When !.agdt/config/ exists after .agdt/, file negation is inserted after it."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".agdt/\nsome_other_rule/\n!.agdt/config/\n")

        result = ensure_root_gitignore_negations(tmp_path)

        assert result is True
        lines = gitignore.read_text().splitlines()
        dir_idx = lines.index("!.agdt/config/")
        file_idx = lines.index("!.agdt/config/project.json")
        # File negation must come after directory negation
        assert file_idx == dir_idx + 1

    def test_dir_negation_before_agdt_rule_inserts_after_agdt(self, tmp_path: Path) -> None:
        """When !.agdt/config/ appears before .agdt/, both negations are re-inserted after .agdt/."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("!.agdt/config/\n.agdt/\n*.log\n")

        result = ensure_root_gitignore_negations(tmp_path)

        assert result is True
        lines = gitignore.read_text().splitlines()
        agdt_idx = lines.index(".agdt/")
        # Both negation rules must appear after the .agdt/ rule so they
        # are effective.  The original misplaced !.agdt/config/ remains
        # (harmless duplicate) but new copies are inserted after .agdt/.
        dir_indices = [i for i, line in enumerate(lines) if line == "!.agdt/config/"]
        assert any(i > agdt_idx for i in dir_indices), "!.agdt/config/ must appear after .agdt/"
        file_idx = lines.index("!.agdt/config/project.json")
        assert file_idx > agdt_idx

    def test_out_of_order_negations_reordered(self, tmp_path: Path) -> None:
        """When file negation appears before dir negation after .agdt/, reorders them."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".agdt/\n!.agdt/config/project.json\n!.agdt/config/\n")

        result = ensure_root_gitignore_negations(tmp_path)

        assert result is True
        lines = gitignore.read_text().splitlines()
        dir_idx = lines.index("!.agdt/config/")
        file_idx = lines.index("!.agdt/config/project.json")
        # Directory negation must appear before file negation
        assert dir_idx < file_idx

    def test_out_of_order_with_duplicate_file_negation(self, tmp_path: Path) -> None:
        """When duplicate file negation lines exist in wrong order, fixes ordering."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".agdt/\n!.agdt/config/project.json\n!.agdt/config/project.json\n!.agdt/config/\n")

        result = ensure_root_gitignore_negations(tmp_path)

        assert result is True
        lines = gitignore.read_text().splitlines()
        dir_idx = lines.index("!.agdt/config/")
        # At least one file negation must appear after the directory negation
        file_indices = [i for i, line in enumerate(lines) if line == "!.agdt/config/project.json"]
        assert any(fi > dir_idx for fi in file_indices)

    def test_both_negations_before_agdt_rule_reinserted(self, tmp_path: Path) -> None:
        """When both negation rules appear before .agdt/, they are re-inserted after it."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("!.agdt/config/\n!.agdt/config/project.json\n.agdt/\n")

        result = ensure_root_gitignore_negations(tmp_path)

        assert result is True
        lines = gitignore.read_text().splitlines()
        agdt_idx = lines.index(".agdt/")
        # Effective copies must exist after .agdt/
        after_agdt = lines[agdt_idx + 1 :]
        assert "!.agdt/config/" in after_agdt
        assert "!.agdt/config/project.json" in after_agdt

    def test_handles_agdt_wildcard_anchor(self, tmp_path: Path) -> None:
        """Recognises .agdt/* as an anchor line (from gitignore_updater)."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("node_modules/\n.agdt/*\n*.log\n")

        result = ensure_root_gitignore_negations(tmp_path)

        assert result is True
        content = gitignore.read_text()
        lines = content.splitlines()
        agdt_idx = lines.index(".agdt/*")
        assert lines[agdt_idx + 1] == "!.agdt/config/"
        assert lines[agdt_idx + 2] == "!.agdt/config/project.json"

    def test_crlf_line_endings_preserved(self, tmp_path: Path) -> None:
        """Inserted negation rules use CRLF when the file uses CRLF."""
        gitignore = tmp_path / ".gitignore"
        with open(gitignore, "w", encoding="utf-8", newline="") as fh:
            fh.write("node_modules/\r\n.agdt/\r\n*.log\r\n")

        result = ensure_root_gitignore_negations(tmp_path)

        assert result is True
        with open(gitignore, encoding="utf-8", newline="") as fh:
            raw = fh.read()
        # All inserted lines should use CRLF, no bare LF
        assert "!.agdt/config/\r\n" in raw
        assert "!.agdt/config/project.json\r\n" in raw
        # No mixed endings — every line should end with \r\n
        for line in raw.splitlines(keepends=True):
            if line.strip():
                assert line.endswith("\r\n"), f"Mixed endings: {line!r}"

    def test_crlf_no_trailing_newline(self, tmp_path: Path) -> None:
        """Handles CRLF file where .agdt/ line has no trailing newline."""
        gitignore = tmp_path / ".gitignore"
        with open(gitignore, "w", encoding="utf-8", newline="") as fh:
            fh.write(".agdt/")

        result = ensure_root_gitignore_negations(tmp_path)

        assert result is True
        with open(gitignore, encoding="utf-8", newline="") as fh:
            raw = fh.read()
        assert "!.agdt/config/" in raw
        assert "!.agdt/config/project.json" in raw
