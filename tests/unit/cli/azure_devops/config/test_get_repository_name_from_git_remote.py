"""Tests for get repository name from git remote."""
from agentic_devtools import state
from agentic_devtools.cli import azure_devops


class TestRepositoryDetection:
    """Tests for repository name detection from git remote."""

    def test_get_repository_name_from_azure_devops_url(self, monkeypatch):
        """Test extracting repository name from Azure DevOps URL."""
        import subprocess

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = "https://dev.azure.com/swica/DragonflyMgmt/_git/dfly-platform-management"
                returncode = 0

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        from agentic_devtools.cli.azure_devops.config import get_repository_name_from_git_remote

        result = get_repository_name_from_git_remote()
        assert result == "dfly-platform-management"

    def test_get_repository_name_from_azure_devops_url_with_query(self, monkeypatch):
        """Test extracting repository name from Azure DevOps URL with query string."""
        import subprocess

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = "https://dev.azure.com/swica/DragonflyMgmt/_git/dfly-platform-management?version=GBmain"
                returncode = 0

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        from agentic_devtools.cli.azure_devops.config import get_repository_name_from_git_remote

        result = get_repository_name_from_git_remote()
        assert result == "dfly-platform-management"

    def test_get_repository_name_from_github_https(self, monkeypatch):
        """Test extracting repository name from GitHub HTTPS URL."""
        import subprocess

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = "https://github.com/ayaiayorg/agentic-devtools.git"
                returncode = 0

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        from agentic_devtools.cli.azure_devops.config import get_repository_name_from_git_remote

        result = get_repository_name_from_git_remote()
        assert result == "agentic-devtools"

    def test_get_repository_name_from_github_https_no_git(self, monkeypatch):
        """Test extracting repository name from GitHub HTTPS URL without .git."""
        import subprocess

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = "https://github.com/ayaiayorg/agentic-devtools"
                returncode = 0

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        from agentic_devtools.cli.azure_devops.config import get_repository_name_from_git_remote

        result = get_repository_name_from_git_remote()
        assert result == "agentic-devtools"

    def test_get_repository_name_from_github_ssh(self, monkeypatch):
        """Test extracting repository name from GitHub SSH URL."""
        import subprocess

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = "git@github.com:ayaiayorg/agentic-devtools.git"
                returncode = 0

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        from agentic_devtools.cli.azure_devops.config import get_repository_name_from_git_remote

        result = get_repository_name_from_git_remote()
        assert result == "agentic-devtools"

    def test_get_repository_name_from_azure_devops_ssh(self, monkeypatch):
        """Test extracting repository name from Azure DevOps SSH URL (new format)."""
        import subprocess

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = "git@ssh.dev.azure.com:v3/swica/DragonflyMgmt/dfly-platform-management"
                returncode = 0

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        from agentic_devtools.cli.azure_devops.config import get_repository_name_from_git_remote

        result = get_repository_name_from_git_remote()
        assert result == "dfly-platform-management"

    def test_get_repository_name_from_azure_devops_ssh_legacy(self, monkeypatch):
        """Test extracting repository name from Azure DevOps SSH URL (legacy visualstudio.com format)."""
        import subprocess

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = "swica@vs-ssh.visualstudio.com:v3/swica/DragonflyMgmt/dfly-platform-management"
                returncode = 0

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        from agentic_devtools.cli.azure_devops.config import get_repository_name_from_git_remote

        result = get_repository_name_from_git_remote()
        assert result == "dfly-platform-management"

    def test_get_repository_name_from_azure_devops_ssh_with_git_suffix(self, monkeypatch):
        """Test extracting repository name from Azure DevOps SSH URL with .git suffix."""
        import subprocess

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = "git@ssh.dev.azure.com:v3/swica/DragonflyMgmt/dfly-platform-management.git"
                returncode = 0

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        from agentic_devtools.cli.azure_devops.config import get_repository_name_from_git_remote

        result = get_repository_name_from_git_remote()
        assert result == "dfly-platform-management"

    def test_get_repository_name_git_command_fails(self, monkeypatch):
        """Test returns None when git command fails."""
        import subprocess

        def mock_run(*args, **kwargs):
            raise subprocess.CalledProcessError(128, "git")

        monkeypatch.setattr(subprocess, "run", mock_run)

        from agentic_devtools.cli.azure_devops.config import get_repository_name_from_git_remote

        result = get_repository_name_from_git_remote()
        assert result is None

    def test_get_repository_name_git_not_available(self, monkeypatch):
        """Test returns None when git is not available."""
        import subprocess

        def mock_run(*args, **kwargs):
            raise FileNotFoundError()

        monkeypatch.setattr(subprocess, "run", mock_run)

        from agentic_devtools.cli.azure_devops.config import get_repository_name_from_git_remote

        result = get_repository_name_from_git_remote()
        assert result is None

    def test_get_repository_name_empty_url(self, monkeypatch):
        """Test returns None when git returns empty URL."""
        import subprocess

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = ""
                returncode = 0

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        from agentic_devtools.cli.azure_devops.config import get_repository_name_from_git_remote

        result = get_repository_name_from_git_remote()
        assert result is None

    def test_get_repository_name_unsupported_url(self, monkeypatch):
        """Test returns None for unsupported URL format."""
        import subprocess

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = "https://gitlab.com/owner/repo.git"
                returncode = 0

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        from agentic_devtools.cli.azure_devops.config import get_repository_name_from_git_remote

        result = get_repository_name_from_git_remote()
        assert result is None

    def test_from_state_uses_git_remote_when_no_state(self, temp_state_dir, clear_state_before, monkeypatch):
        """Test config uses git remote URL when state repository is not set."""
        import subprocess

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = "https://dev.azure.com/swica/DragonflyMgmt/_git/dfly-platform-management"
                returncode = 0

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        config = azure_devops.AzureDevOpsConfig.from_state()
        assert config.repository == "dfly-platform-management"

    def test_from_state_prefers_state_over_git(self, temp_state_dir, clear_state_before, monkeypatch):
        """Test config prefers state value over git remote."""
        import subprocess

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = "https://dev.azure.com/swica/DragonflyMgmt/_git/dfly-platform-management"
                returncode = 0

            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        state.set_value("repository", "custom-repo")
        config = azure_devops.AzureDevOpsConfig.from_state()
        assert config.repository == "custom-repo"

    def test_from_state_falls_back_to_default_when_git_fails(
        self, temp_state_dir, clear_state_before, monkeypatch
    ):
        """Test config falls back to default when git command fails."""
        import subprocess

        def mock_run(*args, **kwargs):
            raise subprocess.CalledProcessError(128, "git")

        monkeypatch.setattr(subprocess, "run", mock_run)

        config = azure_devops.AzureDevOpsConfig.from_state()
        assert config.repository == azure_devops.DEFAULT_REPOSITORY
