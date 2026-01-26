"""
Tests for pr_summary_commands module.

Covers:
- Return value behavior of generate_overarching_pr_comments
- Early exit scenarios (no files, no threads, dry run)
- Helper functions for path normalization, sorting, and link building
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.azure_devops.pr_summary_commands import (
    FileSummary,
    FolderSummary,
    _build_comment_link,
    _build_file_link,
    _build_folder_comment,
    _filter_threads,
    _get_azure_devops_sort_key,
    _get_file_thread_status,
    _get_latest_comment_context,
    _get_root_folder,
    _get_thread_file_path,
    _normalize_repo_path,
    _post_comment,
    _sort_entries_by_path,
    _sort_folders,
    generate_overarching_pr_comments,
    generate_overarching_pr_comments_cli,
)


class TestGenerateOverarchingPrComments:
    """Tests for generate_overarching_pr_comments function."""

    def test_returns_true_when_no_files_in_pr(self, temp_state_dir, clear_state_before, capsys, tmp_path):
        """Should return True when PR has no file metadata."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "12345")

        # Create mock PR details file with no files
        pr_details = {"files": [], "threads": []}

        # Set up temp directory structure
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir(exist_ok=True)
        details_file = temp_dir / "temp-get-pull-request-details-response.json"
        details_file.write_text(json.dumps(pr_details))

        # Patch at the source module where it's imported from
        with patch("agentic_devtools.cli.azure_devops.pull_request_details_commands.get_pull_request_details"), patch(
            "agentic_devtools.cli.azure_devops.pr_summary_commands.Path"
        ) as mock_path_class:
            # Mock Path(__file__).parent chain to return tmp_path
            mock_path_class.return_value.parent.parent.parent.parent.parent = tmp_path

            result = generate_overarching_pr_comments()

        assert result is True
        captured = capsys.readouterr()
        assert "No file metadata found" in captured.out

    def test_returns_true_when_no_threads(self, temp_state_dir, clear_state_before, capsys, tmp_path):
        """Should return True when PR has files but no threads."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "12345")

        # Create mock PR details file with files but no threads
        pr_details = {
            "files": [{"path": "/src/main.py", "changeType": "edit"}],
            "threads": [],
        }

        # Set up temp directory structure
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir(exist_ok=True)
        details_file = temp_dir / "temp-get-pull-request-details-response.json"
        details_file.write_text(json.dumps(pr_details))

        with patch("agentic_devtools.cli.azure_devops.pull_request_details_commands.get_pull_request_details"), patch(
            "agentic_devtools.cli.azure_devops.pr_summary_commands.Path"
        ) as mock_path_class:
            # Mock Path(__file__).parent chain to return tmp_path
            mock_path_class.return_value.parent.parent.parent.parent.parent = tmp_path

            result = generate_overarching_pr_comments()

        assert result is True
        captured = capsys.readouterr()
        assert "No discussion threads detected" in captured.out

    def test_dry_run_returns_true(self, temp_state_dir, clear_state_before, capsys, tmp_path):
        """Should return True on successful dry run."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "12345")
        set_value("dry_run", "true")

        # Create mock PR details with files and threads
        pr_details = {
            "files": [{"path": "/src/main.py", "changeType": "edit"}],
            "threads": [
                {
                    "id": 1,
                    "status": "closed",
                    "threadContext": {"filePath": "/src/main.py"},
                    "comments": [{"content": "LGTM"}],
                }
            ],
        }

        # Set up temp directory structure
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir(exist_ok=True)
        details_file = temp_dir / "temp-get-pull-request-details-response.json"
        details_file.write_text(json.dumps(pr_details))

        with patch("agentic_devtools.cli.azure_devops.pull_request_details_commands.get_pull_request_details"), patch(
            "agentic_devtools.cli.azure_devops.pr_summary_commands.Path"
        ) as mock_path_class:
            mock_path_class.return_value.parent.parent.parent.parent.parent = tmp_path

            result = generate_overarching_pr_comments()

        assert result is True
        captured = capsys.readouterr()
        assert "Dry run complete" in captured.out

    def test_missing_pull_request_id_raises_error(self, temp_state_dir, clear_state_before):
        """Should raise KeyError if pull_request_id is not set."""
        # Don't set pull_request_id

        with pytest.raises(KeyError, match="pull_request_id"):
            generate_overarching_pr_comments()


