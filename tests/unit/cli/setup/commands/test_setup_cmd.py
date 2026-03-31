"""Tests for setup_cmd."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

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
        """Prevent setup_cmd() from writing .agdt/.gitignore or injecting skills into the real repo."""
        with patch("agentic_devtools.state._get_git_repo_root", return_value=None):
            with patch("agentic_devtools.agdt_gitignore.ensure_agdt_gitignore", return_value=False):
                with patch("agentic_devtools.skill_injector.inject_skills", return_value=False):
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
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
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
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
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
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch(
                                                    "agentic_devtools.skill_injector.inject_skills", return_value=True
                                                ):
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
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch(
                                                    "agentic_devtools.skill_injector.inject_skills", return_value=False
                                                ):
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
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
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

    # ── New flag acceptance tests ──────────────────────────────────────

    def test_skip_platform_detection_flag_accepted(self, capsys):
        """--skip-platform-detection flag is accepted without error."""
        with patch("sys.argv", ["agdt-setup", "--skip-platform-detection"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                commands.setup_cmd()

    def test_issue_adapter_jira_flag_accepted(self, capsys):
        """--issue-adapter jira flag is accepted without error."""
        with patch("sys.argv", ["agdt-setup", "--issue-adapter", "jira"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                commands.setup_cmd()

    def test_issue_adapter_github_flag_accepted(self, capsys):
        """--issue-adapter github flag is accepted without error."""
        with patch("sys.argv", ["agdt-setup", "--issue-adapter", "github"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                commands.setup_cmd()

    def test_issue_adapter_markdown_flag_accepted(self, capsys):
        """--issue-adapter markdown flag is accepted without error."""
        with patch("sys.argv", ["agdt-setup", "--issue-adapter", "markdown"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                commands.setup_cmd()

    def test_skip_templates_flag_accepted(self, capsys):
        """--skip-templates flag is accepted without error."""
        with patch("sys.argv", ["agdt-setup", "--skip-templates"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                commands.setup_cmd()

    def test_reconfigure_flag_accepted(self, capsys):
        """--reconfigure flag is accepted without error."""
        with patch("sys.argv", ["agdt-setup", "--reconfigure"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                commands.setup_cmd()

    def test_reconfigure_flag_threads_to_prompt_functions(self, capsys, tmp_path):
        """--reconfigure passes force_prompt=True to both prompt functions."""
        with patch("sys.argv", ["agdt-setup", "--reconfigure", "--skip-platform-detection", "--skip-templates"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
                                    with patch(
                                        "agentic_devtools.agdt_gitignore.ensure_agdt_gitignore", return_value=True
                                    ):
                                        with patch.object(commands, "_prompt_project_config") as mock_project:
                                            with patch.object(commands, "_prompt_copilot_model") as mock_copilot:
                                                commands.setup_cmd()
        mock_project.assert_called_once_with(force_prompt=True)
        mock_copilot.assert_called_once_with(force_prompt=True)

    def test_no_reconfigure_passes_false_to_prompt_functions(self, capsys, tmp_path):
        """Without --reconfigure, force_prompt=False is passed to both prompt functions."""
        with patch("sys.argv", ["agdt-setup", "--skip-platform-detection", "--skip-templates"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
                                    with patch(
                                        "agentic_devtools.agdt_gitignore.ensure_agdt_gitignore", return_value=True
                                    ):
                                        with patch.object(commands, "_prompt_project_config") as mock_project:
                                            with patch.object(commands, "_prompt_copilot_model") as mock_copilot:
                                                commands.setup_cmd()
        mock_project.assert_called_once_with(force_prompt=False)
        mock_copilot.assert_called_once_with(force_prompt=False)

    def test_invalid_issue_adapter_rejected(self, capsys):
        """Invalid --issue-adapter value is rejected by argparse."""
        with patch("sys.argv", ["agdt-setup", "--issue-adapter", "foo"]):
            with pytest.raises(SystemExit) as exc_info:
                commands.setup_cmd()
        assert exc_info.value.code == 2

    # ── Platform detection step tests ──────────────────────────────────

    def test_detection_runs_and_save_succeeds(self, capsys, tmp_path):
        """Detection runs and save succeeds → prints success message."""
        mock_result = MagicMock()
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
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch(
                                                    "agentic_devtools.cli.setup.platform_detection.detect_platforms",
                                                    return_value=mock_result,
                                                ) as mock_detect:
                                                    with patch(
                                                        "agentic_devtools.cli.setup.platform_detection.confirm_and_override",
                                                        return_value={"issue_adapter": "jira"},
                                                    ) as mock_confirm:
                                                        with patch(
                                                            "agentic_devtools.config.save_platform_config",
                                                            return_value=True,
                                                        ) as mock_save:
                                                            with patch(
                                                                "agentic_devtools.cli.setup.workflow_templates.generate_default_templates",
                                                                return_value=[],
                                                            ):
                                                                commands.setup_cmd()
        out = capsys.readouterr().out
        assert "Platform configuration saved" in out
        mock_detect.assert_called_once_with(str(tmp_path))
        mock_confirm.assert_called_once_with(mock_result)
        mock_save.assert_called_once_with(str(tmp_path), {"issue_adapter": "jira"})

    def test_skip_platform_detection_skips_detect_and_save(self, capsys, tmp_path):
        """--skip-platform-detection → detection and save are NOT called."""
        with patch("sys.argv", ["agdt-setup", "--skip-platform-detection"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
                                    with patch(
                                        "agentic_devtools.agdt_gitignore.ensure_agdt_gitignore", return_value=True
                                    ):
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch(
                                                    "agentic_devtools.cli.setup.platform_detection.detect_platforms",
                                                ) as mock_detect:
                                                    with patch(
                                                        "agentic_devtools.config.save_platform_config",
                                                    ) as mock_save:
                                                        with patch(
                                                            "agentic_devtools.cli.setup.workflow_templates.generate_default_templates",
                                                            return_value=[],
                                                        ):
                                                            commands.setup_cmd()
        mock_detect.assert_not_called()
        mock_save.assert_not_called()

    def test_issue_adapter_override_skips_detection(self, capsys, tmp_path):
        """--issue-adapter jira → detect_platforms NOT called, loads existing config and overrides adapter."""
        existing_config = {
            "issue_adapter": "github",
            "code_hosting": "azure_devops",
            "jira": {},
            "github": {"repo": "owner/repo"},
            "azure_devops": {"project": "org/proj"},
        }
        with patch("sys.argv", ["agdt-setup", "--issue-adapter", "jira"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
                                    with patch(
                                        "agentic_devtools.agdt_gitignore.ensure_agdt_gitignore", return_value=True
                                    ):
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch(
                                                    "agentic_devtools.cli.setup.platform_detection.detect_platforms",
                                                ) as mock_detect:
                                                    with patch(
                                                        "agentic_devtools.config.load_platform_config",
                                                        return_value=existing_config,
                                                    ) as mock_load:
                                                        with patch(
                                                            "agentic_devtools.config.save_platform_config",
                                                            return_value=True,
                                                        ) as mock_save:
                                                            with patch(
                                                                "agentic_devtools.cli.setup.workflow_templates.generate_default_templates",
                                                                return_value=[],
                                                            ):
                                                                commands.setup_cmd()
        out = capsys.readouterr().out
        assert "Issue adapter configured: jira" in out
        mock_detect.assert_not_called()
        mock_load.assert_called_once_with(str(tmp_path))
        # Verify existing fields are preserved and only issue_adapter is overridden
        mock_save.assert_called_once_with(
            str(tmp_path),
            {
                "issue_adapter": "jira",
                "code_hosting": "azure_devops",
                "jira": {},
                "github": {"repo": "owner/repo"},
                "azure_devops": {"project": "org/proj"},
            },
        )

    def test_save_platform_config_returns_false_warns_stderr(self, capsys, tmp_path):
        """save_platform_config returns False → prints warning to stderr."""
        mock_result = MagicMock()
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
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch(
                                                    "agentic_devtools.cli.setup.platform_detection.detect_platforms",
                                                    return_value=mock_result,
                                                ):
                                                    with patch(
                                                        "agentic_devtools.cli.setup.platform_detection.confirm_and_override",
                                                        return_value={"issue_adapter": "jira"},
                                                    ):
                                                        with patch(
                                                            "agentic_devtools.config.save_platform_config",
                                                            return_value=False,
                                                        ):
                                                            with patch(
                                                                "agentic_devtools.cli.setup.workflow_templates.generate_default_templates",
                                                                return_value=[],
                                                            ):
                                                                commands.setup_cmd()
        err = capsys.readouterr().err
        assert "Failed to save platform configuration" in err

    def test_detect_platforms_raises_warns_stderr(self, capsys, tmp_path):
        """detect_platforms raises RuntimeError → prints warning to stderr, setup completes."""
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
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch(
                                                    "agentic_devtools.cli.setup.platform_detection.detect_platforms",
                                                    side_effect=RuntimeError("boom"),
                                                ):
                                                    with patch(
                                                        "agentic_devtools.cli.setup.workflow_templates.generate_default_templates",
                                                        return_value=[],
                                                    ):
                                                        commands.setup_cmd()
        err = capsys.readouterr().err
        assert "Platform setup failed" in err
        assert "boom" in err

    def test_system_only_skips_detection(self, capsys):
        """--system-only → detection NOT called."""
        with patch("sys.argv", ["agdt-setup", "--system-only"]):
            with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                with patch.object(commands, "_persist_env_vars_to_profile"):
                    with patch(
                        "agentic_devtools.cli.setup.platform_detection.detect_platforms",
                    ) as mock_detect:
                        commands.setup_cmd()
        mock_detect.assert_not_called()

    # ── Template generation step tests ─────────────────────────────────

    def test_templates_generated_prints_paths(self, capsys, tmp_path):
        """Templates generated → prints success message for each file."""
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
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch(
                                                    "agentic_devtools.cli.setup.platform_detection.detect_platforms",
                                                    side_effect=RuntimeError("skip"),
                                                ):
                                                    with patch(
                                                        "agentic_devtools.cli.setup.workflow_templates.generate_default_templates",
                                                        return_value=[
                                                            Path("/tmp/a.py"),
                                                            Path("/tmp/b.py"),
                                                        ],
                                                    ):
                                                        commands.setup_cmd()
        out = capsys.readouterr().out
        assert "Generated template:" in out

    def test_skip_templates_does_not_call_generate(self, capsys, tmp_path):
        """--skip-templates → generate_default_templates NOT called."""
        with patch("sys.argv", ["agdt-setup", "--skip-templates"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
                                    with patch(
                                        "agentic_devtools.agdt_gitignore.ensure_agdt_gitignore", return_value=True
                                    ):
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch(
                                                    "agentic_devtools.cli.setup.platform_detection.detect_platforms",
                                                    side_effect=RuntimeError("skip"),
                                                ):
                                                    with patch(
                                                        "agentic_devtools.cli.setup.workflow_templates.generate_default_templates",
                                                    ) as mock_gen:
                                                        commands.setup_cmd()
        mock_gen.assert_not_called()

    def test_templates_empty_list_prints_info(self, capsys, tmp_path):
        """generate_default_templates returns empty list → prints info message."""
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
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch(
                                                    "agentic_devtools.cli.setup.platform_detection.detect_platforms",
                                                    side_effect=RuntimeError("skip"),
                                                ):
                                                    with patch(
                                                        "agentic_devtools.cli.setup.workflow_templates.generate_default_templates",
                                                        return_value=[],
                                                    ):
                                                        commands.setup_cmd()
        out = capsys.readouterr().out
        assert "Workflow templates already exist" in out

    def test_template_generation_raises_warns_stderr(self, capsys, tmp_path):
        """generate_default_templates raises OSError → prints warning, setup completes."""
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
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch(
                                                    "agentic_devtools.cli.setup.platform_detection.detect_platforms",
                                                    side_effect=RuntimeError("skip"),
                                                ):
                                                    with patch(
                                                        "agentic_devtools.cli.setup.workflow_templates.generate_default_templates",
                                                        side_effect=OSError("disk full"),
                                                    ):
                                                        commands.setup_cmd()
        err = capsys.readouterr().err
        assert "Template generation failed" in err
        assert "disk full" in err

    def test_template_target_dir_is_correct(self, capsys, tmp_path):
        """Template target_dir is git_root / '.agdt' / 'workflow-definitions'."""
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
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch(
                                                    "agentic_devtools.cli.setup.platform_detection.detect_platforms",
                                                    side_effect=RuntimeError("skip"),
                                                ):
                                                    with patch(
                                                        "agentic_devtools.cli.setup.workflow_templates.generate_default_templates",
                                                        return_value=[],
                                                    ) as mock_gen:
                                                        commands.setup_cmd()
        mock_gen.assert_called_once_with(tmp_path / ".agdt" / "workflow-definitions")

    # ── Import failure tests ───────────────────────────────────────────

    def test_platform_detection_import_failure_skips_detection(self, capsys, tmp_path):
        """Import of platform_detection fails → prints warning, skips detection, templates still run."""
        import builtins

        original_import = builtins.__import__

        def _raising_import(name, *args, **kwargs):
            if name == "agentic_devtools.cli.setup.platform_detection":
                raise ImportError("simulated import error")
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
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch("builtins.__import__", side_effect=_raising_import):
                                                    with patch(
                                                        "agentic_devtools.cli.setup.workflow_templates.generate_default_templates",
                                                        return_value=[],
                                                    ) as mock_gen:
                                                        commands.setup_cmd()
        err = capsys.readouterr().err
        assert "Platform setup failed" in err
        mock_gen.assert_called_once()

    def test_workflow_templates_import_failure_skips_templates(self, capsys, tmp_path):
        """Import of workflow_templates fails → prints warning, skips templates."""
        import builtins

        original_import = builtins.__import__

        def _raising_import(name, *args, **kwargs):
            if name == "agentic_devtools.cli.setup.workflow_templates":
                raise ImportError("simulated import error")
            return original_import(name, *args, **kwargs)

        with patch("sys.argv", ["agdt-setup", "--skip-platform-detection"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
                                    with patch(
                                        "agentic_devtools.agdt_gitignore.ensure_agdt_gitignore", return_value=True
                                    ):
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch("builtins.__import__", side_effect=_raising_import):
                                                    commands.setup_cmd()
        err = capsys.readouterr().err
        assert "Template generation failed" in err

    # ── Integration tests ──────────────────────────────────────────────

    def test_all_new_steps_succeed_exits_zero(self, capsys, tmp_path):
        """All new steps succeed → setup exits 0 with success message."""
        mock_result = MagicMock()
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
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch(
                                                    "agentic_devtools.cli.setup.platform_detection.detect_platforms",
                                                    return_value=mock_result,
                                                ):
                                                    with patch(
                                                        "agentic_devtools.cli.setup.platform_detection.confirm_and_override",
                                                        return_value={"issue_adapter": "github"},
                                                    ):
                                                        with patch(
                                                            "agentic_devtools.config.save_platform_config",
                                                            return_value=True,
                                                        ):
                                                            with patch(
                                                                "agentic_devtools.cli.setup.workflow_templates.generate_default_templates",
                                                                return_value=[Path("/tmp/a.py")],
                                                            ):
                                                                commands.setup_cmd()
        out = capsys.readouterr().out
        assert "Setup complete! ✅" in out

    def test_new_steps_fail_but_setup_still_exits_zero(self, capsys, tmp_path):
        """New steps fail but copilot/gh/deps succeed → setup still exits 0."""
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
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch(
                                                    "agentic_devtools.cli.setup.platform_detection.detect_platforms",
                                                    side_effect=RuntimeError("detection failed"),
                                                ):
                                                    with patch(
                                                        "agentic_devtools.cli.setup.workflow_templates.generate_default_templates",
                                                        side_effect=OSError("template failed"),
                                                    ):
                                                        commands.setup_cmd()
        out = capsys.readouterr().out
        assert "Setup complete! ✅" in out

    def test_save_platform_config_returns_false_with_issue_adapter_warns(self, capsys, tmp_path):
        """--issue-adapter with save returning False → prints warning to stderr."""
        with patch("sys.argv", ["agdt-setup", "--issue-adapter", "github"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
                                    with patch(
                                        "agentic_devtools.agdt_gitignore.ensure_agdt_gitignore", return_value=True
                                    ):
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch(
                                                    "agentic_devtools.config.load_platform_config",
                                                    return_value={
                                                        "issue_adapter": "jira",
                                                        "code_hosting": "other",
                                                        "jira": {},
                                                        "github": {},
                                                        "azure_devops": {},
                                                    },
                                                ):
                                                    with patch(
                                                        "agentic_devtools.config.save_platform_config",
                                                        return_value=False,
                                                    ):
                                                        with patch(
                                                            "agentic_devtools.cli.setup.workflow_templates.generate_default_templates",
                                                            return_value=[],
                                                        ):
                                                            commands.setup_cmd()
        err = capsys.readouterr().err
        assert "Failed to save platform configuration" in err

    def test_section_header_printed(self, capsys, tmp_path):
        """Platform & Workflow Setup section header is printed."""
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
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch(
                                                    "agentic_devtools.cli.setup.platform_detection.detect_platforms",
                                                    side_effect=RuntimeError("skip"),
                                                ):
                                                    with patch(
                                                        "agentic_devtools.cli.setup.workflow_templates.generate_default_templates",
                                                        return_value=[],
                                                    ):
                                                        commands.setup_cmd()
        out = capsys.readouterr().out
        assert "Platform & Workflow Setup" in out

    def test_skip_pr_workflow_flag_accepted(self, capsys):
        """--skip-pr-workflow flag is accepted without error."""
        with patch("sys.argv", ["agdt-setup", "--skip-pr-workflow"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                commands.setup_cmd()

    def test_skip_pr_workflow_bypasses_pr_workflow(self, capsys, tmp_path):
        """--skip-pr-workflow runs file-modifying steps directly without PR workflow."""
        with patch("sys.argv", ["agdt-setup", "--skip-pr-workflow"]):
            with patch.object(commands, "_prefetch_certs"):
                with patch.object(commands, "install_copilot_cli", return_value=True):
                    with patch.object(commands, "install_gh_cli", return_value=True):
                        with patch.object(commands, "check_all_dependencies", return_value=_make_statuses(True)):
                            with patch.object(commands, "_persist_env_vars_to_profile"):
                                with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
                                    with patch(
                                        "agentic_devtools.agdt_gitignore.ensure_agdt_gitignore", return_value=True
                                    ):
                                        with patch.object(commands, "_prompt_project_config"):
                                            with patch.object(commands, "_prompt_copilot_model"):
                                                with patch(
                                                    "agentic_devtools.cli.setup.pr_workflow.run_setup_with_pr_workflow"
                                                ) as mock_pr:
                                                    commands.setup_cmd()
        # PR workflow should NOT be called
        mock_pr.assert_not_called()
