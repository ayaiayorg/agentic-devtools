"""Tests for _build_pr_base_url helper."""

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.review_scaffold import _build_pr_base_url

_ORG = "https://dev.azure.com/testorg"
_PROJECT = "TestProject"
_REPO = "test-repo"


def _make_config(org=_ORG, project=_PROJECT, repo=_REPO) -> AzureDevOpsConfig:
    return AzureDevOpsConfig(organization=org, project=project, repository=repo)


class TestBuildPrBaseUrl:
    """Tests for _build_pr_base_url helper."""

    def test_builds_correct_url(self):
        """Builds the expected PR web URL."""
        config = _make_config()
        result = _build_pr_base_url(config, 42)
        assert result == f"{_ORG}/{_PROJECT}/_git/{_REPO}/pullRequest/42"

    def test_strips_trailing_slash_from_org(self):
        """Handles trailing slash in organization URL."""
        config = _make_config(org="https://dev.azure.com/testorg/")
        result = _build_pr_base_url(config, 1)
        assert result == f"https://dev.azure.com/testorg/{_PROJECT}/_git/{_REPO}/pullRequest/1"

    def test_normalizes_short_org_name(self):
        """Normalizes a short org name to a full Azure DevOps URL."""
        config = _make_config(org="myorg")
        result = _build_pr_base_url(config, 7)
        assert result == f"https://dev.azure.com/myorg/{_PROJECT}/_git/{_REPO}/pullRequest/7"

    def test_normalizes_short_org_name_with_leading_slash(self):
        """Strips leading slash from short org name during normalization."""
        config = _make_config(org="/myorg")
        result = _build_pr_base_url(config, 7)
        assert result == f"https://dev.azure.com/myorg/{_PROJECT}/_git/{_REPO}/pullRequest/7"

    def test_url_encodes_project_with_spaces(self):
        """URL-encodes project names containing spaces."""
        config = _make_config(project="My Project")
        result = _build_pr_base_url(config, 1)
        assert result == f"{_ORG}/My%20Project/_git/{_REPO}/pullRequest/1"

    def test_url_encodes_repo_with_spaces(self):
        """URL-encodes repository names containing spaces."""
        config = _make_config(repo="my repo")
        result = _build_pr_base_url(config, 1)
        assert result == f"{_ORG}/{_PROJECT}/_git/my%20repo/pullRequest/1"