class TestNormalizeRepoPath:
    """Tests for _normalize_repo_path helper function."""

    def test_returns_none_for_none_input(self):
        """Should return None for None input."""
        assert _normalize_repo_path(None) is None

    def test_returns_none_for_empty_string(self):
        """Should return None for empty string."""
        assert _normalize_repo_path("") is None

    def test_returns_none_for_whitespace_only(self):
        """Should return None for whitespace-only string."""
        assert _normalize_repo_path("   ") is None

    def test_normalizes_backslashes_to_forward_slashes(self):
        """Should convert backslashes to forward slashes."""
        result = _normalize_repo_path("src\\main\\file.py")
        assert result == "/src/main/file.py"

    def test_removes_leading_and_trailing_slashes(self):
        """Should strip leading/trailing slashes before adding single leading slash."""
        result = _normalize_repo_path("/src/file.py/")
        assert result == "/src/file.py"

    def test_handles_simple_path(self):
        """Should handle simple relative path."""
        result = _normalize_repo_path("file.py")
        assert result == "/file.py"

    def test_returns_none_for_whitespace_after_cleaning(self):
        """Should return None if path becomes empty after stripping."""
        assert _normalize_repo_path("///") is None


class TestGetRootFolder:
    """Tests for _get_root_folder helper function."""

    def test_returns_root_for_empty_path(self):
        """Should return 'root' for empty path."""
        assert _get_root_folder("") == "root"

    def test_returns_root_for_file_without_folder(self):
        """Should return 'root' for file without any folder."""
        assert _get_root_folder("file.py") == "root"

    def test_returns_first_segment_for_nested_path(self):
        """Should return first segment for nested path."""
        assert _get_root_folder("src/main/file.py") == "src"

    def test_handles_backslashes(self):
        """Should handle paths with backslashes."""
        assert _get_root_folder("src\\main\\file.py") == "src"


class TestGetThreadFilePath:
    """Tests for _get_thread_file_path helper function."""

    def test_returns_none_for_no_context(self):
        """Should return None if thread has no threadContext."""
        assert _get_thread_file_path({}) is None
        assert _get_thread_file_path({"id": 1}) is None

    def test_extracts_from_filePath(self):
        """Should extract path from filePath in context."""
        thread = {"threadContext": {"filePath": "/src/main.py"}}
        assert _get_thread_file_path(thread) == "src/main.py"

    def test_extracts_from_leftFileStart(self):
        """Should extract path from leftFileStart if filePath not present."""
        thread = {"threadContext": {"leftFileStart": {"filePath": "/src/left.py"}}}
        assert _get_thread_file_path(thread) == "src/left.py"

    def test_extracts_from_rightFileStart(self):
        """Should extract path from rightFileStart if others not present."""
        thread = {"threadContext": {"rightFileStart": {"filePath": "/src/right.py"}}}
        assert _get_thread_file_path(thread) == "src/right.py"

    def test_returns_none_for_empty_context(self):
        """Should return None if context has no file path."""
        thread = {"threadContext": {}}
        assert _get_thread_file_path(thread) is None


class TestFilterThreads:
    """Tests for _filter_threads helper function."""

    def test_returns_empty_list_for_empty_input(self):
        """Should return empty list for empty input."""
        assert _filter_threads([]) == []
        assert _filter_threads(None) == []

    def test_filters_out_deleted_threads(self):
        """Should exclude deleted threads."""
        threads = [
            {"id": 1, "isDeleted": True, "comments": [{"content": "deleted"}]},
            {"id": 2, "comments": [{"content": "kept"}]},
        ]
        result = _filter_threads(threads)
        assert len(result) == 1
        assert result[0]["id"] == 2

    def test_filters_out_deleted_comments(self):
        """Should exclude deleted comments within threads."""
        threads = [
            {
                "id": 1,
                "comments": [
                    {"id": 1, "content": "kept", "isDeleted": False},
                    {"id": 2, "content": "deleted", "isDeleted": True},
                ],
            }
        ]
        result = _filter_threads(threads)
        assert len(result) == 1
        assert len(result[0]["comments"]) == 1
        assert result[0]["comments"][0]["content"] == "kept"

    def test_excludes_threads_with_no_remaining_comments(self):
        """Should exclude threads if all comments are deleted."""
        threads = [{"id": 1, "comments": [{"content": "deleted", "isDeleted": True}]}]
        result = _filter_threads(threads)
        assert result == []

    def test_handles_none_threads_in_list(self):
        """Should skip None threads."""
        threads = [None, {"id": 1, "comments": [{"content": "valid"}]}]
        result = _filter_threads(threads)
        assert len(result) == 1

    def test_handles_none_comments(self):
        """Should skip None comments in list."""
        threads = [{"id": 1, "comments": [None, {"content": "valid"}]}]
        result = _filter_threads(threads)
        assert len(result) == 1
        assert len(result[0]["comments"]) == 1


