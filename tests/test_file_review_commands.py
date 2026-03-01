"""
Tests for file review commands.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_state(tmp_path):
    """Create a mock state environment."""
    with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def mock_requests():
    """Create a mock requests module."""
    mock = MagicMock()
    return mock


class TestNormalizeRepoPath:
    """Tests for _normalize_repo_path function."""

    def test_normalize_empty_path_returns_none(self):
        """Test that empty path returns None."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            _normalize_repo_path,
        )

        assert _normalize_repo_path(None) is None
        assert _normalize_repo_path("") is None
        assert _normalize_repo_path("   ") is None

    def test_normalize_backslashes_to_forward_slashes(self):
        """Test that backslashes are converted to forward slashes."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            _normalize_repo_path,
        )

        result = _normalize_repo_path("src\\components\\App.tsx")
        assert result == "/src/components/App.tsx"

    def test_normalize_strips_leading_trailing_slashes(self):
        """Test that leading and trailing slashes are handled."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            _normalize_repo_path,
        )

        result = _normalize_repo_path("/src/file.ts/")
        assert result == "/src/file.ts"

    def test_normalize_adds_leading_slash(self):
        """Test that a leading slash is added."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            _normalize_repo_path,
        )

        result = _normalize_repo_path("src/file.ts")
        assert result == "/src/file.ts"


class TestGetThreadFilePath:
    """Tests for _get_thread_file_path function."""

    def test_no_thread_context_returns_none(self):
        """Test that no thread context returns None."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            _get_thread_file_path,
        )

        assert _get_thread_file_path({}) is None
        assert _get_thread_file_path({"status": "active"}) is None

    def test_extracts_file_path_from_context(self):
        """Test extracting file path from thread context."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            _get_thread_file_path,
        )

        thread = {"threadContext": {"filePath": "/src/app.ts"}}
        assert _get_thread_file_path(thread) == "src/app.ts"

    def test_extracts_from_left_file_start(self):
        """Test extracting from leftFileStart."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            _get_thread_file_path,
        )

        thread = {"threadContext": {"leftFileStart": {"filePath": "/src/old.ts"}}}
        assert _get_thread_file_path(thread) == "src/old.ts"

    def test_extracts_from_right_file_start(self):
        """Test extracting from rightFileStart."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            _get_thread_file_path,
        )

        thread = {"threadContext": {"rightFileStart": {"filePath": "/src/new.ts"}}}
        assert _get_thread_file_path(thread) == "src/new.ts"

    def test_no_file_path_in_context_returns_none(self):
        """Test that empty file path in context returns None."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            _get_thread_file_path,
        )

        thread = {"threadContext": {}}
        assert _get_thread_file_path(thread) is None


