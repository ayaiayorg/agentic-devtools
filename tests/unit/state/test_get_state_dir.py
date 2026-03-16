"""Tests for agentic_devtools.state.get_state_dir."""

from unittest.mock import MagicMock, patch

from agentic_devtools import state


class TestGetStateDirEnvVar:
    """Tests for AGENTIC_DEVTOOLS_STATE_DIR environment variable override."""

    def test_env_var_takes_priority(self, tmp_path):
        """AGENTIC_DEVTOOLS_STATE_DIR must override all other resolution."""
        custom_dir = tmp_path / "custom_state"
        with patch.dict("os.environ", {"AGENTIC_DEVTOOLS_STATE_DIR": str(custom_dir)}, clear=True):
            result = state.get_state_dir()
            assert result == custom_dir
            assert custom_dir.exists()

    def test_dfly_env_var_legacy_alias(self, tmp_path):
        """DFLY_AI_HELPERS_STATE_DIR must be honored as a legacy alias."""
        custom_dir = tmp_path / "legacy_dir"
        with patch.dict(
            "os.environ",
            {"DFLY_AI_HELPERS_STATE_DIR": str(custom_dir)},
            clear=True,
        ):
            result = state.get_state_dir()
            assert result == custom_dir
            assert custom_dir.exists()

    def test_agentic_env_var_takes_priority_over_dfly(self, tmp_path):
        """AGENTIC_DEVTOOLS_STATE_DIR takes priority over DFLY_AI_HELPERS_STATE_DIR."""
        primary_dir = tmp_path / "primary"
        legacy_dir = tmp_path / "legacy"
        with patch.dict(
            "os.environ",
            {
                "AGENTIC_DEVTOOLS_STATE_DIR": str(primary_dir),
                "DFLY_AI_HELPERS_STATE_DIR": str(legacy_dir),
            },
            clear=True,
        ):
            result = state.get_state_dir()
            assert result == primary_dir
            assert primary_dir.exists()
            assert not legacy_dir.exists()


class TestGetStateDirBootstrap:
    """Tests for bootstrap-based resolution (.agdt/workflows/{identity}/{worktree_key}/)."""

    def test_bootstrap_scoped_path(self, tmp_path):
        """With valid bootstrap → .agdt/workflows/{identity}/{worktree_key}/."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_text(
            json.dumps({"identity": "ama", "worktree_key": "DFLY-1234"}),
            encoding="utf-8",
        )
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()

                expected = tmp_path / ".agdt" / "workflows" / "ama" / "DFLY-1234"
                assert result == expected
                assert result.exists()

    def test_unscoped_fallback_no_bootstrap(self, tmp_path):
        """No bootstrap file → .agdt/workflows/_unscoped/."""
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()

                expected = tmp_path / ".agdt" / "workflows" / "_unscoped"
                assert result == expected
                assert result.exists()

    def test_unscoped_fallback_partial_bootstrap_identity_only(self, tmp_path):
        """Bootstrap with only identity (no worktree_key) → _unscoped."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_text(json.dumps({"identity": "ama"}), encoding="utf-8")
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()

                assert result == tmp_path / ".agdt" / "workflows" / "_unscoped"

    def test_unscoped_fallback_partial_bootstrap_worktree_only(self, tmp_path):
        """Bootstrap with only worktree_key (no identity) → _unscoped."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_text(json.dumps({"worktree_key": "DFLY-1234"}), encoding="utf-8")
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()

                assert result == tmp_path / ".agdt" / "workflows" / "_unscoped"

    def test_unscoped_fallback_empty_strings(self, tmp_path):
        """Bootstrap with empty string values → _unscoped."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_text(
            json.dumps({"identity": "", "worktree_key": ""}), encoding="utf-8"
        )
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()

                assert result == tmp_path / ".agdt" / "workflows" / "_unscoped"

    def test_unscoped_fallback_malformed_json(self, tmp_path):
        """Bootstrap with malformed JSON → _unscoped."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_text("not json", encoding="utf-8")
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()

                assert result == tmp_path / ".agdt" / "workflows" / "_unscoped"

    def test_unscoped_fallback_invalid_encoding(self, tmp_path):
        """Bootstrap with invalid UTF-8 bytes → _unscoped."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_bytes(b"\x80\x81\x82\x83")
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()

                assert result == tmp_path / ".agdt" / "workflows" / "_unscoped"

    def test_unscoped_fallback_non_dict_json(self, tmp_path):
        """Bootstrap with non-dict JSON → _unscoped."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()

                assert result == tmp_path / ".agdt" / "workflows" / "_unscoped"

    def test_unscoped_fallback_non_string_values(self, tmp_path):
        """Bootstrap with non-string identity/worktree_key → _unscoped (not coerced)."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_text(
            json.dumps({"identity": 123, "worktree_key": True}), encoding="utf-8"
        )
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()

                assert result == tmp_path / ".agdt" / "workflows" / "_unscoped"

    def test_unscoped_fallback_whitespace_only_values(self, tmp_path):
        """Bootstrap with whitespace-only identity/worktree_key → _unscoped."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_text(
            json.dumps({"identity": "  ", "worktree_key": "  "}), encoding="utf-8"
        )
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()

                assert result == tmp_path / ".agdt" / "workflows" / "_unscoped"

    def test_creates_directories(self, tmp_path):
        """All returned paths must exist after the call."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_text(
            json.dumps({"identity": "xyz", "worktree_key": "PROJ-99"}),
            encoding="utf-8",
        )
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()
                assert result.exists()
                assert result.is_dir()

    def test_unscoped_fallback_unsafe_identity_dot_dot(self, tmp_path):
        """Bootstrap with '..' in identity must fall back to _unscoped."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_text(
            json.dumps({"identity": "..", "worktree_key": "PR123"}),
            encoding="utf-8",
        )
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()
                expected = tmp_path / ".agdt" / "workflows" / "_unscoped"
                assert result == expected

    def test_unscoped_fallback_unsafe_identity_slash(self, tmp_path):
        """Bootstrap with '/' in identity must fall back to _unscoped."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_text(
            json.dumps({"identity": "foo/bar", "worktree_key": "PR123"}),
            encoding="utf-8",
        )
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()
                expected = tmp_path / ".agdt" / "workflows" / "_unscoped"
                assert result == expected

    def test_unscoped_fallback_unsafe_worktree_key_backslash(self, tmp_path):
        """Bootstrap with backslash in worktree_key must fall back to _unscoped."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_text(
            json.dumps({"identity": "ama", "worktree_key": "foo\\bar"}),
            encoding="utf-8",
        )
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()
                expected = tmp_path / ".agdt" / "workflows" / "_unscoped"
                assert result == expected

    def test_unscoped_fallback_unsafe_identity_drive_letter(self, tmp_path):
        """Bootstrap with Windows drive letter in identity must fall back to _unscoped."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_text(
            json.dumps({"identity": "D:", "worktree_key": "PR123"}),
            encoding="utf-8",
        )
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()
                expected = tmp_path / ".agdt" / "workflows" / "_unscoped"
                assert result == expected


class TestGetStateDirFallback:
    """Tests for the .agdt-temp fallback when not in a git repo."""

    def test_agdt_temp_fallback_no_git(self, tmp_path):
        """Not in a git repo → CWD / .agdt-temp."""
        with patch.object(state, "_get_git_repo_root", return_value=None):
            with patch.dict("os.environ", {}, clear=True):
                with patch("pathlib.Path.cwd", return_value=tmp_path):
                    result = state.get_state_dir()

                    assert result == tmp_path / ".agdt-temp"
                    assert result.exists()


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
