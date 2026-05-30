"""Tests for validate_test_structure."""

from __future__ import annotations

from agentic_devtools.cli.checks.structure import validate_test_structure


class TestValidateTestStructure:
    """Tests for validate_test_structure."""

    def test_no_unit_dir_returns_empty(self, tmp_path):
        violations = validate_test_structure(tmp_path)
        assert violations == []

    def test_valid_structure(self, tmp_path):
        source_root = tmp_path / "agentic_devtools" / "cli"
        source_root.mkdir(parents=True)
        (source_root / "state.py").write_text("# source")

        unit = tmp_path / "tests" / "unit" / "cli" / "state"
        unit.mkdir(parents=True)
        (tmp_path / "tests" / "unit" / "cli" / "__init__.py").touch()
        (unit / "__init__.py").touch()
        (unit / "test_get_value.py").write_text("# test")

        violations = validate_test_structure(tmp_path)
        assert violations == []

    def test_too_shallow_test(self, tmp_path):
        unit = tmp_path / "tests" / "unit"
        unit.mkdir(parents=True)
        (unit / "test_something.py").write_text("# test")

        violations = validate_test_structure(tmp_path)
        assert len(violations) == 1
        assert "too shallow" in violations[0]

    def test_no_matching_source_file(self, tmp_path):
        (tmp_path / "agentic_devtools").mkdir()
        unit = tmp_path / "tests" / "unit" / "nonexistent"
        unit.mkdir(parents=True)
        (unit / "__init__.py").touch()
        (unit / "test_func.py").write_text("# test")

        violations = validate_test_structure(tmp_path)
        assert len(violations) == 1
        assert "no matching source file" in violations[0]

    def test_missing_init_py(self, tmp_path):
        source_root = tmp_path / "agentic_devtools"
        source_root.mkdir()
        (source_root / "mymod.py").write_text("# source")

        unit = tmp_path / "tests" / "unit" / "mymod"
        unit.mkdir(parents=True)
        # Deliberately no __init__.py in unit/mymod/
        (unit / "test_func.py").write_text("# test")

        violations = validate_test_structure(tmp_path)
        init_violations = [v for v in violations if "missing __init__.py" in v]
        assert len(init_violations) >= 1

    def test_defaults_to_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        violations = validate_test_structure()
        assert violations == []
