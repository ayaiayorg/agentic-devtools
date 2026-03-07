"""Tests for _persist_env_vars_to_profile."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.setup.commands import _persist_env_vars_to_profile


class TestPersistEnvVarsToProfile:
    """Tests for _persist_env_vars_to_profile."""

    # -- persist_env=False (manual instructions) --

    def test_no_persist_path_only_prints_path_instructions_when_not_on_path(self, capsys):
        """Prints PATH instructions when persist_env=False, path_only=True, and not on PATH."""
        with patch("agentic_devtools.cli.setup.commands._is_managed_bin_on_path", return_value=False):
            _persist_env_vars_to_profile(
                npmrc_path=None,
                unified_path=None,
                persist_env=False,
                overwrite_env=False,
                path_only=True,
            )
        out = capsys.readouterr().out
        assert "PATH" in out

    def test_no_persist_path_only_prints_nothing_when_on_path(self, capsys):
        """Prints nothing when persist_env=False, path_only=True, and already on PATH."""
        with patch("agentic_devtools.cli.setup.commands._is_managed_bin_on_path", return_value=True):
            _persist_env_vars_to_profile(
                npmrc_path=None,
                unified_path=None,
                persist_env=False,
                overwrite_env=False,
                path_only=True,
            )
        out = capsys.readouterr().out
        assert out == ""

    def test_no_persist_prints_manual_instructions(self, capsys):
        """Prints manual instructions when persist_env=False and path_only=False."""
        with patch("agentic_devtools.cli.setup.commands._is_managed_bin_on_path", return_value=False):
            _persist_env_vars_to_profile(
                npmrc_path=Path("/some/npmrc"),
                unified_path=Path("/some/bundle.pem"),
                persist_env=False,
                overwrite_env=False,
                path_only=False,
            )
        out = capsys.readouterr().out
        assert "NPM_CONFIG_USERCONFIG" in out or "PATH" in out

    # -- persist_env=True, shell detection failure --

    def test_shell_detection_failure_falls_back_to_manual(self, capsys):
        """Falls back to manual instructions when shell detection raises."""
        with patch("agentic_devtools.cli.setup.commands._is_managed_bin_on_path", return_value=False):
            with patch(
                "agentic_devtools.cli.setup.commands.detect_shell_profile",
                side_effect=RuntimeError("no shell"),
            ):
                with patch(
                    "agentic_devtools.cli.setup.commands.detect_shell_type",
                    side_effect=RuntimeError("no shell"),
                ):
                    _persist_env_vars_to_profile(
                        npmrc_path=None,
                        unified_path=None,
                        persist_env=True,
                        overwrite_env=False,
                    )
        err = capsys.readouterr().err
        assert "Could not detect shell profile" in err

    # -- persist_env=True, profile_path is None --

    def test_profile_none_path_only_prints_path_instructions(self, capsys):
        """Prints PATH instructions when profile_path is None and path_only=False."""
        with patch("agentic_devtools.cli.setup.commands._is_managed_bin_on_path", return_value=False):
            with patch("agentic_devtools.cli.setup.commands.detect_shell_profile", return_value=None):
                with patch("agentic_devtools.cli.setup.commands.detect_shell_type", return_value=None):
                    _persist_env_vars_to_profile(
                        npmrc_path=Path("/some/npmrc"),
                        unified_path=Path("/some/bundle.pem"),
                        persist_env=True,
                        overwrite_env=False,
                        path_only=False,
                    )
        out = capsys.readouterr().out
        assert "NPM_CONFIG_USERCONFIG" in out or "PATH" in out

    def test_profile_none_path_only_true_prints_path_instructions(self, capsys):
        """Prints PATH instructions when profile_path is None and path_only=True."""
        with patch("agentic_devtools.cli.setup.commands._is_managed_bin_on_path", return_value=False):
            with patch("agentic_devtools.cli.setup.commands.detect_shell_profile", return_value=None):
                with patch("agentic_devtools.cli.setup.commands.detect_shell_type", return_value=None):
                    _persist_env_vars_to_profile(
                        npmrc_path=None,
                        unified_path=None,
                        persist_env=True,
                        overwrite_env=False,
                        path_only=True,
                    )
        out = capsys.readouterr().out
        assert "PATH" in out

    def test_profile_none_path_only_true_on_path_prints_nothing(self, capsys):
        """Prints nothing when profile_path is None, path_only=True, and already on PATH."""
        with patch("agentic_devtools.cli.setup.commands._is_managed_bin_on_path", return_value=True):
            with patch("agentic_devtools.cli.setup.commands.detect_shell_profile", return_value=None):
                with patch("agentic_devtools.cli.setup.commands.detect_shell_type", return_value=None):
                    _persist_env_vars_to_profile(
                        npmrc_path=None,
                        unified_path=None,
                        persist_env=True,
                        overwrite_env=False,
                        path_only=True,
                    )
        out = capsys.readouterr().out
        assert out == ""

    # -- persist_env=True, profile_path found, persists vars --

    def test_persists_npmrc_and_unified_paths(self, tmp_path, capsys):
        """Persists NPM_CONFIG_USERCONFIG and REQUESTS_CA_BUNDLE when both provided."""
        profile = tmp_path / ".bashrc"
        profile.write_text("", encoding="utf-8")

        with patch("agentic_devtools.cli.setup.commands._is_managed_bin_on_path", return_value=True):
            with patch("agentic_devtools.cli.setup.commands.detect_shell_profile", return_value=profile):
                with patch("agentic_devtools.cli.setup.commands.detect_shell_type", return_value="bash"):
                    _persist_env_vars_to_profile(
                        npmrc_path=Path("/home/user/.agdt/npmrc"),
                        unified_path=Path("/home/user/.agdt/certs/bundle.pem"),
                        persist_env=True,
                        overwrite_env=False,
                        path_only=False,
                    )
        out = capsys.readouterr().out
        assert "NPM_CONFIG_USERCONFIG" in out
        assert "REQUESTS_CA_BUNDLE" in out
        assert "NODE_EXTRA_CA_CERTS" in out

    def test_persists_path_entry_when_not_on_path(self, tmp_path, capsys):
        """Persists PATH entry when managed bin is not on PATH."""
        profile = tmp_path / ".bashrc"
        profile.write_text("", encoding="utf-8")

        with patch("agentic_devtools.cli.setup.commands._is_managed_bin_on_path", return_value=False):
            with patch("agentic_devtools.cli.setup.commands.detect_shell_profile", return_value=profile):
                with patch("agentic_devtools.cli.setup.commands.detect_shell_type", return_value="bash"):
                    with patch(
                        "agentic_devtools.cli.setup.commands.persist_path_entry",
                        return_value=True,
                    ):
                        _persist_env_vars_to_profile(
                            npmrc_path=None,
                            unified_path=None,
                            persist_env=True,
                            overwrite_env=False,
                            path_only=False,
                        )
        out = capsys.readouterr().out
        assert "PATH entry persisted" in out

    def test_path_entry_already_exists_prints_info(self, tmp_path, capsys):
        """Prints info message when PATH entry already exists and overwrite is False."""
        profile = tmp_path / ".bashrc"
        from agentic_devtools.cli.setup.commands import _MANAGED_BIN_DIR

        managed_bin_str = str(_MANAGED_BIN_DIR)
        profile.write_text(f'export PATH="{managed_bin_str}:$PATH"\n', encoding="utf-8")

        with patch("agentic_devtools.cli.setup.commands._is_managed_bin_on_path", return_value=False):
            with patch("agentic_devtools.cli.setup.commands.detect_shell_profile", return_value=profile):
                with patch("agentic_devtools.cli.setup.commands.detect_shell_type", return_value="bash"):
                    with patch(
                        "agentic_devtools.cli.setup.commands.persist_path_entry",
                        return_value=False,
                    ):
                        _persist_env_vars_to_profile(
                            npmrc_path=None,
                            unified_path=None,
                            persist_env=True,
                            overwrite_env=False,
                            path_only=False,
                        )
        out = capsys.readouterr().out
        assert "already set" in out or "overwrite-env" in out

    def test_path_entry_os_error_silently_ignored(self, tmp_path, capsys):
        """Silently ignores OSError when checking if PATH entry exists."""
        profile = tmp_path / ".bashrc"
        # Do NOT create the file so the OSError path is taken

        with patch("agentic_devtools.cli.setup.commands._is_managed_bin_on_path", return_value=False):
            with patch("agentic_devtools.cli.setup.commands.detect_shell_profile", return_value=profile):
                with patch("agentic_devtools.cli.setup.commands.detect_shell_type", return_value="bash"):
                    with patch(
                        "agentic_devtools.cli.setup.commands.persist_path_entry",
                        return_value=False,
                    ):
                        with patch.object(Path, "exists", side_effect=OSError("disk error")):
                            _persist_env_vars_to_profile(
                                npmrc_path=None,
                                unified_path=None,
                                persist_env=True,
                                overwrite_env=False,
                                path_only=False,
                            )
        # Should not raise — OSError is silently caught
        out = capsys.readouterr().out
        assert "PATH entry persisted" not in out

    def test_skips_vars_when_path_only(self, tmp_path, capsys):
        """Skips npmrc and unified path when path_only=True."""
        profile = tmp_path / ".bashrc"
        profile.write_text("", encoding="utf-8")

        with patch("agentic_devtools.cli.setup.commands._is_managed_bin_on_path", return_value=True):
            with patch("agentic_devtools.cli.setup.commands.detect_shell_profile", return_value=profile):
                with patch("agentic_devtools.cli.setup.commands.detect_shell_type", return_value="bash"):
                    with patch(
                        "agentic_devtools.cli.setup.commands.persist_env_var",
                    ) as mock_persist:
                        _persist_env_vars_to_profile(
                            npmrc_path=Path("/some/npmrc"),
                            unified_path=Path("/some/bundle.pem"),
                            persist_env=True,
                            overwrite_env=False,
                            path_only=True,
                        )
        mock_persist.assert_not_called()

    def test_shell_type_detection_failure_in_manual_instructions(self, capsys):
        """Uses None shell_type_hint when detect_shell_type raises in manual instructions path."""
        with patch("agentic_devtools.cli.setup.commands._is_managed_bin_on_path", return_value=False):
            with patch(
                "agentic_devtools.cli.setup.commands.detect_shell_type",
                side_effect=RuntimeError("no shell"),
            ):
                _persist_env_vars_to_profile(
                    npmrc_path=Path("/some/npmrc"),
                    unified_path=None,
                    persist_env=False,
                    overwrite_env=False,
                    path_only=False,
                )
        out = capsys.readouterr().out
        # Falls through to unknown shell instructions with None shell_type
        assert "NPM_CONFIG_USERCONFIG" in out
