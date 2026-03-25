"""Tests for get_azure_devops_context_from_git_remote."""


class TestGetAzureDevOpsContextFromGitRemote:
    """Tests for get_azure_devops_context_from_git_remote function."""

    def test_extracts_context_from_azure_devops_https_remote(self, monkeypatch):
        """Test extracting organization, project, and repository from Azure DevOps HTTPS remote."""
        import subprocess

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = "https://dev.azure.com/swica/DragonflyMgmt/_git/dfly-platform-management"
                returncode = 0

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        from agentic_devtools.cli.azure_devops.config import get_azure_devops_context_from_git_remote

        result = get_azure_devops_context_from_git_remote()
        assert result == ("https://dev.azure.com/swica", "DragonflyMgmt", "dfly-platform-management")

    def test_extracts_context_from_azure_devops_ssh_remote(self, monkeypatch):
        """Test extracting organization, project, and repository from Azure DevOps SSH remote."""
        import subprocess

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = "git@ssh.dev.azure.com:v3/swica/DragonflyMgmt/dfly-platform-management"
                returncode = 0

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        from agentic_devtools.cli.azure_devops.config import get_azure_devops_context_from_git_remote

        result = get_azure_devops_context_from_git_remote()
        assert result == ("https://dev.azure.com/swica", "DragonflyMgmt", "dfly-platform-management")

    def test_returns_none_for_non_azure_devops_remote(self, monkeypatch):
        """Test returning None for non-Azure-DevOps remotes."""
        import subprocess

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = "https://github.com/ayaiayorg/agentic-devtools.git"
                returncode = 0

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        from agentic_devtools.cli.azure_devops.config import get_azure_devops_context_from_git_remote

        result = get_azure_devops_context_from_git_remote()
        assert result is None
