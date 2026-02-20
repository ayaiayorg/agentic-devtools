"""Tests for azure devops config."""

from agentic_devtools import state
from agentic_devtools.cli import azure_devops


class TestAzureDevOpsConfig:
    """Tests for AzureDevOpsConfig dataclass."""

    def test_from_state_defaults(self, temp_state_dir, clear_state_before, monkeypatch):
        """Test config uses defaults when state is empty and git detection fails."""
        import subprocess

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
        assert "test//TestProject" not in url


class TestConfigurationOverrides:
    """Tests for configuration overrides via state."""

    def test_organization_override(self, temp_state_dir, clear_state_before, capsys):
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_value("content", "Test")
        state.set_value("organization", "https://dev.azure.com/custom")
        state.set_dry_run(True)
        azure_devops.reply_to_pull_request_thread()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out

    def test_project_override(self, temp_state_dir, clear_state_before, capsys):
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_value("content", "Test")
        state.set_value("project", "CustomProject")
        state.set_dry_run(True)
        azure_devops.reply_to_pull_request_thread()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out

    def test_repository_override(self, temp_state_dir, clear_state_before, capsys):
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_value("content", "Test")
        state.set_value("repository", "custom-repo")
        state.set_dry_run(True)
        azure_devops.reply_to_pull_request_thread()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