class TestResolveFileThreads:
    """Tests for _resolve_file_threads function."""

    def test_returns_zero_for_empty_path(self, mock_requests):
        """Test that empty target path returns 0."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            _resolve_file_threads,
        )

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        result = _resolve_file_threads(mock_requests, {}, config, "repo-id", 123, "", dry_run=True)
        assert result == 0

    def test_handles_request_failure(self, mock_requests):
        """Test that request failures are handled gracefully."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            _resolve_file_threads,
        )

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        mock_requests.get.side_effect = Exception("Network error")

        result = _resolve_file_threads(mock_requests, {}, config, "repo-id", 123, "/src/file.ts", dry_run=False)
        assert result == 0

    def test_no_matching_threads_returns_zero(self, mock_requests):
        """Test that no matching threads returns 0."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            _resolve_file_threads,
        )

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_requests.get.return_value = mock_response

        result = _resolve_file_threads(mock_requests, {}, config, "repo-id", 123, "/src/file.ts", dry_run=False)
        assert result == 0

    def test_dry_run_counts_but_does_not_resolve(self, mock_requests):
        """Test that dry run counts threads but does not resolve them."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            _resolve_file_threads,
        )

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": 1,
                    "status": "active",
                    "threadContext": {"filePath": "/src/file.ts"},
                }
            ]
        }
        mock_requests.get.return_value = mock_response

        result = _resolve_file_threads(mock_requests, {}, config, "repo-id", 123, "/src/file.ts", dry_run=True)
        assert result == 1
        # patch should not be called in dry run
        mock_requests.patch.assert_not_called()

    def test_resolves_matching_threads(self, mock_requests):
        """Test that matching threads are resolved."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            _resolve_file_threads,
        )

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {
            "value": [
                {
                    "id": 1,
                    "status": "active",
                    "threadContext": {"filePath": "/src/file.ts"},
                },
                {
                    "id": 2,
                    "status": "pending",
                    "threadContext": {"filePath": "/src/file.ts"},
                },
                {
                    "id": 3,
                    "status": "closed",  # Should be ignored
                    "threadContext": {"filePath": "/src/file.ts"},
                },
                {
                    "id": 4,
                    "status": "active",
                    "threadContext": {"filePath": "/other/file.ts"},  # Different file
                },
            ]
        }
        mock_requests.get.return_value = mock_get_response

        mock_patch_response = MagicMock()
        mock_requests.patch.return_value = mock_patch_response

        result = _resolve_file_threads(mock_requests, {}, config, "repo-id", 123, "/src/file.ts", dry_run=False)
        assert result == 2
        assert mock_requests.patch.call_count == 2

    def test_handles_patch_failure(self, mock_requests):
        """Test that patch failures are handled gracefully."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            _resolve_file_threads,
        )

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
        )

        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {
            "value": [
                {
                    "id": 1,
                    "status": "active",
                    "threadContext": {"filePath": "/src/file.ts"},
                }
            ]
        }
        mock_requests.get.return_value = mock_get_response
        mock_requests.patch.side_effect = Exception("Failed to resolve")

        result = _resolve_file_threads(mock_requests, {}, config, "repo-id", 123, "/src/file.ts", dry_run=False)
        # Should still return 0 since patch failed
        assert result == 0


class TestApproveFile:
    """Tests for approve_file command."""

    def test_dry_run_prints_but_does_not_call_api(self, mock_state):
        """Test that dry run prints what would be done."""
        from agentic_devtools.cli.azure_devops.file_review_commands import approve_file
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "/src/app.ts")
        set_value("file_review.summary", "LGTM!")
        set_value("dry_run", True)
        set_value("ado.organization", "https://dev.azure.com/test")
        set_value("ado.project", "TestProject")
        set_value("ado.repository", "TestRepo")

        # Should not raise
        approve_file()

    def test_missing_file_path_exits(self, mock_state):
        """Test that missing file path causes exit."""
        from agentic_devtools.cli.azure_devops.file_review_commands import approve_file
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.summary", "LGTM!")
        set_value("ado.organization", "https://dev.azure.com/test")
        set_value("ado.project", "TestProject")
        set_value("ado.repository", "TestRepo")

        with pytest.raises(SystemExit):
            approve_file()

    def test_missing_content_exits(self, mock_state):
        """Test that missing summary/content causes exit."""
        from agentic_devtools.cli.azure_devops.file_review_commands import approve_file
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "/src/app.ts")
        set_value("ado.organization", "https://dev.azure.com/test")
        set_value("ado.project", "TestProject")
        set_value("ado.repository", "TestRepo")

        with pytest.raises(SystemExit):
            approve_file()


