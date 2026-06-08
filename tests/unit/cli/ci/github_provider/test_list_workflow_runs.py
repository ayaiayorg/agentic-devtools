"""Tests for GitHubActionsProvider.list_workflow_runs()."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.reconciliation.models import WorkflowRun


def _mock_run_safe_response(data: dict):
    class _Result:
        returncode = 0
        stdout = json.dumps(data)
        stderr = ""

    return _Result()


class TestListWorkflowRuns:
    """Tests for GitHubActionsProvider.list_workflow_runs()."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_returns_workflow_runs(self, mock_run_safe) -> None:
        """Returns WorkflowRun instances from API response."""
        mock_run_safe.return_value = _mock_run_safe_response(
            {
                "workflow_runs": [
                    {
                        "id": 100,
                        "name": "CI",
                        "conclusion": "failure",
                        "run_attempt": 1,
                        "created_at": "2024-01-15T10:00:00Z",
                        "event": "push",
                        "head_branch": "main",
                        "html_url": "https://github.com/owner/repo/actions/runs/100",
                        "triggering_actor": {"login": "user1"},
                        "repository": {"full_name": "owner/repo"},
                    }
                ]
            }
        )

        provider = GitHubActionsProvider(repo="owner/repo")
        runs = provider.list_workflow_runs("ci.yml", window_hours=24)

        assert len(runs) == 1
        assert isinstance(runs[0], WorkflowRun)
        assert runs[0].id == 100
        assert runs[0].conclusion == "failure"
        assert runs[0].run_attempt == 1
        assert runs[0].triggering_actor == "user1"
        assert runs[0].repository_full_name == "owner/repo"

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_empty_workflow_runs(self, mock_run_safe) -> None:
        """Returns empty list when no runs found."""
        mock_run_safe.return_value = _mock_run_safe_response({"workflow_runs": []})

        provider = GitHubActionsProvider(repo="owner/repo")
        runs = provider.list_workflow_runs("ci.yml")

        assert runs == []

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_handles_missing_optional_fields(self, mock_run_safe) -> None:
        """Handles runs with missing optional fields gracefully."""
        mock_run_safe.return_value = _mock_run_safe_response(
            {
                "workflow_runs": [
                    {
                        "id": 200,
                        "name": "Build",
                        "conclusion": "cancelled",
                        "run_attempt": 2,
                        "created_at": "2024-01-15T12:00:00Z",
                        "event": "pull_request",
                        "head_branch": "feature",
                    }
                ]
            }
        )

        provider = GitHubActionsProvider(repo="owner/repo")
        runs = provider.list_workflow_runs("build.yml")

        assert len(runs) == 1
        assert runs[0].html_url == ""
        assert runs[0].triggering_actor == ""
        assert runs[0].repository_full_name == ""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_conclusion_none_defaults_to_empty(self, mock_run_safe) -> None:
        """Null conclusion in API response defaults to empty string."""
        mock_run_safe.return_value = _mock_run_safe_response(
            {
                "workflow_runs": [
                    {
                        "id": 300,
                        "name": "Test",
                        "conclusion": None,
                        "run_attempt": 1,
                        "created_at": "2024-01-15T10:00:00Z",
                        "event": "push",
                        "head_branch": "main",
                    }
                ]
            }
        )

        provider = GitHubActionsProvider(repo="owner/repo")
        runs = provider.list_workflow_runs("test.yml")

        assert runs[0].conclusion == ""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_pr_number_populated_from_pull_requests(self, mock_run_safe) -> None:
        """pr_number is populated from pull_requests[0].number in API response."""
        mock_run_safe.return_value = _mock_run_safe_response(
            {
                "workflow_runs": [
                    {
                        "id": 400,
                        "name": "CI",
                        "conclusion": "failure",
                        "run_attempt": 1,
                        "created_at": "2024-01-15T10:00:00Z",
                        "event": "pull_request",
                        "head_branch": "feature/my-branch",
                        "pull_requests": [{"number": 77, "url": "https://api.github.com/repos/o/r/pulls/77"}],
                    }
                ]
            }
        )

        provider = GitHubActionsProvider(repo="owner/repo")
        runs = provider.list_workflow_runs("ci.yml")

        assert len(runs) == 1
        assert runs[0].pr_number == 77

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_pr_number_zero_when_no_pull_requests(self, mock_run_safe) -> None:
        """pr_number defaults to 0 when pull_requests is absent or empty."""
        mock_run_safe.return_value = _mock_run_safe_response(
            {
                "workflow_runs": [
                    {
                        "id": 500,
                        "name": "CI",
                        "conclusion": "failure",
                        "run_attempt": 1,
                        "created_at": "2024-01-15T10:00:00Z",
                        "event": "push",
                        "head_branch": "main",
                        "pull_requests": [],
                    }
                ]
            }
        )

        provider = GitHubActionsProvider(repo="owner/repo")
        runs = provider.list_workflow_runs("ci.yml")

        assert runs[0].pr_number == 0

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_paginates_when_full_page_returned(self, mock_run_safe) -> None:
        """Fetches next page when current page has exactly 100 runs."""
        first_page_runs = [
            {
                "id": i,
                "name": "CI",
                "conclusion": "failure",
                "run_attempt": 1,
                "created_at": "2024-01-15T10:00:00Z",
                "event": "push",
                "head_branch": "main",
            }
            for i in range(1, 101)  # 100 runs on first page
        ]
        second_page_runs = [
            {
                "id": 101,
                "name": "CI",
                "conclusion": "failure",
                "run_attempt": 1,
                "created_at": "2024-01-15T11:00:00Z",
                "event": "push",
                "head_branch": "main",
            }
        ]

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _mock_run_safe_response({"workflow_runs": first_page_runs})
            return _mock_run_safe_response({"workflow_runs": second_page_runs})

        mock_run_safe.side_effect = side_effect

        provider = GitHubActionsProvider(repo="owner/repo")
        runs = provider.list_workflow_runs("ci.yml")

        assert len(runs) == 101
        assert mock_run_safe.call_count == 2

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_workflow_id_with_slash_is_percent_encoded(self, mock_run_safe) -> None:
        """Slashes in workflow_id are percent-encoded (%2F) in the API URL path."""
        mock_run_safe.return_value = _mock_run_safe_response({"workflow_runs": []})

        provider = GitHubActionsProvider(repo="owner/repo")
        provider.list_workflow_runs("org/ci.yml")

        cmd_list = mock_run_safe.call_args[0][0]
        endpoint_arg = next((a for a in cmd_list if "/actions/workflows/" in a), None)
        assert endpoint_arg is not None
        assert "%2F" in endpoint_arg, "Slash in workflow_id must be percent-encoded as %2F"
        assert "/org/ci.yml/" not in endpoint_arg, "Raw slash in workflow_id must not appear in URL path"

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_pr_number_zero_when_pull_request_missing_number_key(self, mock_run_safe) -> None:
        """pr_number defaults to 0 when pull_request object has no 'number' key."""
        mock_run_safe.return_value = _mock_run_safe_response(
            {
                "workflow_runs": [
                    {
                        "id": 600,
                        "name": "CI",
                        "conclusion": "failure",
                        "run_attempt": 1,
                        "created_at": "2024-01-15T10:00:00Z",
                        "event": "pull_request",
                        "head_branch": "feature",
                        "pull_requests": [{"url": "https://api.github.com/repos/o/r/pulls/99"}],
                    }
                ]
            }
        )

        provider = GitHubActionsProvider(repo="owner/repo")
        runs = provider.list_workflow_runs("ci.yml")

        assert runs[0].pr_number == 0
