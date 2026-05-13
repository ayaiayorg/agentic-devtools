"""Tests for check_privileged_paths() guard."""

from agentic_devtools.cli.ci.guards import check_privileged_paths


class TestCheckPrivilegedPaths:
    """Tests for the privileged paths guard."""

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
