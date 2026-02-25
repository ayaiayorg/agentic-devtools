"""Tests for get_pull_request_source_branch function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.helpers import get_pull_request_source_branch


class TestGetPullRequestSourceBranch:
    """Tests for get_pull_request_source_branch function."""

    def test_returns_none_when_pr_not_found(self, mock_azure_devops_env):
        """Should return None when pull request details cannot be retrieved."""
        with patch(
            "agentic_devtools.cli.azure_devops.helpers.get_pull_request_details",
            return_value=None,
        ):
            result = get_pull_request_source_branch(pull_request_id=42)

        assert result is None

    def test_returns_branch_name_without_refs_prefix(self, mock_azure_devops_env):
        """Should return branch name stripped of refs/heads/ prefix."""
        pr_data = {
            "sourceRefName": "refs/heads/feature/my-branch",
            "pullRequestId": 42,
        }

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.get_pull_request_details",
            return_value=pr_data,
        ):
            result = get_pull_request_source_branch(pull_request_id=42)

        assert result == "feature/my-branch"

    def test_returns_none_when_no_source_ref(self, mock_azure_devops_env):
        """Should return None when PR data has no sourceRefName."""
        pr_data = {"pullRequestId": 42}

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.get_pull_request_details",
            return_value=pr_data,
        ):
            result = get_pull_request_source_branch(pull_request_id=42)

        assert result is None
