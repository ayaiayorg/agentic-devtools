"""Test build_inventory — pyproject.toml and fallback paths (FR-002, FR-011)."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.speckit.pass_g.inventory import (
    _discover_files,
    build_inventory,
)
from agentic_devtools.cli.speckit.pass_g.models import ReferenceKind


def test_build_inventory_extracts_pyproject_entry_points(tmp_path):
    """Verify build_inventory extracts CLI entry points from pyproject.toml."""
    # Create a minimal Python file
    src = tmp_path / "module.py"
    src.write_text("def main():\n    pass\n")

    # Create pyproject.toml with entry points
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project.scripts]\nagdt-test = "agentic_devtools.cli.runner:run"\n')

    with patch("agentic_devtools.cli.speckit.pass_g.inventory._discover_files") as mock_discover:
        mock_discover.return_value = ["module.py"]
        inv = build_inventory(tmp_path)

    # Should have the CLI entry point
    cli_symbols = [s for s in inv.get_all_symbols() if s.kind == ReferenceKind.CLI_COMMAND]
    assert len(cli_symbols) == 1
    assert cli_symbols[0].name == "agdt-test"


def test_build_inventory_handles_oserror_on_file_read(tmp_path):
    """OSError on reading a Python file is silently skipped."""
    src = tmp_path / "module.py"
    src.write_text("class Foo:\n    pass\n")

    with patch("agentic_devtools.cli.speckit.pass_g.inventory._discover_files") as mock_discover:
        mock_discover.return_value = ["module.py"]
        # Make read_text raise OSError
        with patch.object(Path, "read_text", side_effect=OSError("read error")):
            inv = build_inventory(tmp_path)

    # No symbols extracted due to OSError
    assert inv.get_all_symbols() == []


def test_build_inventory_handles_oserror_on_pyproject(tmp_path):
    """OSError on reading pyproject.toml is silently skipped."""
    src = tmp_path / "module.py"
    src.write_text("def func():\n    pass\n")

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project.scripts]\nagdt-x = "pkg:main"\n')

    with patch("agentic_devtools.cli.speckit.pass_g.inventory._discover_files") as mock_discover:
        mock_discover.return_value = ["module.py"]
        # We need a more nuanced mock: allow module.py to be read but not pyproject.toml
        original_read = Path.read_text

        def mock_read(self, *args, **kwargs):
            if "pyproject" in str(self):
                raise OSError("cannot read")
            return original_read(self, *args, **kwargs)

        with patch.object(Path, "read_text", mock_read):
            inv = build_inventory(tmp_path)

    # Python symbols extracted, but no CLI symbols
    func_symbols = [s for s in inv.get_all_symbols() if s.kind == ReferenceKind.FUNCTION_NAME]
    assert len(func_symbols) == 1
    cli_symbols = [s for s in inv.get_all_symbols() if s.kind == ReferenceKind.CLI_COMMAND]
    assert cli_symbols == []


def test_discover_files_git_fallback(tmp_path):
    """When git ls-files fails, fallback to directory walking."""
    # Create files
    (tmp_path / "a.py").write_text("# a")
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "b.py").write_text("# b")

    with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
        files = _discover_files(tmp_path)

    assert len(files) >= 2
    # Normalize separators for cross-platform
    normalized = [f.replace("\\", "/") for f in files]
    assert "a.py" in normalized
    assert "sub/b.py" in normalized


def test_discover_files_git_nonzero_returncode(tmp_path):
    """When git ls-files returns non-zero, fallback to directory walking."""
    (tmp_path / "c.py").write_text("# c")

    import subprocess

    mock_result = subprocess.CompletedProcess(args=[], returncode=128, stdout="", stderr="not a git repo")
    with patch("subprocess.run", return_value=mock_result):
        files = _discover_files(tmp_path)

    assert "c.py" in files


def test_discover_files_git_timeout(tmp_path):
    """When git ls-files times out, fallback to directory walking."""
    import subprocess

    (tmp_path / "d.py").write_text("# d")

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 30)):
        files = _discover_files(tmp_path)

    assert "d.py" in files


def test_discover_files_git_success(tmp_path):
    """When git ls-files succeeds, return its output directly."""
    import subprocess

    mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="src/main.py\nlib/utils.py\n\n", stderr="")
    with patch("subprocess.run", return_value=mock_result):
        files = _discover_files(tmp_path)

    assert files == ["src/main.py", "lib/utils.py"]


def test_discover_files_rglob_fallback_valueerror(tmp_path):
    """When path.relative_to raises ValueError in rglob fallback, continue."""
    (tmp_path / "valid.py").write_text("# valid")

    import subprocess

    mock_result = subprocess.CompletedProcess(args=[], returncode=128, stdout="", stderr="error")

    # Mock rglob to yield a path that can't be made relative to tmp_path
    outside_path = Path("/some/outside/path.py")

    def mock_rglob(self, pattern):
        # Yield the valid file, then yield the outside path
        yield tmp_path / "valid.py"
        yield outside_path

    with patch("subprocess.run", return_value=mock_result):
        with patch.object(Path, "rglob", mock_rglob):
            # Also need to mock is_file for the outside path
            original_is_file = Path.is_file

            def mock_is_file(self):
                if self == outside_path:
                    return True
                return original_is_file(self)

            with patch.object(Path, "is_file", mock_is_file):
                files = _discover_files(tmp_path)

    # Should have valid.py but not the outside path
    normalized = [f.replace("\\", "/") for f in files]
    assert "valid.py" in normalized
    assert len(files) == 1
