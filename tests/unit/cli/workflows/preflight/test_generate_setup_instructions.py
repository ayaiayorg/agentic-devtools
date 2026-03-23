"""Tests for GenerateSetupInstructions."""

from agentic_devtools.cli.workflows.preflight import (
    PreflightResult,
    generate_setup_instructions,
)


class TestGenerateSetupInstructions:
    """Tests for generate_setup_instructions function."""

    def test_includes_failure_reasons(self):
        """Test that failure reasons are included."""
        result = PreflightResult(
            folder_valid=False,
            branch_valid=False,
            folder_name="wrong-folder",
            branch_name="main",
            issue_key="PROJECT-1850",
        )

        instructions = generate_setup_instructions("PROJECT-1850", result)

        assert "PROJECT-1850" in instructions
        assert "Issues Detected" in instructions

    def test_includes_worktree_command_when_folder_wrong(self):
        """Test that worktree command is included when folder is wrong."""
        result = PreflightResult(
            folder_valid=False,
            branch_valid=True,
            folder_name="wrong-folder",
            branch_name="feature/PROJECT-1850/test",
            issue_key="PROJECT-1850",
        )

        instructions = generate_setup_instructions("PROJECT-1850", result)

        assert "git worktree add" in instructions
        assert "PROJECT-1850" in instructions

    def test_includes_branch_command_when_only_branch_wrong(self):
        """Test that branch command is included when only branch is wrong."""
        result = PreflightResult(
            folder_valid=True,
            branch_valid=False,
            folder_name="PROJECT-1850",
            branch_name="main",
            issue_key="PROJECT-1850",
        )

        instructions = generate_setup_instructions("PROJECT-1850", result)

        assert "git switch -c" in instructions
        assert "feature/PROJECT-1850" in instructions

    def test_includes_vscode_command(self):
        """Test that VS Code open command is included."""
        result = PreflightResult(
            folder_valid=False,
            branch_valid=False,
            folder_name="wrong",
            branch_name="main",
            issue_key="PROJECT-1850",
        )

        instructions = generate_setup_instructions("PROJECT-1850", result)

        assert "code .." in instructions
        assert "agdt-platform-management.code-workspace" in instructions
