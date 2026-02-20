"""Tests for OpenVscodeWorkspace."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.workflows.worktree_setup import (
    open_vscode_workspace,
)


class TestOpenVscodeWorkspace:
    """Tests for open_vscode_workspace function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    @patch("os.path.exists")
    def test_opens_vscode_on_windows(self, mock_exists, mock_platform, mock_popen):
        """Test opening VS Code on Windows."""
        mock_exists.return_value = True
        mock_platform.return_value = "Windows"
        mock_popen.return_value = MagicMock()

        result = open_vscode_workspace("/repos/DFLY-1234")

        assert result is True
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert "code" in call_args[0].lower() or any("code" in str(arg).lower() for arg in call_args)

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    @patch("os.path.exists")
    def test_opens_vscode_on_linux(self, mock_exists, mock_platform, mock_popen):
        """Test opening VS Code on Linux."""
        mock_exists.return_value = True
        mock_platform.return_value = "Linux"
        mock_popen.return_value = MagicMock()

        result = open_vscode_workspace("/repos/DFLY-1234")

        assert result is True
        mock_popen.assert_called_once()

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    @patch("os.path.exists")
    def test_opens_vscode_on_darwin(self, mock_exists, mock_platform, mock_popen):
        """Test opening VS Code on macOS."""
        mock_exists.return_value = True
        mock_platform.return_value = "Darwin"
        mock_popen.return_value = MagicMock()

        result = open_vscode_workspace("/repos/DFLY-1234")

        assert result is True
        mock_popen.assert_called_once()

    @patch("os.path.exists")
    def test_returns_false_when_workspace_not_found(self, mock_exists):
        """Test returning False when workspace file not found."""
        mock_exists.return_value = False

        result = open_vscode_workspace("/repos/DFLY-1234")

        # Should return False since workspace doesn't exist
        assert result is False

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    @patch("os.path.exists")
    def test_handles_popen_exception(self, mock_exists, mock_platform, mock_popen):
        """Test handling Popen exception."""
        mock_exists.return_value = True
        mock_platform.return_value = "Windows"
        mock_popen.side_effect = OSError("code not found")

        result = open_vscode_workspace("/repos/DFLY-1234")

        assert result is False
