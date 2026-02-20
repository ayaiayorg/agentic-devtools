"""Tests for the review_commands module and helper functions."""


class TestGetLinkedPullRequestFromJira:
    """Tests for _get_linked_pull_request_from_jira function."""

    def test_returns_none_when_requests_not_available(self):
        """Test returns None when requests library is not available."""
        from unittest.mock import patch

        with patch.dict("sys.modules", {"requests": None}):
            # Force reimport to trigger ImportError
            import importlib

            from agdt_ai_helpers.cli.azure_devops import review_commands

            importlib.reload(review_commands)
            from agdt_ai_helpers.cli.azure_devops.review_commands import (
                _get_linked_pull_request_from_jira,
            )

            result = _get_linked_pull_request_from_jira("DFLY-1234")
            assert result is None
            # Reload again to restore normal state
            importlib.reload(review_commands)

    def test_returns_none_when_jira_module_not_available(self):
        """Test returns None when Jira module imports fail."""
        from unittest.mock import MagicMock, patch

        with patch.dict("sys.modules", {"requests": MagicMock()}):
            # Mock Jira module import failure
            with patch(
                "agdt_ai_helpers.cli.azure_devops.review_commands._get_linked_pull_request_from_jira"
            ) as mock_func:
                mock_func.return_value = None
                from agdt_ai_helpers.cli.azure_devops.review_commands import (
                    _get_linked_pull_request_from_jira,
                )

                result = _get_linked_pull_request_from_jira("DFLY-1234")
                assert result is None

    def test_returns_none_on_issue_fetch_error(self):
        """Test returns None when Jira issue fetch fails."""
        from unittest.mock import MagicMock, patch

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("requests.get", return_value=mock_response):
            with patch(
                "agdt_ai_helpers.cli.jira.config.get_jira_base_url",
                return_value="https://jira.example.com",
            ):
                with patch(
                    "agdt_ai_helpers.cli.jira.config.get_jira_headers",
                    return_value={"Authorization": "Bearer token"},
                ):
                    with patch(
                        "agdt_ai_helpers.cli.jira.helpers._get_ssl_verify",
                        return_value=True,
                    ):
                        from agdt_ai_helpers.cli.azure_devops.review_commands import (
                            _get_linked_pull_request_from_jira,
                        )

                        result = _get_linked_pull_request_from_jira("DFLY-1234")
                        assert result is None

    def test_returns_none_on_network_exception(self):
        """Test returns None when network exception occurs."""
        from unittest.mock import patch

        with patch("requests.get", side_effect=Exception("Network error")):
            with patch(
                "agdt_ai_helpers.cli.jira.config.get_jira_base_url",
                return_value="https://jira.example.com",
            ):
                with patch(
                    "agdt_ai_helpers.cli.jira.config.get_jira_headers",
                    return_value={"Authorization": "Bearer token"},
                ):
                    with patch(
                        "agdt_ai_helpers.cli.jira.helpers._get_ssl_verify",
                        return_value=True,
                    ):
                        from agdt_ai_helpers.cli.azure_devops.review_commands import (
                            _get_linked_pull_request_from_jira,
                        )

                        result = _get_linked_pull_request_from_jira("DFLY-1234")
                        assert result is None

    def test_returns_pr_id_from_remote_links(self):
        """Test extracts PR ID from remote links."""
        from unittest.mock import MagicMock, patch

        issue_response = MagicMock()
        issue_response.status_code = 200

        links_response = MagicMock()
        links_response.status_code = 200
        links_response.json.return_value = [
            {"object": {"url": "https://dev.azure.com/org/project/_git/repo/pullrequest/456"}}
        ]

        def mock_get(url, **kwargs):
            if "remotelink" in url:
                return links_response
            return issue_response

        with patch("requests.get", side_effect=mock_get):
            with patch(
                "agdt_ai_helpers.cli.jira.config.get_jira_base_url",
                return_value="https://jira.example.com",
            ):
                with patch(
                    "agdt_ai_helpers.cli.jira.config.get_jira_headers",
                    return_value={"Authorization": "Bearer token"},
                ):
                    with patch(
                        "agdt_ai_helpers.cli.jira.helpers._get_ssl_verify",
                        return_value=True,
                    ):
                        from agdt_ai_helpers.cli.azure_devops.review_commands import (
                            _get_linked_pull_request_from_jira,
                        )

                        result = _get_linked_pull_request_from_jira("DFLY-1234")
                        assert result == 456

    def test_returns_pr_id_from_visualstudio_url(self):
        """Test extracts PR ID from visualstudio.com URL."""
        from unittest.mock import MagicMock, patch

        issue_response = MagicMock()
        issue_response.status_code = 200

        links_response = MagicMock()
        links_response.status_code = 200
        links_response.json.return_value = [
            {"object": {"url": "https://org.visualstudio.com/project/_git/repo/pullrequests/789"}}
        ]

        def mock_get(url, **kwargs):
            if "remotelink" in url:
                return links_response
            return issue_response

        with patch("requests.get", side_effect=mock_get):
            with patch(
                "agdt_ai_helpers.cli.jira.config.get_jira_base_url",
                return_value="https://jira.example.com",
            ):
                with patch(
                    "agdt_ai_helpers.cli.jira.config.get_jira_headers",
                    return_value={"Authorization": "Bearer token"},
                ):
                    with patch(
                        "agdt_ai_helpers.cli.jira.helpers._get_ssl_verify",
                        return_value=True,
                    ):
                        from agdt_ai_helpers.cli.azure_devops.review_commands import (
                            _get_linked_pull_request_from_jira,
                        )

                        result = _get_linked_pull_request_from_jira("DFLY-1234")
                        assert result == 789

    def test_returns_none_when_no_matching_links(self):
        """Test returns None when no Azure DevOps PR links found."""
        from unittest.mock import MagicMock, patch

        issue_response = MagicMock()
        issue_response.status_code = 200

        links_response = MagicMock()
        links_response.status_code = 200
        links_response.json.return_value = [
            {"object": {"url": "https://github.com/org/repo/pull/123"}}  # Not Azure DevOps
        ]

        def mock_get(url, **kwargs):
            if "remotelink" in url:
                return links_response
            return issue_response

        with patch("requests.get", side_effect=mock_get):
            with patch(
                "agdt_ai_helpers.cli.jira.config.get_jira_base_url",
                return_value="https://jira.example.com",
            ):
                with patch(
                    "agdt_ai_helpers.cli.jira.config.get_jira_headers",
                    return_value={"Authorization": "Bearer token"},
                ):
                    with patch(
                        "agdt_ai_helpers.cli.jira.helpers._get_ssl_verify",
                        return_value=True,
                    ):
                        from agdt_ai_helpers.cli.azure_devops.review_commands import (
                            _get_linked_pull_request_from_jira,
                        )

                        result = _get_linked_pull_request_from_jira("DFLY-1234")
                        assert result is None
