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


class TestGetStateDirBootstrap:
    """Tests for bootstrap-based resolution (.agdt/workflows/{identity}/{worktree_key}/)."""

    def test_bootstrap_scoped_path(self, tmp_path):
        """With valid bootstrap → .agdt/workflows/{identity}/{worktree_key}/."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_text(
            json.dumps({"identity": "ama", "worktree_key": "PROJECT-1234"}),
            encoding="utf-8",
        )
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()

                expected = tmp_path / ".agdt" / "workflows" / "ama" / "PROJECT-1234"
                assert result == expected
                assert result.exists()

    def test_identity_json_used_for_scoped_path(self, tmp_path):
        """Identity from identity.json + worktree_key from bootstrap → scoped path."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        # identity.json holds identity; bootstrap holds only worktree_key
        (agdt_dir / "identity.json").write_text(json.dumps({"identity": "ama", "email": "a@b.com"}), encoding="utf-8")
        (agdt_dir / "runtime-bootstrap.json").write_text(json.dumps({"worktree_key": "PROJECT-1234"}), encoding="utf-8")
        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()

                expected = tmp_path / ".agdt" / "workflows" / "ama" / "PROJECT-1234"
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
        (agdt_dir / "runtime-bootstrap.json").write_text(json.dumps({"worktree_key": "PROJECT-1234"}), encoding="utf-8")
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


class TestGetStateDirPinFile:
    """Tests for pin file resolution (step 2 in priority chain)."""

    def _write_pin(self, git_root, state_dir, workflow="pull-request-review", ttl_hours=24, created_utc=None):
        """Helper to write a pin file."""
        import json
        from datetime import datetime, timezone

        agdt_dir = git_root / ".agdt"
        agdt_dir.mkdir(parents=True, exist_ok=True)
        if created_utc is None:
            created_utc = datetime.now(timezone.utc).isoformat()
        data = {
            "state_dir": str(state_dir),
            "workflow": workflow,
            "created_utc": created_utc,
            "ttl_hours": ttl_hours,
        }
        (agdt_dir / state.PIN_FILENAME).write_text(json.dumps(data), encoding="utf-8")

    def test_valid_pin_honored_as_step_2(self, tmp_path):
        """Valid pin file is used when env var is not set."""
        state._pin_logged = False
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-123"
        state_dir.mkdir(parents=True)
        self._write_pin(tmp_path, state_dir)

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                result = state.get_state_dir()
                assert result == state_dir

    def test_env_var_takes_priority_over_pin(self, tmp_path):
        """Env var must bypass pin file (step 1 > step 2)."""
        state._pin_logged = False
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-123"
        state_dir.mkdir(parents=True)
        self._write_pin(tmp_path, state_dir)

        custom_dir = tmp_path / "env_override"
        with patch.dict("os.environ", {"AGENTIC_DEVTOOLS_STATE_DIR": str(custom_dir)}, clear=True):
            result = state.get_state_dir()
            assert result == custom_dir
            assert result != state_dir

    def test_expired_pin_falls_through_to_bootstrap(self, tmp_path):
        """Expired pin falls through to bootstrap resolution."""
        import json
        from datetime import datetime, timedelta, timezone

        state._pin_logged = False
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-123"
        state_dir.mkdir(parents=True)
        expired = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        self._write_pin(tmp_path, state_dir, created_utc=expired)

        # Set up bootstrap to return a different path
        agdt_dir = tmp_path / ".agdt"
        (agdt_dir / "runtime-bootstrap.json").write_text(
            json.dumps({"identity": "ama", "worktree_key": "OTHER-KEY"}),
            encoding="utf-8",
        )

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                with patch.object(state, "_read_identity_cache", return_value={"identity": "ama"}):
                    result = state.get_state_dir()
                    # Should resolve via bootstrap, not pin
                    expected = tmp_path / ".agdt" / "workflows" / "ama" / "OTHER-KEY"
                    assert result == expected

    def test_no_pin_uses_bootstrap_unchanged(self, tmp_path):
        """Without pin file, bootstrap chain works as before."""
        import json

        state._pin_logged = False
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        (agdt_dir / "runtime-bootstrap.json").write_text(
            json.dumps({"identity": "ama", "worktree_key": "PROJ-456"}),
            encoding="utf-8",
        )

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {}, clear=True):
                with patch.object(state, "_read_identity_cache", return_value={"identity": "ama"}):
                    result = state.get_state_dir()
                    expected = tmp_path / ".agdt" / "workflows" / "ama" / "PROJ-456"
                    assert result == expected

    def test_empty_env_var_treated_as_unset(self, tmp_path):
        """Empty AGENTIC_DEVTOOLS_STATE_DIR falls through to pin/bootstrap."""

        state._pin_logged = False
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-1"
        state_dir.mkdir(parents=True)
        self._write_pin(tmp_path, state_dir)

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {"AGENTIC_DEVTOOLS_STATE_DIR": ""}, clear=True):
                result = state.get_state_dir()
                # Pin should be honored since env var is empty
                assert result == state_dir

    def test_whitespace_only_env_var_treated_as_unset(self, tmp_path):
        """Whitespace-only AGENTIC_DEVTOOLS_STATE_DIR falls through to pin/bootstrap."""

        state._pin_logged = False
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-1"
        state_dir.mkdir(parents=True)
        self._write_pin(tmp_path, state_dir)

        with patch.object(state, "_get_git_repo_root", return_value=tmp_path):
            with patch.dict("os.environ", {"AGENTIC_DEVTOOLS_STATE_DIR": "   "}, clear=True):
                result = state.get_state_dir()
                # Pin should be honored since whitespace-only env var is treated as unset
                assert result == state_dir


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
