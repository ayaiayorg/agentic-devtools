"""Tests for OpenVscodeWorkspace."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.workflows.worktree_setup import (
    open_vscode_workspace,
)


class TestOpenVscodeWorkspace:
    """Tests for open_vscode_workspace function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.CREATE_NEW_PROCESS_GROUP", 0x200, create=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.DETACHED_PROCESS", 0x8, create=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    @patch(
        "agentic_devtools.cli.workflows.worktree_setup.find_workspace_file",
        return_value="/repos/DFLY-1234/my-project.code-workspace",
    )
    def test_opens_vscode_on_windows(self, mock_find, mock_platform, mock_popen):
        """Test opening VS Code on Windows uses shell=True and creationflags."""
        mock_platform.return_value = "Windows"
        mock_popen.return_value = MagicMock()

        result = open_vscode_workspace("/repos/DFLY-1234")

        assert result is True
        mock_popen.assert_called_once()
        call_kwargs = mock_popen.call_args[1]
        assert call_kwargs["shell"] is True
        assert call_kwargs["creationflags"] == 0x8 | 0x200

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    @patch(
        "agentic_devtools.cli.workflows.worktree_setup.find_workspace_file",
        return_value="/repos/DFLY-1234/my-project.code-workspace",
    )
    def test_opens_vscode_on_linux(self, mock_find, mock_platform, mock_popen):
        """Test opening VS Code on Linux."""
        mock_platform.return_value = "Linux"
        mock_popen.return_value = MagicMock()

        result = open_vscode_workspace("/repos/DFLY-1234")

        assert result is True
        mock_popen.assert_called_once()

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    @patch(
        "agentic_devtools.cli.workflows.worktree_setup.find_workspace_file",
        return_value="/repos/DFLY-1234/my-project.code-workspace",
    )
    def test_opens_vscode_on_darwin(self, mock_find, mock_platform, mock_popen):
        """Test opening VS Code on macOS."""
        mock_platform.return_value = "Darwin"
        mock_popen.return_value = MagicMock()

        result = open_vscode_workspace("/repos/DFLY-1234")

        assert result is True
        mock_popen.assert_called_once()

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    @patch(
        "agentic_devtools.cli.workflows.worktree_setup.find_workspace_file",
        return_value=None,
    )
    def test_opens_folder_when_workspace_not_found(self, mock_find, mock_platform, mock_popen):
        """Test that VS Code opens at the worktree root when no workspace file exists."""
        mock_platform.return_value = "Linux"
        mock_popen.return_value = MagicMock()

        result = open_vscode_workspace("/repos/DFLY-1234")

        assert result is True
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert "/repos/DFLY-1234" in call_args

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    @patch(
        "agentic_devtools.cli.workflows.worktree_setup.find_workspace_file",
        return_value="/repos/DFLY-1234/my-project.code-workspace",
    )
    def test_handles_popen_exception(self, mock_find, mock_platform, mock_popen):
        """Test handling Popen exception."""
        mock_platform.return_value = "Windows"
        mock_popen.side_effect = OSError("code not found")

        result = open_vscode_workspace("/repos/DFLY-1234")

        assert result is False
