"""Tests for check_all_dependencies."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.setup import dependency_checker
from agentic_devtools.cli.setup.dependency_checker import DependencyStatus, check_all_dependencies


class TestCheckAllDependencies:
    """Tests for check_all_dependencies."""

    def test_returns_list_of_dependency_statuses(self):
        """Returns a list of DependencyStatus objects."""
        with patch.object(dependency_checker, "_find_binary", return_value=None):
            result = check_all_dependencies()
        assert isinstance(result, list)
        assert all(isinstance(s, DependencyStatus) for s in result)

    def test_includes_all_expected_tools(self):
        """Reports status for copilot, gh, git, az, and code."""
        with patch.object(dependency_checker, "_find_binary", return_value=None):
            result = check_all_dependencies()
        names = [s.name for s in result]
        assert "copilot" in names
        assert "gh" in names
        assert "git" in names
        assert "az" in names
        assert "code" in names

    def test_git_is_required(self):
        """git is marked as required."""
        with patch.object(dependency_checker, "_find_binary", return_value=None):
            result = check_all_dependencies()
        git_status = next(s for s in result if s.name == "git")
        assert git_status.required is True

    def test_copilot_and_gh_are_not_required(self):
        """copilot and gh are not strictly required."""
        with patch.object(dependency_checker, "_find_binary", return_value=None):
            result = check_all_dependencies()
        for name in ("copilot", "gh"):
            status = next(s for s in result if s.name == name)
            assert status.required is False

    def test_found_when_binary_on_path(self, tmp_path):
        """found=True when binary is detected on PATH."""
        fake_git = tmp_path / "git"
        fake_git.touch()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "git version 2.43.0\n"

        with patch.object(
            dependency_checker,
            "_find_binary",
            side_effect=lambda n: str(fake_git) if n == "git" else None,
        ):
            with patch.object(dependency_checker, "_run_version", return_value="git version 2.43.0"):
                result = check_all_dependencies()
        git_status = next(s for s in result if s.name == "git")
        assert git_status.found is True
        assert git_status.path == str(fake_git)

    def test_not_found_when_binary_absent(self):
        """found=False when binary cannot be located."""
        with patch.object(dependency_checker, "_find_binary", return_value=None):
            result = check_all_dependencies()
        for s in result:
            assert s.found is False
