"""Tests for check_privileged_paths() guard."""

import pytest

from agentic_devtools.cli.ci.guards import check_privileged_paths


class TestCheckPrivilegedPaths:
    """Tests for the privileged paths guard."""

    @pytest.fixture(autouse=True)
    def clear_allow_privileged_paths_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AGDT_ALLOW_PRIVILEGED_PATHS", raising=False)

    def test_workflow_file_triggers(self) -> None:
        assert check_privileged_paths([".github/workflows/ci.yml"]) is True

    def test_actions_file_triggers(self) -> None:
        assert check_privileged_paths([".github/actions/setup/action.yml"]) is True

    def test_scripts_file_triggers(self) -> None:
        assert check_privileged_paths([".github/scripts/deploy.sh"]) is True

    def test_markdown_excluded(self) -> None:
        assert check_privileged_paths([".github/workflows/README.md"]) is False

    def test_markdown_in_scripts_excluded(self) -> None:
        assert check_privileged_paths([".github/scripts/NOTES.md"]) is False

    def test_non_privileged_paths(self) -> None:
        assert check_privileged_paths(["src/main.py", "tests/test_main.py"]) is False

    def test_empty_file_list(self) -> None:
        assert check_privileged_paths([]) is False

    def test_mixed_privileged_and_normal(self) -> None:
        files = ["src/app.py", ".github/workflows/ci.yml", "README.md"]
        assert check_privileged_paths(files) is True

    def test_github_root_files_not_privileged(self) -> None:
        assert check_privileged_paths([".github/CODEOWNERS"]) is False

    def test_github_agents_not_privileged(self) -> None:
        assert check_privileged_paths([".github/agents/review.md"]) is False

    def test_env_var_disabled_bypasses_guard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AGDT_ALLOW_PRIVILEGED_PATHS", "1")
        assert check_privileged_paths([".github/workflows/ci.yml"]) is False

    def test_env_var_true_bypasses_guard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AGDT_ALLOW_PRIVILEGED_PATHS", "true")
        assert check_privileged_paths([".github/workflows/ci.yml"]) is False

    def test_env_var_yes_bypasses_guard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AGDT_ALLOW_PRIVILEGED_PATHS", "yes")
        assert check_privileged_paths([".github/workflows/ci.yml"]) is False

    def test_env_var_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AGDT_ALLOW_PRIVILEGED_PATHS", "TRUE")
        assert check_privileged_paths([".github/workflows/ci.yml"]) is False

    def test_env_var_zero_does_not_bypass(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AGDT_ALLOW_PRIVILEGED_PATHS", "0")
        assert check_privileged_paths([".github/workflows/ci.yml"]) is True

    def test_env_var_unset_default_behaviour(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AGDT_ALLOW_PRIVILEGED_PATHS", raising=False)
        assert check_privileged_paths([".github/workflows/ci.yml"]) is True