class TestGetFileThreadStatus:
    """Tests for _get_file_thread_status helper function."""

    def test_returns_approved_for_empty_threads(self):
        """Should return Approved for empty thread list."""
        assert _get_file_thread_status([]) == "Approved"

    def test_returns_needs_work_for_active_thread(self):
        """Should return NeedsWork if any thread is active."""
        threads = [{"status": "active"}]
        assert _get_file_thread_status(threads) == "NeedsWork"

    def test_returns_needs_work_for_pending_thread(self):
        """Should return NeedsWork if any thread is pending."""
        threads = [{"status": "pending"}]
        assert _get_file_thread_status(threads) == "NeedsWork"

    def test_returns_approved_for_closed_threads(self):
        """Should return Approved if all threads are closed."""
        threads = [{"status": "closed"}, {"status": "fixed"}]
        assert _get_file_thread_status(threads) == "Approved"


class TestGetAzureDevOpsSortKey:
    """Tests for _get_azure_devops_sort_key helper function."""

    def test_returns_default_for_empty_path(self):
        """Should return '1|' for empty path."""
        assert _get_azure_devops_sort_key("") == "1|"

    def test_returns_default_for_none(self):
        """Should return '1|' for None (via empty)."""
        # Function expects string, but we test edge case
        assert _get_azure_devops_sort_key(None) == "1|"

    def test_single_file_at_root(self):
        """Should generate key for single file at root."""
        result = _get_azure_devops_sort_key("file.py")
        assert result == "1|file.py|"

    def test_nested_file_generates_proper_key(self):
        """Should generate key with folder/file indicators."""
        result = _get_azure_devops_sort_key("/src/main/file.py")
        # src = folder (0), main = folder (0), file.py = file (1)
        assert result == "0|src|0|main|1|file.py|"

    def test_handles_slashes_only_path(self):
        """Should handle path that becomes empty after stripping."""
        result = _get_azure_devops_sort_key("/")
        assert result == "1|"


class TestSortEntriesByPath:
    """Tests for _sort_entries_by_path helper function."""

    def test_sorts_files_alphabetically(self):
        """Should sort file summaries by path."""
        entries = [
            FileSummary("/z.py", "z.py", "root", [], "Approved"),
            FileSummary("/a.py", "a.py", "root", [], "Approved"),
        ]
        result = _sort_entries_by_path(entries)
        assert result[0].path == "a.py"
        assert result[1].path == "z.py"


class TestSortFolders:
    """Tests for _sort_folders helper function."""

    def test_sorts_alphabetically_with_root_last(self):
        """Should sort folders alphabetically with root last."""
        folders = [
            FolderSummary("root", "Approved"),
            FolderSummary("src", "Approved"),
            FolderSummary("docs", "NeedsWork"),
        ]
        result = _sort_folders(folders)
        assert result[0].name == "docs"
        assert result[1].name == "src"
        assert result[2].name == "root"


class TestBuildCommentLink:
    """Tests for _build_comment_link helper function."""

    @pytest.fixture
    def mock_config(self):
        """Create mock AzureDevOpsConfig."""
        config = MagicMock()
        config.organization = "https://dev.azure.com/org/"
        config.project = "My Project"
        config.repository = "my-repo"
        return config

    def test_builds_base_pr_link(self, mock_config):
        """Should build base PR link without thread/comment."""
        result = _build_comment_link(mock_config, 123)
        assert "pullRequest/123" in result
        assert "discussionId" not in result

    def test_builds_link_with_thread_id(self, mock_config):
        """Should include discussionId when thread_id provided."""
        result = _build_comment_link(mock_config, 123, thread_id=456)
        assert "discussionId=456" in result

    def test_builds_link_with_thread_and_comment(self, mock_config):
        """Should include both discussionId and commentId."""
        result = _build_comment_link(mock_config, 123, thread_id=456, comment_id=789)
        assert "discussionId=456" in result
        assert "commentId=789" in result

    def test_builds_link_with_comment_only(self, mock_config):
        """Should handle comment_id without thread_id."""
        result = _build_comment_link(mock_config, 123, comment_id=789)
        assert "#789" in result

    def test_escapes_ampersands(self, mock_config):
        """Should escape ampersands for markdown."""
        result = _build_comment_link(mock_config, 123, thread_id=456, comment_id=789)
        assert "&amp;" in result
        assert "& " not in result  # Not plain ampersand followed by space


