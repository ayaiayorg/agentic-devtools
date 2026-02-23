"""Tests for agentic_devtools.state.get_state_dir."""

from unittest.mock import MagicMock, patch

from agentic_devtools import state


class TestStateDirResolution:
    """Tests for state directory resolution edge cases."""

    def test_env_var_state_dir(self, tmp_path):
        """Test that DFLY_AI_HELPERS_STATE_DIR environment variable is used."""
        custom_dir = tmp_path / "custom_state"
        with patch.dict("os.environ", {"DFLY_AI_HELPERS_STATE_DIR": str(custom_dir)}):
            result = state.get_state_dir()
            assert result == custom_dir
            assert custom_dir.exists()

    def test_finds_existing_scripts_temp(self, tmp_path, monkeypatch):
        """Test that existing scripts/temp is found and used."""
        project_dir = tmp_path / "project"
        scripts_temp = project_dir / "scripts" / "temp"
        scripts_temp.mkdir(parents=True)

        work_dir = project_dir / "src" / "app"
        work_dir.mkdir(parents=True)

        monkeypatch.chdir(work_dir)
        monkeypatch.delenv("DFLY_AI_HELPERS_STATE_DIR", raising=False)

        result = state.get_state_dir()
        assert result == scripts_temp

    def test_fallback_dir_when_no_scripts_temp(self, tmp_path, monkeypatch):
        """Test fallback to .agdt-temp when scripts/temp not found."""
        isolated_dir = tmp_path / "isolated"
        isolated_dir.mkdir()

        monkeypatch.chdir(isolated_dir)
        monkeypatch.delenv("DFLY_AI_HELPERS_STATE_DIR", raising=False)

        result = state.get_state_dir()
        assert result.name == ".agdt-temp"
        assert result.exists()

    def test_scripts_dir_creates_temp(self, tmp_path, monkeypatch):
        """Test that temp is created when inside scripts directory."""
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()

        monkeypatch.chdir(scripts_dir)
        monkeypatch.delenv("DFLY_AI_HELPERS_STATE_DIR", raising=False)

        result = state.get_state_dir()
        assert result == scripts_dir / "temp"
        assert result.exists()

    def test_creates_temp_when_scripts_exists_but_temp_missing(self, tmp_path, monkeypatch):
        """Test that scripts/temp is created when scripts exists but temp doesn't."""
        project_dir = tmp_path / "project"
        scripts_dir = project_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        (scripts_dir / "some_helper.py").touch()

        work_dir = project_dir / "src" / "app"
        work_dir.mkdir(parents=True)

        monkeypatch.chdir(work_dir)
        monkeypatch.delenv("DFLY_AI_HELPERS_STATE_DIR", raising=False)

        result = state.get_state_dir()
        expected_temp = scripts_dir / "temp"
        assert result == expected_temp
        assert expected_temp.exists(), "scripts/temp should be created automatically"


class TestGetStateDirWithGit:
    """Tests for get_state_dir using git-based detection."""

    def test_uses_git_repo_root_when_available(self, tmp_path):
        """Test that get_state_dir uses git repo root when available."""
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()

                assert result == tmp_path / "scripts" / "temp"
                assert result.exists()

    def test_falls_back_to_dfly_temp_when_no_scripts_dir(self, tmp_path):
        """Test that get_state_dir falls back to .agdt-temp when no scripts dir found."""
        subdir = tmp_path / "deep" / "nested" / "path"
        subdir.mkdir(parents=True)

        with patch.object(state, "_get_git_repo_root", return_value=None):
            with patch.dict("os.environ", {}, clear=True):
                with patch("pathlib.Path.cwd", return_value=subdir):
                    result = state.get_state_dir()

                    assert ".agdt-temp" in str(result)

    def test_env_var_takes_precedence_over_git(self, tmp_path):
        """Test that DFLY_AI_HELPERS_STATE_DIR env var takes precedence."""
        env_dir = tmp_path / "custom_state"

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path / "repo"):
            with patch.dict("os.environ", {"DFLY_AI_HELPERS_STATE_DIR": str(env_dir)}):
                result = state.get_state_dir()

                assert result == env_dir
                assert result.exists()

    def test_git_root_without_scripts_dir_falls_back(self, tmp_path):
        """Test fallback when git root exists but has no scripts directory."""
        git_root = tmp_path / "repo_no_scripts"
        git_root.mkdir()

        cwd = tmp_path / "cwd"
        cwd.mkdir()

        with patch.object(state, "_get_git_repo_root", return_value=git_root):
            with patch.dict("os.environ", {}, clear=True):
                with patch("pathlib.Path.cwd", return_value=cwd):
                    result = state.get_state_dir()

                    assert ".agdt-temp" in str(result)


class TestGetGitRepoRoot:
    """Tests for _get_git_repo_root function (called by get_state_dir)."""

    def test_returns_path_when_in_git_repo(self, tmp_path):
        """Test returns Path when git command succeeds."""
        with patch("agentic_devtools.state.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = str(tmp_path) + "\n"
            mock_run.return_value = mock_result

            result = state._get_git_repo_root()

            assert result == tmp_path
            mock_run.assert_called_once_with(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_returns_none_when_not_in_git_repo(self):
        """Test returns None when git command fails (not in repo)."""
        with patch("agentic_devtools.state.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 128
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            result = state._get_git_repo_root()

            assert result is None

    def test_returns_none_when_git_not_found(self):
        """Test returns None when git command is not found."""
        with patch("agentic_devtools.state.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git not found")

            result = state._get_git_repo_root()

            assert result is None

    def test_returns_none_on_os_error(self):
        """Test returns None when OSError occurs."""
        with patch("agentic_devtools.state.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Permission denied")

            result = state._get_git_repo_root()

            assert result is None

    def test_returns_none_when_stdout_empty(self):
        """Test returns None when git returns empty stdout."""
        with patch("agentic_devtools.state.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "   \n"
            mock_run.return_value = mock_result

            result = state._get_git_repo_root()

            assert result is None
