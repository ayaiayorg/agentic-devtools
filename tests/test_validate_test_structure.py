"""Tests for scripts/validate_test_structure.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    """Load scripts/validate_test_structure.py as a module."""
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "validate_test_structure.py"
    spec = importlib.util.spec_from_file_location("validate_test_structure", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load validate_test_structure.py from {script_path!s}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = _load_module()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_valid_tree(unit_dir: Path, source_root: Path) -> Path:
    """Create a minimal valid 1:1:1 tree and return the test file path."""
    # Source: source_root/mymod.py
    source_file = source_root / "mymod.py"
    source_file.write_text("def do_thing(): pass\n")

    # Test: unit_dir/mymod/test_do_thing.py
    test_dir = unit_dir / "mymod"
    test_dir.mkdir(parents=True)
    (test_dir / "__init__.py").write_text("")
    (unit_dir / "__init__.py").write_text("")
    test_file = test_dir / "test_do_thing.py"
    test_file.write_text("def test_do_thing(): pass\n")
    return test_file


# ---------------------------------------------------------------------------
# validate() — no violations
# ---------------------------------------------------------------------------


class TestValidateNoViolations:
    def test_empty_unit_dir_returns_no_violations(self, tmp_path, monkeypatch):
        unit_dir = tmp_path / "unit"
        unit_dir.mkdir()
        source_root = tmp_path / "src"
        source_root.mkdir()
        monkeypatch.setattr(validator, "UNIT_TESTS_DIR", unit_dir)
        monkeypatch.setattr(validator, "SOURCE_ROOT", source_root)

        violations = validator.validate()

        assert violations == []

    def test_valid_tree_returns_no_violations(self, tmp_path, monkeypatch):
        unit_dir = tmp_path / "unit"
        unit_dir.mkdir()
        source_root = tmp_path / "src"
        source_root.mkdir()
        monkeypatch.setattr(validator, "UNIT_TESTS_DIR", unit_dir)
        monkeypatch.setattr(validator, "SOURCE_ROOT", source_root)

        _make_valid_tree(unit_dir, source_root)

        violations = validator.validate()

        assert violations == []

    def test_nested_module_valid(self, tmp_path, monkeypatch):
        """Test file nested two levels deep maps to a nested source file correctly."""
        unit_dir = tmp_path / "unit"
        unit_dir.mkdir()
        source_root = tmp_path / "src"
        source_root.mkdir()
        monkeypatch.setattr(validator, "UNIT_TESTS_DIR", unit_dir)
        monkeypatch.setattr(validator, "SOURCE_ROOT", source_root)

        # Source: source_root/cli/git/core.py
        nested_src = source_root / "cli" / "git"
        nested_src.mkdir(parents=True)
        (nested_src / "core.py").write_text("def get_branch(): pass\n")

        # Tests: unit_dir/cli/git/core/test_get_branch.py
        test_dir = unit_dir / "cli" / "git" / "core"
        test_dir.mkdir(parents=True)
        for ancestor in [unit_dir, unit_dir / "cli", unit_dir / "cli" / "git", test_dir]:
            (ancestor / "__init__.py").write_text("")
        (test_dir / "test_get_branch.py").write_text("def test_get_branch(): pass\n")

        violations = validator.validate()

        assert violations == []


# ---------------------------------------------------------------------------
# validate() — structural violations
# ---------------------------------------------------------------------------


class TestValidateViolations:
    def test_too_shallow_test_file_reported(self, tmp_path, monkeypatch):
        """A test_*.py directly in unit_dir (1 part) is a violation."""
        unit_dir = tmp_path / "unit"
        unit_dir.mkdir()
        source_root = tmp_path / "src"
        source_root.mkdir()
        monkeypatch.setattr(validator, "UNIT_TESTS_DIR", unit_dir)
        monkeypatch.setattr(validator, "SOURCE_ROOT", source_root)

        (unit_dir / "__init__.py").write_text("")
        (unit_dir / "test_orphan.py").write_text("def test_orphan(): pass\n")

        violations = validator.validate()

        assert len(violations) == 1
        assert "too shallow" in violations[0]

    def test_missing_source_file_reported(self, tmp_path, monkeypatch):
        """Test file whose parent folder has no matching source file is a violation."""
        unit_dir = tmp_path / "unit"
        unit_dir.mkdir()
        source_root = tmp_path / "src"
        source_root.mkdir()
        monkeypatch.setattr(validator, "UNIT_TESTS_DIR", unit_dir)
        monkeypatch.setattr(validator, "SOURCE_ROOT", source_root)

        test_dir = unit_dir / "nonexistent_module"
        test_dir.mkdir()
        (unit_dir / "__init__.py").write_text("")
        (test_dir / "__init__.py").write_text("")
        (test_dir / "test_some_fn.py").write_text("def test_some_fn(): pass\n")

        violations = validator.validate()

        assert any("no matching source file" in v for v in violations)

    def test_missing_init_in_test_dir_reported(self, tmp_path, monkeypatch):
        """A test_*.py directory lacking __init__.py is a violation."""
        unit_dir = tmp_path / "unit"
        unit_dir.mkdir()
        source_root = tmp_path / "src"
        source_root.mkdir()
        monkeypatch.setattr(validator, "UNIT_TESTS_DIR", unit_dir)
        monkeypatch.setattr(validator, "SOURCE_ROOT", source_root)
        monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)

        # Source exists
        (source_root / "mymod.py").write_text("def do_thing(): pass\n")

        # Test dir exists but has NO __init__.py (unit_dir __init__.py is present)
        test_dir = unit_dir / "mymod"
        test_dir.mkdir()
        (unit_dir / "__init__.py").write_text("")
        # deliberately omit (test_dir / "__init__.py")
        (test_dir / "test_do_thing.py").write_text("def test_do_thing(): pass\n")

        violations = validator.validate()

        assert any("missing __init__.py" in v for v in violations)

    def test_missing_init_in_intermediate_dir_reported(self, tmp_path, monkeypatch):
        """An intermediate directory in a nested path lacking __init__.py is a violation."""
        unit_dir = tmp_path / "unit"
        unit_dir.mkdir()
        source_root = tmp_path / "src"
        source_root.mkdir()
        monkeypatch.setattr(validator, "UNIT_TESTS_DIR", unit_dir)
        monkeypatch.setattr(validator, "SOURCE_ROOT", source_root)
        monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)

        # Source: src/cli/core.py
        (source_root / "cli").mkdir()
        (source_root / "cli" / "core.py").write_text("def run(): pass\n")

        # Tests: unit_dir/cli/core/test_run.py — but unit_dir/cli/__init__.py is missing
        test_dir = unit_dir / "cli" / "core"
        test_dir.mkdir(parents=True)
        (unit_dir / "__init__.py").write_text("")
        # deliberately omit (unit_dir / "cli" / "__init__.py")
        (test_dir / "__init__.py").write_text("")
        (test_dir / "test_run.py").write_text("def test_run(): pass\n")

        violations = validator.validate()

        assert any("missing __init__.py" in v for v in violations)

    def test_multiple_violations_all_reported(self, tmp_path, monkeypatch):
        """Multiple bad test files each generate their own violation entry."""
        unit_dir = tmp_path / "unit"
        unit_dir.mkdir()
        source_root = tmp_path / "src"
        source_root.mkdir()
        monkeypatch.setattr(validator, "UNIT_TESTS_DIR", unit_dir)
        monkeypatch.setattr(validator, "SOURCE_ROOT", source_root)

        # Two directories whose source files do not exist
        for name in ("missing_a", "missing_b"):
            d = unit_dir / name
            d.mkdir()
            (unit_dir / "__init__.py").write_text("")
            (d / "__init__.py").write_text("")
            (d / f"test_fn_{name}.py").write_text(f"def test_fn_{name}(): pass\n")

        violations = validator.validate()

        assert len([v for v in violations if "no matching source file" in v]) == 2


# ---------------------------------------------------------------------------
# main() — exit codes
# ---------------------------------------------------------------------------


class TestMain:
    def test_exits_zero_when_no_violations(self, tmp_path, monkeypatch):
        unit_dir = tmp_path / "unit"
        unit_dir.mkdir()
        source_root = tmp_path / "src"
        source_root.mkdir()
        monkeypatch.setattr(validator, "UNIT_TESTS_DIR", unit_dir)
        monkeypatch.setattr(validator, "SOURCE_ROOT", source_root)

        _make_valid_tree(unit_dir, source_root)

        rc = validator.main()

        assert rc == 0

    def test_exits_one_when_violations_exist(self, tmp_path, monkeypatch):
        unit_dir = tmp_path / "unit"
        unit_dir.mkdir()
        source_root = tmp_path / "src"
        source_root.mkdir()
        monkeypatch.setattr(validator, "UNIT_TESTS_DIR", unit_dir)
        monkeypatch.setattr(validator, "SOURCE_ROOT", source_root)

        # Create a test file with no matching source
        d = unit_dir / "no_source"
        d.mkdir()
        (unit_dir / "__init__.py").write_text("")
        (d / "__init__.py").write_text("")
        (d / "test_fn.py").write_text("def test_fn(): pass\n")

        rc = validator.main()

        assert rc == 1

    def test_ok_message_printed_when_clean(self, tmp_path, monkeypatch, capsys):
        unit_dir = tmp_path / "unit"
        unit_dir.mkdir()
        source_root = tmp_path / "src"
        source_root.mkdir()
        monkeypatch.setattr(validator, "UNIT_TESTS_DIR", unit_dir)
        monkeypatch.setattr(validator, "SOURCE_ROOT", source_root)

        _make_valid_tree(unit_dir, source_root)
        validator.main()

        captured = capsys.readouterr()
        assert "OK" in captured.out

    def test_fail_message_printed_when_violations(self, tmp_path, monkeypatch, capsys):
        unit_dir = tmp_path / "unit"
        unit_dir.mkdir()
        source_root = tmp_path / "src"
        source_root.mkdir()
        monkeypatch.setattr(validator, "UNIT_TESTS_DIR", unit_dir)
        monkeypatch.setattr(validator, "SOURCE_ROOT", source_root)

        (unit_dir / "test_orphan.py").write_text("def test_orphan(): pass\n")

        validator.main()

        captured = capsys.readouterr()
        assert "FAIL" in captured.out

    def test_exits_zero_when_unit_dir_missing(self, tmp_path, monkeypatch):
        """If tests/unit/ does not exist, there are no violations."""
        unit_dir = tmp_path / "unit"  # does not exist
        source_root = tmp_path / "src"
        source_root.mkdir()
        monkeypatch.setattr(validator, "UNIT_TESTS_DIR", unit_dir)
        monkeypatch.setattr(validator, "SOURCE_ROOT", source_root)

        rc = validator.main()

        assert rc == 0