class TestSubmitFileReview:
    """Tests for submit_file_review command."""

    def test_dry_run_approve_outcome(self, mock_state):
        """Test dry run with Approve outcome."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            submit_file_review,
        )
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "/src/app.ts")
        set_value("file_review.outcome", "Approve")
        set_value("content", "LGTM!")
        set_value("dry_run", True)
        set_value("ado.organization", "https://dev.azure.com/test")
        set_value("ado.project", "TestProject")
        set_value("ado.repository", "TestRepo")

        # Should not raise
        submit_file_review()

    def test_dry_run_changes_outcome_with_line(self, mock_state):
        """Test dry run with Changes outcome and line."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            submit_file_review,
        )
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "/src/app.ts")
        set_value("file_review.outcome", "Changes")
        set_value("content", "Please fix this.")
        set_value("line", 42)
        set_value("end_line", 45)
        set_value("dry_run", True)
        set_value("ado.organization", "https://dev.azure.com/test")
        set_value("ado.project", "TestProject")
        set_value("ado.repository", "TestRepo")

        # Should not raise
        submit_file_review()

    def test_missing_file_path_exits(self, mock_state):
        """Test that missing file path causes exit."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            submit_file_review,
        )
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.outcome", "Approve")
        set_value("content", "LGTM!")
        set_value("ado.organization", "https://dev.azure.com/test")
        set_value("ado.project", "TestProject")
        set_value("ado.repository", "TestRepo")

        with pytest.raises(SystemExit):
            submit_file_review()

    def test_invalid_outcome_exits(self, mock_state):
        """Test that invalid outcome causes exit."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            submit_file_review,
        )
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "/src/app.ts")
        set_value("file_review.outcome", "Invalid")
        set_value("content", "Comment")
        set_value("ado.organization", "https://dev.azure.com/test")
        set_value("ado.project", "TestProject")
        set_value("ado.repository", "TestRepo")

        with pytest.raises(SystemExit):
            submit_file_review()

    def test_missing_content_exits(self, mock_state):
        """Test that missing content causes exit."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            submit_file_review,
        )
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "/src/app.ts")
        set_value("file_review.outcome", "Approve")
        set_value("ado.organization", "https://dev.azure.com/test")
        set_value("ado.project", "TestProject")
        set_value("ado.repository", "TestRepo")

        with pytest.raises(SystemExit):
            submit_file_review()

    def test_changes_without_line_exits(self, mock_state):
        """Test that Changes outcome without line causes exit."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            submit_file_review,
        )
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "/src/app.ts")
        set_value("file_review.outcome", "Changes")
        set_value("content", "Please fix this.")
        set_value("ado.organization", "https://dev.azure.com/test")
        set_value("ado.project", "TestProject")
        set_value("ado.repository", "TestRepo")

        with pytest.raises(SystemExit):
            submit_file_review()


class TestRequestChanges:
    """Tests for request_changes command."""

    def test_dry_run_prints_details(self, mock_state):
        """Test that dry run prints what would be done."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            request_changes,
        )
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "/src/app.ts")
        set_value("file_review.summary", "Please fix this issue.")
        set_value(
            "file_review.suggestions",
            '[{"line": 42, "severity": "high", "content": "Fix this"}]',
        )
        set_value("dry_run", True)
        set_value("ado.organization", "https://dev.azure.com/test")
        set_value("ado.project", "TestProject")
        set_value("ado.repository", "TestRepo")

        # Should not raise
        request_changes()

    def test_dry_run_with_line_range(self, mock_state):
        """Test dry run with line range."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            request_changes,
        )
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "/src/app.ts")
        set_value("file_review.summary", "Please fix this issue.")
        set_value(
            "file_review.suggestions",
            '[{"line": 42, "end_line": 50, "severity": "high", "content": "Fix this"}]',
        )
        set_value("dry_run", True)
        set_value("ado.organization", "https://dev.azure.com/test")
        set_value("ado.project", "TestProject")
        set_value("ado.repository", "TestRepo")

        # Should not raise
        request_changes()

    def test_missing_file_path_exits(self, mock_state):
        """Test that missing file path causes exit."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            request_changes,
        )
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.summary", "Please fix this.")
        set_value(
            "file_review.suggestions",
            '[{"line": 42, "severity": "high", "content": "Fix this"}]',
        )
        set_value("ado.organization", "https://dev.azure.com/test")
        set_value("ado.project", "TestProject")
        set_value("ado.repository", "TestRepo")

        with pytest.raises(SystemExit):
            request_changes()

    def test_missing_summary_exits(self, mock_state):
        """Test that missing summary causes exit."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            request_changes,
        )
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "/src/app.ts")
        set_value(
            "file_review.suggestions",
            '[{"line": 42, "severity": "high", "content": "Fix this"}]',
        )
        set_value("ado.organization", "https://dev.azure.com/test")
        set_value("ado.project", "TestProject")
        set_value("ado.repository", "TestRepo")

        with pytest.raises(SystemExit):
            request_changes()

    def test_missing_suggestions_exits(self, mock_state):
        """Test that missing suggestions causes exit."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            request_changes,
        )
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "/src/app.ts")
        set_value("file_review.summary", "Please fix this.")
        set_value("ado.organization", "https://dev.azure.com/test")
        set_value("ado.project", "TestProject")
        set_value("ado.repository", "TestRepo")

        with pytest.raises(SystemExit):
            request_changes()