class TestGetLatestCommentContext:
    """Tests for _get_latest_comment_context helper function."""

    def test_returns_none_for_empty_threads(self):
        """Should return None for empty thread list."""
        assert _get_latest_comment_context([]) is None
        assert _get_latest_comment_context(None) is None

    def test_returns_thread_with_no_comments(self):
        """Should return thread with None comment if no comments exist."""
        threads = [{"id": 1, "publishedDate": "2024-01-01T00:00:00Z", "comments": []}]
        result = _get_latest_comment_context(threads)
        assert result is not None
        thread, comment = result
        assert thread["id"] == 1
        assert comment is None

    def test_returns_latest_by_timestamp(self):
        """Should return the most recently updated thread/comment."""
        threads = [
            {
                "id": 1,
                "comments": [
                    {
                        "id": 1,
                        "lastUpdatedDate": "2024-01-01T00:00:00Z",
                        "commentType": "text",
                    }
                ],
            },
            {
                "id": 2,
                "comments": [
                    {
                        "id": 2,
                        "lastUpdatedDate": "2024-01-02T00:00:00Z",
                        "commentType": "text",
                    }
                ],
            },
        ]
        result = _get_latest_comment_context(threads)
        assert result is not None
        thread, comment = result
        assert thread["id"] == 2

    def test_skips_code_position_comments(self):
        """Should skip comments with commentType codePosition."""
        threads = [
            {
                "id": 1,
                "comments": [
                    {
                        "id": 1,
                        "lastUpdatedDate": "2024-01-02T00:00:00Z",
                        "commentType": "codePosition",
                    },
                    {
                        "id": 2,
                        "lastUpdatedDate": "2024-01-01T00:00:00Z",
                        "commentType": "text",
                    },
                ],
            }
        ]
        result = _get_latest_comment_context(threads)
        assert result is not None
        _, comment = result
        assert comment["id"] == 2

    def test_handles_invalid_timestamp(self):
        """Should handle invalid timestamp gracefully."""
        threads = [
            {
                "id": 1,
                "comments": [{"id": 1, "lastUpdatedDate": "invalid-date", "commentType": "text"}],
            }
        ]
        result = _get_latest_comment_context(threads)
        assert result is not None

    def test_handles_none_thread_in_list(self):
        """Should skip None threads in list."""
        threads = [None, {"id": 1, "comments": [{"id": 1, "commentType": "text"}]}]
        result = _get_latest_comment_context(threads)
        assert result is not None

    def test_handles_none_comment_in_list(self):
        """Should skip None comments in list."""
        threads = [{"id": 1, "comments": [None, {"id": 1, "commentType": "text"}]}]
        result = _get_latest_comment_context(threads)
        assert result is not None


class TestBuildFileLink:
    """Tests for _build_file_link helper function."""

    @pytest.fixture
    def mock_config(self):
        """Create mock AzureDevOpsConfig."""
        config = MagicMock()
        config.organization = "https://dev.azure.com/org/"
        config.project = "Project"
        config.repository = "repo"
        return config

    def test_returns_display_path_for_no_context(self, mock_config):
        """Should return display path if no threads."""
        result = _build_file_link("/src/file.py", [], mock_config, 123)
        assert result == "/src/file.py"

    def test_builds_markdown_link(self, mock_config):
        """Should build markdown link with thread context."""
        threads = [
            {
                "id": 1,
                "comments": [{"id": 1, "commentType": "text"}],
            }
        ]
        result = _build_file_link("/src/file.py", threads, mock_config, 123)
        assert result.startswith("[/src/file.py](")
        assert "pullRequest/123" in result

    def test_handles_empty_file_path(self, mock_config):
        """Should use 'root' as display for empty path."""
        result = _build_file_link("", [], mock_config, 123)
        assert result == "root"

    def test_uses_first_thread_if_no_latest_context(self, mock_config):
        """Should fall back to first thread if no timestamps."""
        threads = [
            {
                "id": 1,
                "comments": [{"id": 1, "commentType": "text"}],
            }
        ]
        result = _build_file_link("/src/file.py", threads, mock_config, 123)
        assert "[/src/file.py](" in result

    def test_skips_code_position_comment_for_fallback(self, mock_config):
        """Should skip codePosition comments when finding fallback."""
        threads = [
            {
                "id": 1,
                "comments": [
                    {"id": 1, "commentType": "codePosition"},
                    {"id": 2, "commentType": "text"},
                ],
            }
        ]
        result = _build_file_link("/src/file.py", threads, mock_config, 123)
        assert "[/src/file.py](" in result


