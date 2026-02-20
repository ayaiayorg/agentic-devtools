"""Tests for scripts/scaffold_tests.py."""

from __future__ import annotations

import importlib.util
import textwrap
from pathlib import Path

import pytest

# We import the script directly by path so there is no package dependency.


def _load_scaffold_module():
    """Load scripts/scaffold_tests.py as a module."""
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "scaffold_tests.py"
    spec = importlib.util.spec_from_file_location("scaffold_tests", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load scaffold_tests.py from {script_path!s}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scaffold = _load_scaffold_module()


# ---------------------------------------------------------------------------
# _collect_public_functions
# ---------------------------------------------------------------------------


class TestCollectPublicFunctions:
    def test_returns_public_functions(self, tmp_path):
        src = tmp_path / "sample.py"
        src.write_text(
            textwrap.dedent(
                """\
                def public_one():
                    pass

                def public_two():
                    pass

                def _private():
                    pass
                """
            )
        )
        result = scaffold._collect_public_functions(src)
        assert result == ["public_one", "public_two"]

    def test_excludes_private_functions(self, tmp_path):
        src = tmp_path / "sample.py"
        src.write_text("def _hidden(): pass\n")
        result = scaffold._collect_public_functions(src)
        assert result == []

    def test_excludes_class_methods(self, tmp_path):
        src = tmp_path / "sample.py"
        src.write_text(
            textwrap.dedent(
                """\
                class MyClass:
                    def method(self):
                        pass

                def top_level():
                    pass
                """
            )
        )
        result = scaffold._collect_public_functions(src)
        assert result == ["top_level"]

    def test_handles_async_functions(self, tmp_path):
        src = tmp_path / "sample.py"
        src.write_text("async def async_fn(): pass\n")
        result = scaffold._collect_public_functions(src)
        assert result == ["async_fn"]

    def test_returns_sorted_names(self, tmp_path):
        src = tmp_path / "sample.py"
        src.write_text("def zebra(): pass\ndef alpha(): pass\n")
        result = scaffold._collect_public_functions(src)
        assert result == ["alpha", "zebra"]

    def test_returns_empty_for_syntax_error(self, tmp_path):
        src = tmp_path / "bad.py"
        src.write_text("def (: pass\n")
        result = scaffold._collect_public_functions(src)
        assert result == []

    def test_returns_empty_for_file_with_no_functions(self, tmp_path):
        src = tmp_path / "empty.py"
        src.write_text("X = 1\n")
        result = scaffold._collect_public_functions(src)
        assert result == []


# ---------------------------------------------------------------------------
# _build_import_path
# ---------------------------------------------------------------------------


class TestBuildImportPath:
    def test_top_level_module(self):
        repo_root = scaffold.REPO_ROOT
        source = repo_root / "agentic_devtools" / "state.py"
        result = scaffold._build_import_path(source)
        assert result == "agentic_devtools.state"

    def test_nested_module(self):
        repo_root = scaffold.REPO_ROOT
        source = repo_root / "agentic_devtools" / "cli" / "git" / "core.py"
        result = scaffold._build_import_path(source)
        assert result == "agentic_devtools.cli.git.core"


# ---------------------------------------------------------------------------
# _stub_content
# ---------------------------------------------------------------------------


class TestStubContent:
    def test_content_includes_docstring(self, tmp_path):
        source = tmp_path / "agentic_devtools" / "state.py"
        source.parent.mkdir(parents=True)
        source.write_text("")
        stub = scaffold.TestStub(
            test_file=tmp_path / "tests" / "unit" / "state" / "test_get_value.py",
            source_file=source,
            function_name="get_value",
        )
        # Patch REPO_ROOT in the module so _build_import_path works with tmp_path
        original = scaffold.REPO_ROOT
        scaffold.REPO_ROOT = tmp_path
        try:
            content = scaffold._stub_content(stub)
        finally:
            scaffold.REPO_ROOT = original

        assert "def test_get_value" in content
        assert "raise NotImplementedError" in content
        assert "get_value" in content

    def test_content_has_import(self, tmp_path):
        source = tmp_path / "agentic_devtools" / "mymod.py"
        source.parent.mkdir(parents=True)
        source.write_text("")
        stub = scaffold.TestStub(
            test_file=tmp_path / "tests" / "unit" / "mymod" / "test_do_thing.py",
            source_file=source,
            function_name="do_thing",
        )
        original = scaffold.REPO_ROOT
        scaffold.REPO_ROOT = tmp_path
        try:
            content = scaffold._stub_content(stub)
        finally:
            scaffold.REPO_ROOT = original

        assert "from agentic_devtools.mymod import do_thing" in content


# ---------------------------------------------------------------------------
# collect_all_stubs — integration smoke test
# ---------------------------------------------------------------------------


class TestCollectAllStubs:
    def test_returns_non_empty_list(self):
        stubs = scaffold.collect_all_stubs()
        assert len(stubs) > 0

    def test_stubs_have_correct_types(self):
        stubs = scaffold.collect_all_stubs()
        for stub in stubs[:10]:  # spot-check first 10
            assert isinstance(stub.test_file, Path)
            assert isinstance(stub.source_file, Path)
            assert isinstance(stub.function_name, str)
            assert not stub.function_name.startswith("_")

    def test_test_files_under_unit_dir(self):
        stubs = scaffold.collect_all_stubs()
        unit_dir = scaffold.UNIT_TESTS_DIR
        for stub in stubs[:10]:
            assert stub.test_file.is_relative_to(unit_dir)


# ---------------------------------------------------------------------------
# main / CLI integration
# ---------------------------------------------------------------------------


class TestMain:
    def test_dry_run_exits_zero(self, capsys):
        rc = scaffold.main(["--dry-run"])
        assert rc == 0

    def test_dry_run_prints_output(self, capsys):
        scaffold.main(["--dry-run"])
        captured = capsys.readouterr()
        assert "Dry-run" in captured.out

    def test_generate_creates_files(self, tmp_path, monkeypatch):
        """generate() creates __init__.py and stub files in a temp unit dir."""
        monkeypatch.setattr(scaffold, "UNIT_TESTS_DIR", tmp_path / "unit")
        monkeypatch.setattr(scaffold, "REPO_ROOT", scaffold.REPO_ROOT)

        # Use a minimal stub list to avoid writing hundreds of files
        source = scaffold.REPO_ROOT / "agentic_devtools" / "state.py"
        functions = scaffold._collect_public_functions(source)
        assert functions, "state.py should have public functions"

        func = functions[0]
        test_file = tmp_path / "unit" / "state" / f"test_{func}.py"
        stub = scaffold.TestStub(test_file=test_file, source_file=source, function_name=func)

        scaffold.generate([stub])

        assert test_file.exists()
        content = test_file.read_text()
        assert f"def test_{func}" in content

    def test_generate_skips_existing_files(self, tmp_path, monkeypatch):
        """generate() does not overwrite existing test files."""
        monkeypatch.setattr(scaffold, "UNIT_TESTS_DIR", tmp_path / "unit")

        source = scaffold.REPO_ROOT / "agentic_devtools" / "state.py"
        functions = scaffold._collect_public_functions(source)
        func = functions[0]
        test_file = tmp_path / "unit" / "state" / f"test_{func}.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        (test_file.parent / "__init__.py").write_text("")
        original_content = "# already exists\n"
        test_file.write_text(original_content)

        stub = scaffold.TestStub(test_file=test_file, source_file=source, function_name=func)
        scaffold.generate([stub])

        # Original content must be preserved
        assert test_file.read_text() == original_content

    def test_requires_mode_argument(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            scaffold.main([])
        assert exc_info.value.code != 0
