"""Tests for fetch_pr_details_node."""

from unittest.mock import patch

from agentic_devtools.orchestration.review.nodes import fetch_pr_details_node


class TestFetchPrDetailsNode:
    """Tests for fetch_pr_details_node."""

    def test_returns_error_when_no_pr_id(self):
        """Returns failure when pr_id is missing from state."""
        result = fetch_pr_details_node({})
        assert result["status"] == "failed"
        assert "No pr_id" in result["error"]

    def test_returns_error_on_api_failure(self):
        """Returns failure when API call raises exception."""
        with patch(
            "agentic_devtools.cli.azure_devops.helpers.get_pull_request_details",
            side_effect=Exception("Connection error"),
        ):
            result = fetch_pr_details_node({"pr_id": 123})
            assert result["status"] == "failed"
            assert "Connection error" in result["error"]

    def test_returns_error_when_pr_not_found(self):
        """Returns failure when PR details are None/empty."""
        with patch(
            "agentic_devtools.cli.azure_devops.helpers.get_pull_request_details",
            return_value=None,
        ):
            result = fetch_pr_details_node({"pr_id": 999})
            assert result["status"] == "failed"
            assert "not found" in result["error"]

    def test_extracts_pr_details_correctly(self):
        """Extracts title, branches, and changed files from API response."""
        mock_details = {
            "title": "Add feature X",
            "description": "Implements feature X",
            "sourceRefName": "refs/heads/feature/x",
            "targetRefName": "refs/heads/main",
            "changes": [
                {"item": {"path": "/src/feature.py"}},
                {"item": {"path": "/tests/test_feature.py"}},
            ],
        }

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.get_pull_request_details",
            return_value=mock_details,
        ):
            result = fetch_pr_details_node({"pr_id": 123})
            assert result["status"] == "active"
            assert result["pr_title"] == "Add feature X"
            assert result["source_branch"] == "feature/x"
            assert result["target_branch"] == "main"
            assert "/src/feature.py" in result["changed_files"]
            assert "/tests/test_feature.py" in result["changed_files"]

    def test_returns_error_when_changes_not_in_details(self):
        """Falls back to iteration changes when details payload omits changes."""
        mock_details = {
            "title": "Add feature X",
            "description": "Implements feature X",
            "sourceRefName": "refs/heads/feature/x",
            "targetRefName": "refs/heads/main",
        }

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.get_pull_request_details",
            return_value=mock_details,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.helpers.get_pull_request_changed_files",
                return_value=["/src/feature.py"],
            ):
                result = fetch_pr_details_node({"pr_id": 123})
                assert result["status"] == "active"
                assert result["changed_files"] == ["/src/feature.py"]

    def test_returns_error_when_changes_unavailable_in_details_and_iterations(self):
        """Returns failure when neither details nor iteration API provide file changes."""
        mock_details = {
            "title": "Add feature X",
            "description": "Implements feature X",
            "sourceRefName": "refs/heads/feature/x",
            "targetRefName": "refs/heads/main",
        }

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.get_pull_request_details",
            return_value=mock_details,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.helpers.get_pull_request_changed_files",
                return_value=[],
            ):
                result = fetch_pr_details_node({"pr_id": 123})
                assert result["status"] == "failed"
                assert "Changed files are not available" in result["error"]