class TestBuildFolderComment:
    """Tests for _build_folder_comment helper function."""

    @pytest.fixture
    def mock_config(self):
        """Create mock AzureDevOpsConfig."""
        config = MagicMock()
        config.organization = "https://dev.azure.com/org/"
        config.project = "Project"
        config.repository = "repo"
        return config

    def test_generates_approved_status(self, mock_config):
        """Should generate Approved status when all files approved."""
        file_summaries = [
            FileSummary("/src/a.py", "/src/a.py", "src", [], "Approved"),
            FileSummary("/src/b.py", "/src/b.py", "src", [], "Approved"),
        ]
        comment, status = _build_folder_comment("src", file_summaries, mock_config, 123)
        assert status == "Approved"
        assert "Status:* Approved" in comment

    def test_generates_needs_work_status(self, mock_config):
        """Should generate Needs Work status if any file needs work."""
        file_summaries = [
            FileSummary("/src/a.py", "/src/a.py", "src", [], "Approved"),
            FileSummary("/src/b.py", "/src/b.py", "src", [{"status": "active"}], "NeedsWork"),
        ]
        comment, status = _build_folder_comment("src", file_summaries, mock_config, 123)
        assert status == "Needs Work"
        assert "Status:* Needs Work" in comment

    def test_includes_needs_work_section(self, mock_config):
        """Should include Needs Work section when files need work."""
        file_summaries = [
            FileSummary("/src/a.py", "/src/a.py", "src", [], "NeedsWork"),
        ]
        comment, _ = _build_folder_comment("src", file_summaries, mock_config, 123)
        assert "### Needs Work" in comment

    def test_includes_approved_section(self, mock_config):
        """Should include Approved section when files are approved."""
        file_summaries = [
            FileSummary("/src/a.py", "/src/a.py", "src", [], "Approved"),
        ]
        comment, _ = _build_folder_comment("src", file_summaries, mock_config, 123)
        assert "### Approved" in comment


class TestPostComment:
    """Tests for _post_comment helper function."""

    @pytest.fixture
    def mock_config(self):
        """Create mock AzureDevOpsConfig."""
        config = MagicMock()
        config.build_api_url = MagicMock(return_value="https://api.example.com/threads")
        return config

    def test_posts_comment_and_resolves_thread(self, mock_config):
        """Should post comment and resolve thread by default."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 123, "comments": [{"id": 456}]}
        mock_requests.post.return_value = mock_response

        result = _post_comment(
            mock_requests,
            {"Authorization": "Bearer token"},
            mock_config,
            "repo-id",
            100,
            "Test comment",
        )

        assert result["thread_id"] == 123
        assert result["comment_id"] == 456
        mock_requests.patch.assert_called_once()  # Thread resolved

    def test_leaves_thread_active_when_requested(self, mock_config):
        """Should not resolve thread when leave_active=True."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 123, "comments": [{"id": 456}]}
        mock_requests.post.return_value = mock_response

        _post_comment(
            mock_requests,
            {"Authorization": "Bearer token"},
            mock_config,
            "repo-id",
            100,
            "Test comment",
            leave_active=True,
        )

        mock_requests.patch.assert_not_called()

    def test_returns_none_on_post_failure(self, mock_config, capsys):
        """Should return None and print warning on failure."""
        mock_requests = MagicMock()
        mock_requests.post.side_effect = Exception("Network error")

        result = _post_comment(
            mock_requests,
            {"Authorization": "Bearer token"},
            mock_config,
            "repo-id",
            100,
            "Test comment",
        )

        assert result is None
        captured = capsys.readouterr()
        assert "Failed to post comment" in captured.err

    def test_handles_resolve_failure_gracefully(self, mock_config, capsys):
        """Should continue even if resolving thread fails."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 123, "comments": [{"id": 456}]}
        mock_requests.post.return_value = mock_response
        mock_requests.patch.side_effect = Exception("Resolve failed")

        result = _post_comment(
            mock_requests,
            {"Authorization": "Bearer token"},
            mock_config,
            "repo-id",
            100,
            "Test comment",
        )

        assert result is not None  # Still returns result
        captured = capsys.readouterr()
        assert "Failed to resolve thread" in captured.err


class TestGenerateOverarchingPrCommentsCli:
    """Tests for CLI entry point."""

    def test_cli_calls_main_function(self, temp_state_dir, clear_state_before):
        """CLI entry point should call generate_overarching_pr_comments."""
        with patch(
            "agentic_devtools.cli.azure_devops.pr_summary_commands.generate_overarching_pr_comments"
        ) as mock_func:
            mock_func.return_value = True
            generate_overarching_pr_comments_cli()
            mock_func.assert_called_once()
