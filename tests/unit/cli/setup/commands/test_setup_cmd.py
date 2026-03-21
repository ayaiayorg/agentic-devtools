"""Tests for setup_cmd."""

import os
from unittest.mock import patch

import pytest

from agentic_devtools.cli.setup import commands
from agentic_devtools.cli.setup.dependency_checker import DependencyStatus


def _make_statuses(git_found: bool = True) -> list:
    return [
        DependencyStatus(name="copilot", found=True, version="v1.0.0", path="/bin/copilot", category="Recommended"),
        DependencyStatus(name="gh", found=True, version="v2.65.0", path="/bin/gh", category="Recommended"),
        DependencyStatus(
            name="git",
            found=git_found,
            path="/usr/bin/git" if git_found else None,
            version="2.43.0" if git_found else None,
            required=True,
            category="Required",
        ),
        DependencyStatus(name="az", found=False, category="Optional — needed for Azure DevOps"),
        DependencyStatus(name="code", found=False, category="Optional — needed for VS Code integration"),
    ]


class TestSetupCmd:
    """Tests for setup_cmd."""

    @pytest.fixture(autouse=True)
    def _isolate_gitignore(self):
        """Prevent setup_cmd() from writing .agdt/.gitignore, injecting skills, or prompting for project config."""
        with patch("agentic_devtools.state._get_git_repo_root", return_value=None):
            with patch("agentic_devtools.agdt_gitignore.ensure_agdt_gitignore", return_value=False):
                with patch("agentic_devtools.skill_injector.inject_skills", return_value=False):
                    with patch.object(commands, "_prompt_project_config"):
                        yield

    def test_exits_zero_on_full_success(self, capsys):
        """Exits 0 when all installs succeed and required deps are found."""
        with patch("sys.argv", ["agdt-setup"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                commands.setup_cmd()  # Should not raise

    def test_exits_one_when_copilot_install_fails(self, capsys):
        """Exits 1 when copilot CLI install fails."""
        with patch("sys.argv", ["agdt-setup"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=False):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                with pytest.raises(SystemExit) as exc_info:
                                    commands.setup_cmd()
        assert exc_info.value.code == 1

    def test_exits_one_when_gh_install_fails(self, capsys):
        """Exits 1 when gh CLI install fails."""
        with patch("sys.argv", ["agdt-setup"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=False):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                with pytest.raises(SystemExit) as exc_info:
                                    commands.setup_cmd()
        assert exc_info.value.code == 1

    def test_exits_one_when_required_dep_missing(self, capsys):
        """Exits 1 when a required dependency (git) is not found."""
        with patch("sys.argv", ["agdt-setup"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(False)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                with pytest.raises(SystemExit) as exc_info:
                                    commands.setup_cmd()
        assert exc_info.value.code == 1

    def test_prints_banner(self, capsys):
        """Prints the setup banner."""
        with patch("sys.argv", ["agdt-setup"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                commands.setup_cmd()
        out = capsys.readouterr().out
        assert "agentic-devtools Setup" in out

    def test_system_only_skips_managed_installs(self, capsys):
        """With --system-only, managed installs are skipped."""
        with patch("sys.argv", ["agdt-setup", "--system-only"]):
            with patch.object(commands, "_prefetch_certs") as mock_certs:
                with patch.object(commands, "install_copilot_cli") as mock_copilot:
                    with patch.object(commands, "install_gh_cli") as mock_gh:
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                commands.setup_cmd()
        mock_certs.assert_not_called()
        mock_copilot.assert_not_called()
        mock_gh.assert_not_called()

    def test_system_only_exits_zero_when_required_deps_found(self, capsys):
        """With --system-only, exits 0 when required deps are present."""
        with patch("sys.argv", ["agdt-setup", "--system-only"]):
            with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                with patch.object(commands, "_persist_env_vars_to_profile"):
                    commands.setup_cmd()  # Should not raise

    def test_system_only_exits_one_when_required_dep_missing(self, capsys):
        """With --system-only, exits 1 when a required dependency (git) is missing."""
        with patch("sys.argv", ["agdt-setup", "--system-only"]):
            with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(False)):
                with patch.object(commands, "_persist_env_vars_to_profile"):
                    with pytest.raises(SystemExit) as exc_info:
                        commands.setup_cmd()
        assert exc_info.value.code == 1

    def test_system_only_prints_skip_message(self, capsys):
        """With --system-only, prints a message indicating managed installs are skipped."""
        with patch("sys.argv", ["agdt-setup", "--system-only"]):
            with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                with patch.object(commands, "_persist_env_vars_to_profile"):
                    commands.setup_cmd()
        out = capsys.readouterr().out
        assert "--system-only" in out

    def test_no_verify_ssl_cleaned_up_after_setup(self, monkeypatch):
        """AGDT_NO_VERIFY_SSL is removed from env after setup_cmd completes."""
        monkeypatch.delenv("AGDT_NO_VERIFY_SSL", raising=False)
        monkeypatch.setattr("sys.argv", ["agdt-setup", "--no-verify-ssl"])

        with patch.object(commands, "_prefetch_certs"):
            with patch.object(commands, "install_copilot_cli", return_value=True):
                with patch.object(commands, "install_gh_cli", return_value=True):
                    with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                        with patch.object(commands, "_persist_env_vars_to_profile"):
                            commands.setup_cmd()

        assert os.environ.get("AGDT_NO_VERIFY_SSL") is None

    def test_no_verify_ssl_prints_warning(self, capsys, monkeypatch):
        """Prints a warning when --no-verify-ssl is used."""
        monkeypatch.setattr("sys.argv", ["agdt-setup", "--no-verify-ssl"])

        with patch.object(commands, "install_copilot_cli", return_value=True):
            with patch.object(commands, "install_gh_cli", return_value=True):
                with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                    with patch.object(commands, "_persist_env_vars_to_profile"):
                        commands.setup_cmd()

        out = capsys.readouterr().out
        assert "SSL verification disabled" in out

    def test_without_no_verify_ssl_does_not_set_env_var(self, monkeypatch):
        """Does not set AGDT_NO_VERIFY_SSL when flag is absent."""
        monkeypatch.delenv("AGDT_NO_VERIFY_SSL", raising=False)
        monkeypatch.setattr("sys.argv", ["agdt-setup"])

        with patch.object(commands, "install_copilot_cli", return_value=True):
            with patch.object(commands, "install_gh_cli", return_value=True):
                with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                    with patch.object(commands, "_persist_env_vars_to_profile"):
                        commands.setup_cmd()

        assert os.environ.get("AGDT_NO_VERIFY_SSL") is None

    def test_no_persist_env_flag_disables_persistence(self, monkeypatch):
        """--no-persist-env flag disables env var persistence."""
        monkeypatch.setattr("sys.argv", ["agdt-setup", "--no-persist-env"])

        with patch.object(commands, "_prefetch_certs"):
            with patch.object(commands, "install_copilot_cli", return_value=True):
                with patch.object(commands, "install_gh_cli", return_value=True):
                    with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                        with patch.object(commands, "_persist_env_vars_to_profile") as mock_persist:
                            commands.setup_cmd()

        mock_persist.assert_called_once()
        assert mock_persist.call_args.kwargs["persist_env"] is False

    def test_overwrite_env_flag_accepted(self, monkeypatch):
        """--overwrite-env flag is accepted and passed through."""
        monkeypatch.setattr("sys.argv", ["agdt-setup", "--overwrite-env"])

        with patch.object(commands, "_prefetch_certs"):
            with patch.object(commands, "install_copilot_cli", return_value=True):
                with patch.object(commands, "install_gh_cli", return_value=True):
                    with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                        with patch.object(commands, "_persist_env_vars_to_profile") as mock_persist:
                            commands.setup_cmd()

        mock_persist.assert_called_once()
        assert mock_persist.call_args.kwargs["overwrite_env"] is True

    def test_gitignore_success_prints_message(self, capsys, tmp_path):
        """Prints success message when .agdt/.gitignore is created."""
        with patch("sys.argv", ["agdt-setup"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                # Override autouse fixture to test the success path
                                with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
                                    with patch(
                                        "agentic_devtools.agdt_gitignore.ensure_agdt_gitignore", return_value=True
                                    ):
                                        commands.setup_cmd()

        out = capsys.readouterr().out
        assert "Ensured .agdt/.gitignore" in out

    def test_gitignore_write_failure_warns_on_stderr(self, capsys, tmp_path):
        """Prints warning to stderr when .agdt/.gitignore write fails."""
        with patch("sys.argv", ["agdt-setup"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                # Override autouse fixture to test the failure path
                                with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
                                    with patch(
                                        "agentic_devtools.agdt_gitignore.ensure_agdt_gitignore", return_value=False
                                    ):
                                        commands.setup_cmd()

        err = capsys.readouterr().err
        assert "Failed to create/update .agdt/.gitignore" in err

    def test_inject_skills_success_prints_message(self, capsys, tmp_path):
        """Prints success message when agent/prompt skills are injected."""
        with patch("sys.argv", ["agdt-setup"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
                                    with patch(
                                        "agentic_devtools.agdt_gitignore.ensure_agdt_gitignore", return_value=True
                                    ):
                                        with patch("agentic_devtools.skill_injector.inject_skills", return_value=True):
                                            commands.setup_cmd()

        out = capsys.readouterr().out
        assert "Injected agent/prompt skills" in out

    def test_inject_skills_failure_warns_on_stderr(self, capsys, tmp_path):
        """Prints neutral warning to stderr when skill injection fails."""
        with patch("sys.argv", ["agdt-setup"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
                                    with patch(
                                        "agentic_devtools.agdt_gitignore.ensure_agdt_gitignore", return_value=True
                                    ):
                                        with patch("agentic_devtools.skill_injector.inject_skills", return_value=False):
                                            commands.setup_cmd()

        err = capsys.readouterr().err
        assert "Failed to inject agent/prompt skills" in err
        assert "missing/corrupted bundled skills" in err

    def test_skill_injector_import_failure_warns_and_skips_injection(self, capsys, tmp_path):
        """Prints a warning and skips injection when the lazy skill injector import fails."""
        import builtins

        original_import = builtins.__import__

        def _raising_import(name, *args, **kwargs):
            if name == "agentic_devtools.skill_injector":
                raise SyntaxError("simulated syntax error in skill_injector")
            return original_import(name, *args, **kwargs)

        with patch("sys.argv", ["agdt-setup"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
                                    with patch(
                                        "agentic_devtools.agdt_gitignore.ensure_agdt_gitignore", return_value=True
                                    ):
                                        with patch("builtins.__import__", side_effect=_raising_import):
                                            commands.setup_cmd()

        err = capsys.readouterr().err
        assert "Failed to import skill injector" in err
        assert "skipping agent/prompt skill injection" in err

    def test_no_verify_ssl_restored_after_setup_when_previously_set(self, monkeypatch):
        """Restores pre-existing AGDT_NO_VERIFY_SSL value after setup_cmd completes."""
        monkeypatch.setenv("AGDT_NO_VERIFY_SSL", "pre-existing")
        monkeypatch.setattr("sys.argv", ["agdt-setup", "--no-verify-ssl"])

        with patch.object(commands, "_prefetch_certs"):
            with patch.object(commands, "install_copilot_cli", return_value=True):
                with patch.object(commands, "install_gh_cli", return_value=True):
                    with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                        with patch.object(commands, "_persist_env_vars_to_profile"):
                            commands.setup_cmd()

        assert os.environ.get("AGDT_NO_VERIFY_SSL") == "pre-existing"

    def test_no_verify_ssl_cleaned_up_on_error(self, monkeypatch):
        """AGDT_NO_VERIFY_SSL is cleaned up even when setup_cmd raises."""
        monkeypatch.delenv("AGDT_NO_VERIFY_SSL", raising=False)
        monkeypatch.setattr("sys.argv", ["agdt-setup", "--no-verify-ssl"])

        with patch.object(commands, "_prefetch_certs"):
            with patch.object(commands, "install_copilot_cli", return_value=False):
                with patch.object(commands, "install_gh_cli", return_value=True):
                    with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                        with patch.object(commands, "_persist_env_vars_to_profile"):
                            try:
                                commands.setup_cmd()
                            except SystemExit:
                                pass

        assert os.environ.get("AGDT_NO_VERIFY_SSL") is None
