"""Tests for _detect_python_scripts_dir."""

import sys
from unittest.mock import patch

import pytest

from agentic_devtools.cli.workflows.worktree_setup import _detect_python_scripts_dir

_MODULE = "agentic_devtools.cli.workflows.worktree_setup"


class TestDetectPythonScriptsDir:
    """Tests for _detect_python_scripts_dir function."""

    @staticmethod
    def _make_executable(path):
        """Make a test entry-point executable on POSIX hosts."""
        if sys.platform != "win32":
            path.chmod(0o755)

    def test_returns_parent_dir_when_agdt_on_path(self, tmp_path):
        """Returns the parent directory of agdt-advance-workflow when shutil.which finds it."""
        fake_bin = tmp_path / "bin" / "agdt-advance-workflow"
        fake_bin.parent.mkdir(parents=True)
        fake_bin.write_text("", encoding="utf-8")
        self._make_executable(fake_bin)

        with patch(f"{_MODULE}.shutil.which", return_value=str(fake_bin)):
            result = _detect_python_scripts_dir()

        assert result == str(fake_bin.parent)

    def test_resolves_symlinked_which_path_before_deriving_parent(self, tmp_path):
        """Uses os.path.realpath(which_result) so symlinked launchers resolve to the target directory."""
        shim_bin = tmp_path / "shim" / "agdt-advance-workflow"
        target_bin = tmp_path / "target" / "agdt-advance-workflow"
        shim_bin.parent.mkdir(parents=True)
        target_bin.parent.mkdir(parents=True)
        shim_bin.write_text("", encoding="utf-8")
        target_bin.write_text("", encoding="utf-8")
        self._make_executable(shim_bin)
        self._make_executable(target_bin)

        with patch(f"{_MODULE}.shutil.which", return_value=str(shim_bin)):
            with patch(f"{_MODULE}.os.path.realpath", return_value=str(target_bin)):
                result = _detect_python_scripts_dir()

        assert result == str(target_bin.parent)

    def test_returns_agdt_bin_when_which_returns_none(self, tmp_path):
        """Falls back to ~/.agdt/bin when shutil.which returns None and the entry point exists there."""
        fake_bin_dir = tmp_path / ".agdt" / "bin"
        fake_bin_dir.mkdir(parents=True)
        entry_point = "agdt-advance-workflow.exe" if sys.platform == "win32" else "agdt-advance-workflow"
        entry_point_path = fake_bin_dir / entry_point
        entry_point_path.write_text("", encoding="utf-8")
        self._make_executable(entry_point_path)

        def fake_which(name):
            # Only return None for the initial which check
            return None

        with patch(f"{_MODULE}.shutil.which", side_effect=fake_which):
            with patch(f"{_MODULE}.os.path.expanduser", return_value=str(tmp_path)):
                result = _detect_python_scripts_dir()

        assert result == str(fake_bin_dir)

    def test_falls_back_to_sysconfig_scripts_dir(self, tmp_path):
        """Falls back to sysconfig.get_path('scripts') when earlier candidates fail."""
        scripts_dir = tmp_path / "Scripts"
        scripts_dir.mkdir()
        entry_point = "agdt-advance-workflow.exe" if sys.platform == "win32" else "agdt-advance-workflow"
        entry_point_path = scripts_dir / entry_point
        entry_point_path.write_text("", encoding="utf-8")
        self._make_executable(entry_point_path)

        import sysconfig as _sysconfig

        with patch(f"{_MODULE}.shutil.which", return_value=None):
            with patch(f"{_MODULE}.os.path.expanduser", return_value=str(tmp_path / "nohome")):
                with patch.object(_sysconfig, "get_path", return_value=str(scripts_dir)):
                    result = _detect_python_scripts_dir()

        assert result == str(scripts_dir)

    def test_falls_back_to_sys_executable_parent(self, tmp_path):
        """Falls back to the parent directory of sys.executable when earlier candidates fail."""
        exe_dir = tmp_path / "python_dir"
        exe_dir.mkdir()
        entry_point = "agdt-advance-workflow.exe" if sys.platform == "win32" else "agdt-advance-workflow"
        entry_point_path = exe_dir / entry_point
        entry_point_path.write_text("", encoding="utf-8")
        self._make_executable(entry_point_path)

        import sysconfig as _sysconfig

        with patch(f"{_MODULE}.shutil.which", return_value=None):
            with patch(f"{_MODULE}.os.path.expanduser", return_value=str(tmp_path / "nohome")):
                with patch.object(_sysconfig, "get_path", return_value=str(tmp_path / "nonexistent_scripts")):
                    with patch(f"{_MODULE}.sys.executable", str(exe_dir / "python")):
                        result = _detect_python_scripts_dir()

        assert result == str(exe_dir)

    def test_windows_falls_back_to_scripts_sibling(self, tmp_path):
        """On Windows, <exe_dir>/Scripts is checked when exe_dir itself has no entry point."""
        exe_dir = tmp_path / "python_dir"
        exe_dir.mkdir()
        scripts_dir = exe_dir / "Scripts"
        scripts_dir.mkdir()
        # The entry point lives only in Scripts/, not in exe_dir itself.
        entry_point_path = scripts_dir / "agdt-advance-workflow.exe"
        entry_point_path.write_text("", encoding="utf-8")
        self._make_executable(entry_point_path)

        import sysconfig as _sysconfig

        with patch(f"{_MODULE}.sys.platform", "win32"):
            with patch(f"{_MODULE}.shutil.which", return_value=None):
                with patch(f"{_MODULE}.os.path.expanduser", return_value=str(tmp_path / "nohome")):
                    with patch.object(_sysconfig, "get_path", return_value=str(tmp_path / "nonexistent")):
                        with patch(f"{_MODULE}.sys.executable", str(exe_dir / "python.exe")):
                            result = _detect_python_scripts_dir()

        assert result == str(scripts_dir)

    def test_returns_none_when_no_candidate_has_entry_point(self, tmp_path):
        """Returns None when none of the candidate directories contain agdt-advance-workflow."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        import sysconfig as _sysconfig

        with patch(f"{_MODULE}.shutil.which", return_value=None):
            with patch(f"{_MODULE}.os.path.expanduser", return_value=str(tmp_path / "nohome")):
                with patch.object(_sysconfig, "get_path", return_value=str(empty_dir)):
                    with patch(f"{_MODULE}.sys.executable", str(empty_dir / "python")):
                        result = _detect_python_scripts_dir()

        assert result is None

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only .exe suffix test")
    def test_windows_finds_exe_suffix(self, tmp_path):
        """On Windows, detects agdt-advance-workflow.exe in the Scripts directory."""
        scripts_dir = tmp_path / "Scripts"
        scripts_dir.mkdir()
        entry_point_path = scripts_dir / "agdt-advance-workflow.exe"
        entry_point_path.write_text("", encoding="utf-8")
        self._make_executable(entry_point_path)

        import sysconfig as _sysconfig

        with patch(f"{_MODULE}.shutil.which", return_value=None):
            with patch(f"{_MODULE}.os.path.expanduser", return_value=str(tmp_path / "nohome")):
                with patch.object(_sysconfig, "get_path", return_value=str(scripts_dir)):
                    result = _detect_python_scripts_dir()

        assert result == str(scripts_dir)

    @pytest.mark.skipif(sys.platform == "win32", reason="Non-Windows test")
    def test_non_windows_finds_entry_point_without_exe(self, tmp_path):
        """On non-Windows, detects agdt-advance-workflow (no .exe) in the Scripts directory."""
        scripts_dir = tmp_path / "bin"
        scripts_dir.mkdir()
        entry_point_path = scripts_dir / "agdt-advance-workflow"
        entry_point_path.write_text("", encoding="utf-8")
        self._make_executable(entry_point_path)

        import sysconfig as _sysconfig

        with patch(f"{_MODULE}.shutil.which", return_value=None):
            with patch(f"{_MODULE}.os.path.expanduser", return_value=str(tmp_path / "nohome")):
                with patch.object(_sysconfig, "get_path", return_value=str(scripts_dir)):
                    result = _detect_python_scripts_dir()

        assert result == str(scripts_dir)

    def test_handles_oserror_in_contains_entry_point(self, tmp_path):
        """Returns None gracefully when os.path.isfile raises OSError inside _contains_entry_point."""
        import sysconfig as _sysconfig

        # Create a real directory so isdir passes, but isfile raises OSError
        candidate_dir = tmp_path / "scripts"
        candidate_dir.mkdir()

        with patch(f"{_MODULE}.shutil.which", return_value=None):
            with patch(f"{_MODULE}.os.path.expanduser", return_value=str(tmp_path / "nohome")):
                with patch.object(_sysconfig, "get_path", return_value=str(candidate_dir)):
                    with patch(f"{_MODULE}.sys.executable", str(candidate_dir / "python")):
                        with patch(f"{_MODULE}.os.path.isfile", side_effect=OSError("permission denied")):
                            result = _detect_python_scripts_dir()

        assert result is None

    def test_handles_sysconfig_exception(self, tmp_path):
        """Returns None gracefully when sysconfig.get_path raises an exception."""
        import sysconfig as _sysconfig

        with patch(f"{_MODULE}.shutil.which", return_value=None):
            with patch(f"{_MODULE}.os.path.expanduser", return_value=str(tmp_path / "nohome")):
                with patch.object(_sysconfig, "get_path", side_effect=Exception("sysconfig error")):
                    with patch(f"{_MODULE}.sys.executable", ""):
                        result = _detect_python_scripts_dir()

        assert result is None

    def test_handles_oserror_in_outer_isdir_loop(self, tmp_path):
        """Returns None gracefully when os.path.isdir raises OSError for a candidate."""
        import sysconfig as _sysconfig

        candidate_dir = tmp_path / "scripts"

        with patch(f"{_MODULE}.shutil.which", return_value=None):
            with patch(f"{_MODULE}.os.path.expanduser", return_value=str(tmp_path / "nohome")):
                with patch.object(_sysconfig, "get_path", return_value=str(candidate_dir)):
                    with patch(f"{_MODULE}.sys.executable", ""):
                        with patch(f"{_MODULE}.os.path.isdir", side_effect=OSError("permission denied")):
                            result = _detect_python_scripts_dir()

        assert result is None

    def test_windows_contains_entry_point_returns_true_without_access_check(self, tmp_path):
        """When os.name is nt, finding the .exe file returns True without requiring os.access."""
        fake_bin_dir = tmp_path / ".agdt" / "bin"
        fake_bin_dir.mkdir(parents=True)
        entry_point_path = fake_bin_dir / "agdt-advance-workflow.exe"
        entry_point_path.write_text("", encoding="utf-8")

        with patch(f"{_MODULE}.sys.platform", "win32"):
            with patch(f"{_MODULE}.os.name", "nt"):
                with patch(f"{_MODULE}.shutil.which", return_value=None):
                    with patch(f"{_MODULE}.os.path.expanduser", return_value=str(tmp_path)):
                        with patch(f"{_MODULE}.os.access", return_value=False):
                            result = _detect_python_scripts_dir()

        assert result == str(fake_bin_dir)
