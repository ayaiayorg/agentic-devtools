"""
Tests for Azure DevOps configuration and constants.
"""

from agentic_devtools import state
from agentic_devtools.cli import azure_devops


class TestConstants:
    """Tests for module constants."""

    def test_default_organization(self):
        """Test default organization URL."""
        assert azure_devops.DEFAULT_ORGANIZATION == "https://dev.azure.com/swica"

    def test_default_project(self):
        """Test default project."""
        assert azure_devops.DEFAULT_PROJECT == "DragonflyMgmt"

    def test_default_repository(self):
        """Test default repository."""
        assert azure_devops.DEFAULT_REPOSITORY == "agdt-platform-management"

    def test_approval_sentinel(self):
        """Test approval sentinel constant."""
        assert azure_devops.APPROVAL_SENTINEL == "--- APPROVED ---"

    def test_api_version(self):
        """Test API version constant."""
        assert azure_devops.API_VERSION == "7.0"


class TestAzureDevOpsConfig:
    """Tests for AzureDevOpsConfig dataclass."""

    def test_from_state_defaults(self, temp_state_dir, clear_state_before, monkeypatch):
        """Test config uses defaults when state is empty and git detection fails."""
        import subprocess

        # Mock git command to fail, forcing fallback to DEFAULT_REPOSITORY
        def mock_run(*args, **kwargs):
            raise subprocess.CalledProcessError(128, "git")

        monkeypatch.setattr(subprocess, "run", mock_run)

        config = azure_devops.AzureDevOpsConfig.from_state()
        assert config.organization == azure_devops.DEFAULT_ORGANIZATION
        assert config.project == azure_devops.DEFAULT_PROJECT
        assert config.repository == azure_devops.DEFAULT_REPOSITORY

    def test_from_state_with_overrides(self, temp_state_dir, clear_state_before):
        """Test config uses state values when set."""
        state.set_value("organization", "https://dev.azure.com/custom")
        state.set_value("project", "CustomProject")
        state.set_value("repository", "custom-repo")

        config = azure_devops.AzureDevOpsConfig.from_state()
        assert config.organization == "https://dev.azure.com/custom"
        assert config.project == "CustomProject"
        assert config.repository == "custom-repo"

    def test_build_api_url_simple(self):
        """Test building simple API URL."""
        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        url = config.build_api_url("repo-123", "pullRequests", "456")
        assert (
            url
            == "https://dev.azure.com/test/TestProject/_apis/git/repositories/repo-123/pullRequests/456?api-version=7.0"
        )

    def test_build_api_url_strips_trailing_slash(self):
        """Test that trailing slash in organization is stripped."""
        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test/",
            project="TestProject",
            repository="test-repo",
        )
        url = config.build_api_url("repo-123", "pullRequests")
        assert "test//TestProject" not in url  # No double slash


class TestConfigurationOverrides:
    """Tests for configuration overrides via state."""

    def test_organization_override(self, temp_state_dir, clear_state_before, capsys):
        """Test organization can be overridden."""
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_value("content", "Test")
        state.set_value("organization", "https://dev.azure.com/custom")
        state.set_dry_run(True)

        azure_devops.reply_to_pull_request_thread()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out

    def test_project_override(self, temp_state_dir, clear_state_before, capsys):
        """Test project can be overridden."""
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_value("content", "Test")
        state.set_value("project", "CustomProject")
        state.set_dry_run(True)

        azure_devops.reply_to_pull_request_thread()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out

    def test_repository_override(self, temp_state_dir, clear_state_before, capsys):
        """Test repository can be overridden."""
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_value("content", "Test")
        state.set_value("repository", "custom-repo")
        state.set_dry_run(True)

        azure_devops.reply_to_pull_request_thread()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out


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

