"""Tests for get_pull_request_changed_files function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli import azure_devops
from agentic_devtools.cli.azure_devops.config import API_VERSION, PR_ITERATION_CHANGES_API_VERSION
from agentic_devtools.cli.azure_devops.helpers import get_pull_request_changed_files


class TestGetPullRequestChangedFiles:
    """Tests for get_pull_request_changed_files function."""

    def test_returns_changed_files_from_latest_iteration(self):
        """Returns file paths from changeEntries in the latest iteration."""
        mock_requests = MagicMock()
        iterations_response = MagicMock()
        iterations_response.status_code = 200
        iterations_response.json.return_value = {"value": [{"id": 1}, {"id": 3}, {"id": 2}]}
        changes_response = MagicMock()
        changes_response.status_code = 200
        changes_response.json.return_value = {
            "changeEntries": [
                {"item": {"path": "/src/main.py"}},
                {"item": {"path": "/tests/test_main.py"}},
                {"item": {}},
                {},
                "invalid-entry",
            ]
        }
        mock_requests.get.side_effect = [iterations_response, changes_response]

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with (
            patch(
                "agentic_devtools.cli.azure_devops.helpers.require_requests",
                return_value=mock_requests,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                return_value="repo-id-123",
            ),
        ):
            result = get_pull_request_changed_files(123, config=config, headers=headers)

        assert result == ["/src/main.py", "/tests/test_main.py"]

    def test_uses_default_config_and_headers_when_not_provided(self):
        """Loads config and auth headers when optional args are omitted."""
        mock_requests = MagicMock()
        iterations_response = MagicMock()
        iterations_response.status_code = 200
        iterations_response.json.return_value = {"value": []}
        mock_requests.get.return_value = iterations_response

        with (
            patch(
                "agentic_devtools.cli.azure_devops.helpers.require_requests",
                return_value=mock_requests,
            ),
            patch.object(
                azure_devops.AzureDevOpsConfig,
                "from_state",
                side_effect=lambda: azure_devops.AzureDevOpsConfig(
                    organization="https://dev.azure.com/test",
                    project="TestProject",
                    repository="test-repo",
                ),
            ) as mock_from_state,
            patch(
                "agentic_devtools.cli.azure_devops.auth.get_pat",
                return_value="pat",
            ) as mock_get_pat,
            patch(
                "agentic_devtools.cli.azure_devops.auth.get_auth_headers",
                return_value={"Authorization": "Basic xyz"},
            ) as mock_get_auth_headers,
            patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                return_value="repo-id-123",
            ),
        ):
            result = get_pull_request_changed_files(123)

        assert result == []
        mock_from_state.assert_called_once_with()
        mock_get_pat.assert_called_once_with()
        mock_get_auth_headers.assert_called_once_with("pat")

    def test_returns_empty_list_when_no_iterations(self):
        """Returns empty list when PR has no iterations."""
        mock_requests = MagicMock()
        iterations_response = MagicMock()
        iterations_response.status_code = 200
        iterations_response.json.return_value = {"value": []}
        mock_requests.get.return_value = iterations_response

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with (
            patch(
                "agentic_devtools.cli.azure_devops.helpers.require_requests",
                return_value=mock_requests,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                return_value="repo-id-123",
            ),
        ):
            result = get_pull_request_changed_files(123, config=config, headers=headers)

        assert result == []

    def test_returns_empty_list_when_latest_iteration_id_invalid(self):
        """Returns empty list when iterations do not contain a valid ID."""
        mock_requests = MagicMock()
        iterations_response = MagicMock()
        iterations_response.status_code = 200
        iterations_response.json.return_value = {"value": [{"id": 0}]}
        mock_requests.get.return_value = iterations_response

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with (
            patch(
                "agentic_devtools.cli.azure_devops.helpers.require_requests",
                return_value=mock_requests,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                return_value="repo-id-123",
            ),
        ):
            result = get_pull_request_changed_files(123, config=config, headers=headers)

        assert result == []

    def test_returns_none_on_http_errors(self):
        """Returns None when iterations or changes endpoint returns non-200."""
        mock_requests = MagicMock()
        iterations_error = MagicMock()
        iterations_error.status_code = 500
        mock_requests.get.return_value = iterations_error

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with (
            patch(
                "agentic_devtools.cli.azure_devops.helpers.require_requests",
                return_value=mock_requests,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                return_value="repo-id-123",
            ),
        ):
            iterations_result = get_pull_request_changed_files(
                123,
                config=config,
                headers=headers,
            )

        assert iterations_result is None

        mock_requests = MagicMock()
        iterations_ok = MagicMock()
        iterations_ok.status_code = 200
        iterations_ok.json.return_value = {"value": [{"id": 1}]}
        changes_error = MagicMock()
        changes_error.status_code = 500
        mock_requests.get.side_effect = [iterations_ok, changes_error]

        with (
            patch(
                "agentic_devtools.cli.azure_devops.helpers.require_requests",
                return_value=mock_requests,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                return_value="repo-id-123",
            ),
        ):
            changes_result = get_pull_request_changed_files(
                123,
                config=config,
                headers=headers,
            )

        assert changes_result is None

    def test_returns_none_when_repo_lookup_or_request_fails(self):
        """Returns None when repo lookup or HTTP call raises exception."""
        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with (
            patch(
                "agentic_devtools.cli.azure_devops.helpers.require_requests",
                return_value=MagicMock(),
            ),
            patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                side_effect=RuntimeError("failed"),
            ),
        ):
            repo_error_result = get_pull_request_changed_files(
                123,
                config=config,
                headers=headers,
            )

        assert repo_error_result is None

        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("timeout")
        with (
            patch(
                "agentic_devtools.cli.azure_devops.helpers.require_requests",
                return_value=mock_requests,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                return_value="repo-id-123",
            ),
        ):
            request_error_result = get_pull_request_changed_files(
                123,
                config=config,
                headers=headers,
            )

        assert request_error_result is None

    def test_normalizes_organization_and_project_in_request_urls(self):
        """Builds URLs with normalized org and percent-encoded project."""
        mock_requests = MagicMock()
        iterations_response = MagicMock()
        iterations_response.status_code = 200
        iterations_response.json.return_value = {"value": [{"id": 2}]}
        changes_response = MagicMock()
        changes_response.status_code = 200
        changes_response.json.return_value = {"changeEntries": [{"item": {"path": "/src/main.py"}}]}
        mock_requests.get.side_effect = [iterations_response, changes_response]

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test-org/",
            project="Proj Name",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with (
            patch(
                "agentic_devtools.cli.azure_devops.helpers.require_requests",
                return_value=mock_requests,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                return_value="repo-id-123",
            ),
        ):
            result = get_pull_request_changed_files(123, config=config, headers=headers)

        assert result == ["/src/main.py"]
        first_url = mock_requests.get.call_args_list[0].args[0]
        second_url = mock_requests.get.call_args_list[1].args[0]
        assert first_url.startswith("https://dev.azure.com/test-org/Proj%20Name/_apis/git/repositories/repo-id-123/")
        assert second_url.startswith("https://dev.azure.com/test-org/Proj%20Name/_apis/git/repositories/repo-id-123/")
        assert first_url.endswith(f"/pullrequests/123/iterations?api-version={API_VERSION}")
        assert second_url.endswith(
            f"/pullrequests/123/iterations/2/changes?api-version={PR_ITERATION_CHANGES_API_VERSION}"
        )
