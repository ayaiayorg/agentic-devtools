"""Tests for the review_commands module and helper functions."""


class TestFetchPullRequestBasicInfo:
    """Tests for _fetch_pull_request_basic_info function."""

    def test_returns_pr_data_on_success(self):
        """Test returns PR data on successful az CLI call."""
        import json
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.azure_devops.config import AzureDevOpsConfig
        from agdt_ai_helpers.cli.azure_devops.review_commands import _fetch_pull_request_basic_info

        pr_data = {"pullRequestId": 123, "title": "Test PR"}
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(pr_data)

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.verify_az_cli"):
            with patch("agdt_ai_helpers.cli.azure_devops.review_commands.get_pat", return_value="test-pat"):
                with patch("agdt_ai_helpers.cli.azure_devops.review_commands.run_safe", return_value=mock_result):
                    result = _fetch_pull_request_basic_info(123, config)

        assert result is not None
        assert result["pullRequestId"] == 123

    def test_returns_none_on_cli_failure(self):
        """Test returns None when az CLI fails."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.azure_devops.config import AzureDevOpsConfig
        from agdt_ai_helpers.cli.azure_devops.review_commands import _fetch_pull_request_basic_info

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.verify_az_cli"):
            with patch("agdt_ai_helpers.cli.azure_devops.review_commands.get_pat", return_value="test-pat"):
                with patch("agdt_ai_helpers.cli.azure_devops.review_commands.run_safe", return_value=mock_result):
                    result = _fetch_pull_request_basic_info(123, config)

        assert result is None

    def test_returns_none_on_invalid_json(self):
        """Test returns None when output is not valid JSON."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.azure_devops.config import AzureDevOpsConfig
        from agdt_ai_helpers.cli.azure_devops.review_commands import _fetch_pull_request_basic_info

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json"

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.verify_az_cli"):
            with patch("agdt_ai_helpers.cli.azure_devops.review_commands.get_pat", return_value="test-pat"):
                with patch("agdt_ai_helpers.cli.azure_devops.review_commands.run_safe", return_value=mock_result):
                    result = _fetch_pull_request_basic_info(123, config)

        assert result is None
