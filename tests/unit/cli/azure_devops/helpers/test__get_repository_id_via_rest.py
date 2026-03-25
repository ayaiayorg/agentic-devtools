"""Tests for _get_repository_id_via_rest helper."""

from unittest.mock import MagicMock, patch

import pytest


class TestGetRepositoryIdViaRest:
    """Tests for _get_repository_id_via_rest function."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    def test_returns_repo_id_on_success(self):
        """Test successful REST repository ID lookup."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "repo-guid-abc"}

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch("agentic_devtools.cli.azure_devops.helpers.require_requests", return_value=mock_requests):
            from agentic_devtools.cli.azure_devops.helpers import _get_repository_id_via_rest

            result = _get_repository_id_via_rest(
                organization="https://dev.azure.com/myorg",
                project="MyProject",
                repository="my-repo",
            )

        assert result == "repo-guid-abc"
        mock_requests.get.assert_called_once()
        call_url = mock_requests.get.call_args[0][0]
        assert "MyProject/_apis/git/repositories/my-repo" in call_url

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    def test_raises_on_non_200_status(self):
        """Test raises RuntimeError on non-200 response."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch("agentic_devtools.cli.azure_devops.helpers.require_requests", return_value=mock_requests):
            from agentic_devtools.cli.azure_devops.helpers import _get_repository_id_via_rest

            with pytest.raises(RuntimeError, match="REST API returned 404"):
                _get_repository_id_via_rest(
                    organization="https://dev.azure.com/myorg",
                    project="MyProject",
                    repository="missing-repo",
                )

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    def test_raises_when_response_missing_id(self):
        """Test raises RuntimeError when response has no id field."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "my-repo"}

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch("agentic_devtools.cli.azure_devops.helpers.require_requests", return_value=mock_requests):
            from agentic_devtools.cli.azure_devops.helpers import _get_repository_id_via_rest

            with pytest.raises(RuntimeError, match="did not include a repository id"):
                _get_repository_id_via_rest(
                    organization="https://dev.azure.com/myorg",
                    project="MyProject",
                    repository="my-repo",
                )

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    def test_url_encodes_project_and_repository(self):
        """Test that project and repository names are URL-encoded."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "repo-guid"}

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch("agentic_devtools.cli.azure_devops.helpers.require_requests", return_value=mock_requests):
            from agentic_devtools.cli.azure_devops.helpers import _get_repository_id_via_rest

            _get_repository_id_via_rest(
                organization="https://dev.azure.com/myorg",
                project="My Project",
                repository="my repo",
            )

        call_url = mock_requests.get.call_args[0][0]
        assert "My%20Project" in call_url
        assert "my%20repo" in call_url

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    def test_strips_trailing_slash_from_organization(self):
        """Test that trailing slash in organization URL is stripped."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "repo-guid"}

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch("agentic_devtools.cli.azure_devops.helpers.require_requests", return_value=mock_requests):
            from agentic_devtools.cli.azure_devops.helpers import _get_repository_id_via_rest

            _get_repository_id_via_rest(
                organization="https://dev.azure.com/myorg/",
                project="MyProject",
                repository="my-repo",
            )

        call_url = mock_requests.get.call_args[0][0]
        assert "myorg//MyProject" not in call_url
        assert "myorg/MyProject" in call_url

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    def test_raises_on_empty_response_body(self):
        """Test raises RuntimeError with descriptive message on empty response body."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = ""

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch("agentic_devtools.cli.azure_devops.helpers.require_requests", return_value=mock_requests):
            from agentic_devtools.cli.azure_devops.helpers import _get_repository_id_via_rest

            with pytest.raises(RuntimeError, match="No response body"):
                _get_repository_id_via_rest(
                    organization="https://dev.azure.com/myorg",
                    project="MyProject",
                    repository="my-repo",
                )
