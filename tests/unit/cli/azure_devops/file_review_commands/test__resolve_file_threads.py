"""Tests for _resolve_file_threads."""

from unittest.mock import MagicMock

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.file_review_commands import _resolve_file_threads


def _make_config() -> AzureDevOpsConfig:
    return AzureDevOpsConfig(
        organization="https://dev.azure.com/testorg",
        project="Test Project",
        repository="testrepo",
    )


class TestResolveFileThreads:
    """Tests for _resolve_file_threads."""

    def test_returns_zero_for_blank_target_path(self):
        """Blank target paths should short-circuit without API calls."""
        requests = MagicMock()

        assert _resolve_file_threads(requests, {}, _make_config(), "repo-id", 42, "   ") == 0
        requests.get.assert_not_called()

    def test_returns_zero_when_thread_fetch_fails(self, capsys):
        """Request failures while fetching threads should warn and return zero."""
        requests = MagicMock()
        response = MagicMock()
        response.raise_for_status.side_effect = RuntimeError("boom")
        requests.get.return_value = response

        assert _resolve_file_threads(requests, {}, _make_config(), "repo-id", 42, "src/app.py") == 0
        assert "Failed to retrieve threads" in capsys.readouterr().err

    def test_reports_when_no_matching_unresolved_threads_exist(self, capsys):
        """Only active or pending threads for the target file should be considered."""
        requests = MagicMock()
        response = MagicMock()
        response.json.return_value = {
            "value": [
                {"id": 1, "status": "closed", "threadContext": {"filePath": "/src/app.py"}},
                {"id": 2, "status": "active", "threadContext": {"filePath": "/src/other.py"}},
            ]
        }
        requests.get.return_value = response

        assert _resolve_file_threads(requests, {}, _make_config(), "repo-id", 42, "src/app.py") == 0
        assert "No unresolved comment threads to resolve" in capsys.readouterr().out
        requests.patch.assert_not_called()

    def test_dry_run_counts_matching_threads_without_patch(self, capsys):
        """Dry-run mode should count matching threads but avoid PATCH requests."""
        requests = MagicMock()
        response = MagicMock()
        response.json.return_value = {
            "value": [
                {"id": 1, "status": "active", "threadContext": {"filePath": "/src/app.py"}},
                {"id": 2, "status": "pending", "threadContext": {"filePath": "/src/app.py"}},
            ]
        }
        requests.get.return_value = response

        assert _resolve_file_threads(requests, {}, _make_config(), "repo-id", 42, "src/app.py", dry_run=True) == 2
        output = capsys.readouterr().out
        assert "Would resolve thread 1" in output
        assert "Would resolve thread 2" in output
        requests.patch.assert_not_called()

    def test_resolves_matching_threads_and_reports_partial_failures(self, capsys):
        """Matching threads should be PATCHed, with failures logged per thread."""
        requests = MagicMock()
        get_response = MagicMock()
        get_response.json.return_value = {
            "value": [
                {"id": 1, "status": "active", "threadContext": {"filePath": "/src/app.py"}},
                {"id": 2, "status": "pending", "threadContext": {"filePath": "/src/app.py"}},
                {"id": 3, "status": "active", "threadContext": {"filePath": "/src/other.py"}},
            ]
        }
        requests.get.return_value = get_response

        ok_response = MagicMock()
        fail_response = MagicMock()
        fail_response.raise_for_status.side_effect = RuntimeError("forbidden")
        requests.patch.side_effect = [ok_response, fail_response]

        assert _resolve_file_threads(requests, {}, _make_config(), "repo-id", 42, "src/app.py") == 1
        captured = capsys.readouterr()
        assert "Resolving 2 thread(s)" in captured.out
        assert "Comment threads for 'src/app.py' resolved." in captured.out
        assert "Failed to resolve thread 2" in captured.err
        assert requests.patch.call_count == 2
