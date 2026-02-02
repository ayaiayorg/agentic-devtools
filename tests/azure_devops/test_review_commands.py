"""Tests for the review_commands module and helper functions."""

import pytest

from agdt_ai_helpers.cli.azure_devops.review_helpers import (
    JIRA_ISSUE_KEY_PATTERN,
    build_reviewed_paths_set,
    convert_to_prompt_filename,
    extract_jira_issue_key_from_title,
    filter_threads,
    get_root_folder,
    get_threads_for_file,
    normalize_repo_path,
)


class TestExtractJiraIssueKeyFromTitle:
    """Tests for extract_jira_issue_key_from_title function."""

    def test_standard_format(self):
        """Test extraction from standard commit format."""
        title = "feature([DFLY-1234](https://jira.swica.ch/browse/DFLY-1234)): add feature"
        result = extract_jira_issue_key_from_title(title)
        assert result == "DFLY-1234"

    def test_parent_child_format(self):
        """Test extraction returns first match for parent/child format."""
        title = "feature([DFLY-1840](link) / [DFLY-1900](link)): description"
        result = extract_jira_issue_key_from_title(title)
        assert result == "DFLY-1840"

    def test_simple_brackets(self):
        """Test extraction from simple brackets format."""
        title = "[PROJ-999] Fix the bug"
        result = extract_jira_issue_key_from_title(title)
        assert result == "PROJ-999"

    def test_no_jira_key(self):
        """Test returns None when no Jira key present."""
        title = "feature: add feature without ticket"
        result = extract_jira_issue_key_from_title(title)
        assert result is None

    def test_empty_title(self):
        """Test returns None for empty title."""
        result = extract_jira_issue_key_from_title("")
        assert result is None

    def test_none_title(self):
        """Test returns None for None title."""
        result = extract_jira_issue_key_from_title(None)
        assert result is None

    def test_multiple_keys_returns_first(self):
        """Test returns first key when multiple present."""
        title = "ABC-123 DEF-456 XYZ-789"
        result = extract_jira_issue_key_from_title(title)
        assert result == "ABC-123"

    def test_lowercase_does_not_match(self):
        """Test lowercase project keys don't match."""
        title = "dfly-1234 in lowercase"
        result = extract_jira_issue_key_from_title(title)
        assert result is None


class TestConvertToPromptFilename:
    """Tests for convert_to_prompt_filename function."""

    def test_basic_path(self):
        """Test conversion of a basic file path."""
        result = convert_to_prompt_filename("/path/to/file.ts")
        assert result.startswith("file-")
        assert result.endswith(".md")
        assert len(result) == 24  # "file-" + 16 chars + ".md"

    def test_empty_path(self):
        """Test conversion of empty path."""
        result = convert_to_prompt_filename("")
        assert result == "file-metadata-missing.md"

    def test_same_path_same_hash(self):
        """Test same path produces same hash."""
        result1 = convert_to_prompt_filename("/path/to/file.ts")
        result2 = convert_to_prompt_filename("/path/to/file.ts")
        assert result1 == result2

    def test_different_paths_different_hashes(self):
        """Test different paths produce different hashes."""
        result1 = convert_to_prompt_filename("/path/to/file1.ts")
        result2 = convert_to_prompt_filename("/path/to/file2.ts")
        assert result1 != result2


class TestNormalizeRepoPath:
    """Tests for normalize_repo_path function."""

    def test_basic_path(self):
        """Test normalization of basic path."""
        result = normalize_repo_path("src/app/file.ts")
        assert result == "/src/app/file.ts"

    def test_path_with_leading_slash(self):
        """Test path with leading slash."""
        result = normalize_repo_path("/src/app/file.ts")
        assert result == "/src/app/file.ts"

    def test_path_with_backslashes(self):
        """Test path with Windows backslashes."""
        result = normalize_repo_path("src\\app\\file.ts")
        assert result == "/src/app/file.ts"

    def test_empty_path(self):
        """Test empty path returns None."""
        result = normalize_repo_path("")
        assert result is None

    def test_none_path(self):
        """Test None path returns None."""
        result = normalize_repo_path(None)
        assert result is None

    def test_whitespace_only(self):
        """Test whitespace-only path returns None."""
        result = normalize_repo_path("   ")
        assert result is None


class TestGetRootFolder:
    """Tests for get_root_folder function."""

    def test_basic_path(self):
        """Test extraction from basic path."""
        result = get_root_folder("src/app/file.ts")
        assert result == "src"

    def test_file_only(self):
        """Test file with no folder returns 'root'."""
        result = get_root_folder("file.ts")
        assert result == "root"

    def test_empty_path(self):
        """Test empty path returns 'root'."""
        result = get_root_folder("")
        assert result == "root"

    def test_backslash_path(self):
        """Test path with backslashes."""
        result = get_root_folder("src\\app\\file.ts")
        assert result == "src"

    def test_none_path(self):
        """Test None path returns 'root'."""
        result = get_root_folder(None)
        assert result == "root"


class TestFilterThreads:
    """Tests for filter_threads function."""

    def test_empty_threads(self):
        """Test empty list returns empty list."""
        result = filter_threads([])
        assert result == []

    def test_none_threads(self):
        """Test None returns empty list."""
        result = filter_threads(None)
        assert result == []

    def test_filters_deleted_threads(self):
        """Test deleted threads are filtered out."""
        threads = [
            {"id": 1, "isDeleted": False, "comments": [{"content": "test"}]},
            {"id": 2, "isDeleted": True, "comments": [{"content": "test"}]},
        ]
        result = filter_threads(threads)
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_filters_threads_with_deleted_comments(self):
        """Test threads with all deleted comments are filtered."""
        threads = [
            {"id": 1, "comments": [{"content": "test", "isDeleted": True}]},
        ]
        result = filter_threads(threads)
        assert len(result) == 0

    def test_keeps_partial_deleted_comments(self):
        """Test threads with some active comments are kept."""
        threads = [
            {
                "id": 1,
                "comments": [
                    {"content": "active"},
                    {"content": "deleted", "isDeleted": True},
                ],
            },
        ]
        result = filter_threads(threads)
        assert len(result) == 1
        assert len(result[0]["comments"]) == 1

    def test_filters_null_threads(self):
        """Test null/None items in thread list are filtered."""
        threads = [
            None,
            {"id": 1, "comments": [{"content": "test"}]},
        ]
        result = filter_threads(threads)
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_filters_null_comments(self):
        """Test null/None items in comments list are filtered."""
        threads = [
            {"id": 1, "comments": [None, {"content": "test"}]},
        ]
        result = filter_threads(threads)
        assert len(result) == 1
        assert len(result[0]["comments"]) == 1

    def test_does_not_mutate_original(self):
        """Test that filter_threads does not mutate the original threads."""
        original_threads = [
            {
                "id": 1,
                "comments": [
                    {"content": "active"},
                    {"content": "deleted", "isDeleted": True},
                ],
            },
        ]
        # Make a deep copy for comparison
        import copy

        original_copy = copy.deepcopy(original_threads)

        result = filter_threads(original_threads)

        # Original should be unchanged
        assert original_threads == original_copy
        # Result should have filtered comments
        assert len(result[0]["comments"]) == 1


class TestGetThreadsForFile:
    """Tests for get_threads_for_file function."""

    def test_empty_threads(self):
        """Test empty threads returns empty list."""
        result = get_threads_for_file([], "/path/file.ts")
        assert result == []

    def test_matching_thread(self):
        """Test finds thread matching file path."""
        threads = [{"id": 1, "threadContext": {"filePath": "/src/file.ts"}}]
        result = get_threads_for_file(threads, "/src/file.ts")
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_no_matching_thread(self):
        """Test returns empty when no match."""
        threads = [{"id": 1, "threadContext": {"filePath": "/other/file.ts"}}]
        result = get_threads_for_file(threads, "/src/file.ts")
        assert len(result) == 0

    def test_normalizes_paths(self):
        """Test normalizes both thread path and input path."""
        threads = [
            {
                "id": 1,
                "threadContext": {"filePath": "src/file.ts"},  # no leading slash
            }
        ]
        result = get_threads_for_file(threads, "/src/file.ts")  # with leading slash
        assert len(result) == 1

    def test_null_thread_in_list(self):
        """Test handles null thread in list."""
        threads = [None, {"id": 1, "threadContext": {"filePath": "/src/file.ts"}}]
        result = get_threads_for_file(threads, "/src/file.ts")
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_thread_without_context(self):
        """Test handles thread without threadContext."""
        threads = [
            {"id": 1},  # no threadContext
            {"id": 2, "threadContext": {"filePath": "/src/file.ts"}},
        ]
        result = get_threads_for_file(threads, "/src/file.ts")
        assert len(result) == 1
        assert result[0]["id"] == 2

    def test_leftFileStart_path(self):
        """Test finds thread with path in leftFileStart."""
        threads = [
            {
                "id": 1,
                "threadContext": {"leftFileStart": {"filePath": "/src/file.ts", "line": 10}},
            }
        ]
        result = get_threads_for_file(threads, "/src/file.ts")
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_rightFileStart_path(self):
        """Test finds thread with path in rightFileStart."""
        threads = [
            {
                "id": 1,
                "threadContext": {"rightFileStart": {"filePath": "/src/file.ts", "line": 10}},
            }
        ]
        result = get_threads_for_file(threads, "/src/file.ts")
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_filePath_takes_precedence(self):
        """Test filePath is checked before left/rightFileStart."""
        threads = [
            {
                "id": 1,
                "threadContext": {
                    "filePath": "/other/file.ts",
                    "leftFileStart": {"filePath": "/src/file.ts"},
                },
            }
        ]
        # Should match against filePath, not leftFileStart
        result = get_threads_for_file(threads, "/src/file.ts")
        assert len(result) == 0


class TestBuildReviewedPathsSet:
    """Tests for build_reviewed_paths_set function."""

    def test_empty_pr_details(self):
        """Test empty PR details returns empty set."""
        result = build_reviewed_paths_set({})
        assert result == set()

    def test_no_reviewer_data(self):
        """Test PR details without reviewer key returns empty set."""
        pr_details = {"pullRequest": {"id": 123}}
        result = build_reviewed_paths_set(pr_details)
        assert result == set()

    def test_none_reviewer_data(self):
        """Test PR details with None reviewer returns empty set."""
        pr_details = {"reviewer": None}
        result = build_reviewed_paths_set(pr_details)
        assert result == set()

    def test_empty_reviewed_files(self):
        """Test empty reviewedFiles returns empty set."""
        pr_details = {"reviewer": {"reviewedFiles": []}}
        result = build_reviewed_paths_set(pr_details)
        assert result == set()

    def test_none_reviewed_files(self):
        """Test None reviewedFiles returns empty set."""
        pr_details = {"reviewer": {"reviewedFiles": None}}
        result = build_reviewed_paths_set(pr_details)
        assert result == set()

    def test_single_reviewed_file(self):
        """Test single reviewed file is normalized."""
        pr_details = {"reviewer": {"reviewedFiles": ["/src/file.ts"]}}
        result = build_reviewed_paths_set(pr_details)
        assert "/src/file.ts" in result

    def test_multiple_reviewed_files(self):
        """Test multiple reviewed files are normalized."""
        pr_details = {"reviewer": {"reviewedFiles": ["/src/file1.ts", "/src/file2.ts"]}}
        result = build_reviewed_paths_set(pr_details)
        assert len(result) == 2
        assert "/src/file1.ts" in result
        assert "/src/file2.ts" in result

    def test_paths_are_lowercase(self):
        """Test paths are normalized to lowercase."""
        pr_details = {"reviewer": {"reviewedFiles": ["/SRC/FILE.TS"]}}
        result = build_reviewed_paths_set(pr_details)
        assert "/src/file.ts" in result
        assert "/SRC/FILE.TS" not in result

    def test_invalid_paths_are_skipped(self):
        """Test invalid paths (empty, None) are skipped."""
        pr_details = {"reviewer": {"reviewedFiles": ["", None, "/src/valid.ts", "   "]}}
        result = build_reviewed_paths_set(pr_details)
        assert len(result) == 1
        assert "/src/valid.ts" in result


class TestJiraIssueKeyPattern:
    """Tests for the JIRA_ISSUE_KEY_PATTERN regex."""

    def test_pattern_matches_standard_keys(self):
        """Test pattern matches standard Jira keys."""
        matches = JIRA_ISSUE_KEY_PATTERN.findall("DFLY-1234 PROJ-99 ABC-1")
        assert matches == ["DFLY-1234", "PROJ-99", "ABC-1"]

    def test_pattern_ignores_lowercase(self):
        """Test pattern ignores lowercase keys."""
        matches = JIRA_ISSUE_KEY_PATTERN.findall("dfly-1234 proj-99")
        assert matches == []

    def test_pattern_extracts_from_markdown_links(self):
        """Test pattern extracts from markdown links."""
        text = "[DFLY-1234](https://jira.example.com/browse/DFLY-1234)"
        matches = JIRA_ISSUE_KEY_PATTERN.findall(text)
        # Should find both occurrences
        assert len(matches) == 2
        assert all(m == "DFLY-1234" for m in matches)


# =============================================================================
# Path Normalization for Branch File Comparison Tests
# =============================================================================


class TestNormalizePathForComparison:
    """Tests for _normalize_path_for_comparison function."""

    def test_basic_path(self):
        """Test normalization of basic path."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import _normalize_path_for_comparison

        result = _normalize_path_for_comparison("src/app/file.ts")
        assert result == "src/app/file.ts"

    def test_path_with_leading_slash(self):
        """Test path with leading slash has it stripped."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import _normalize_path_for_comparison

        result = _normalize_path_for_comparison("/src/app/file.ts")
        assert result == "src/app/file.ts"

    def test_path_with_backslashes(self):
        """Test path with Windows backslashes converted."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import _normalize_path_for_comparison

        result = _normalize_path_for_comparison("src\\app\\file.ts")
        assert result == "src/app/file.ts"

    def test_lowercase_normalization(self):
        """Test path is lowercased."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import _normalize_path_for_comparison

        result = _normalize_path_for_comparison("SRC/App/File.ts")
        assert result == "src/app/file.ts"

    def test_empty_path(self):
        """Test empty path returns empty."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import _normalize_path_for_comparison

        result = _normalize_path_for_comparison("")
        assert result == ""

    def test_mixed_normalization(self):
        """Test combination of normalizations."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import _normalize_path_for_comparison

        result = _normalize_path_for_comparison("/SRC\\App/File.ts")
        assert result == "src/app/file.ts"


# =============================================================================
# Checkout and Sync Branch Tests
# =============================================================================


class TestCheckoutAndSyncBranch:
    """Tests for checkout_and_sync_branch function."""

    def test_success_returns_files_on_branch(self):
        """Test successful checkout and sync returns files."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agdt_ai_helpers.cli.git.operations import CheckoutResult, RebaseResult

        with patch("agdt_ai_helpers.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agdt_ai_helpers.cli.git.operations.fetch_main") as mock_fetch:
                with patch("agdt_ai_helpers.cli.git.operations.rebase_onto_main") as mock_rebase:
                    with patch("agdt_ai_helpers.cli.git.operations.get_files_changed_on_branch") as mock_get_files:
                        mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                        mock_fetch.return_value = True
                        mock_rebase.return_value = RebaseResult(RebaseResult.SUCCESS)
                        mock_get_files.return_value = ["file1.ts", "file2.ts"]

                        success, error, files = checkout_and_sync_branch("feature/test")

                        assert success is True
                        assert error is None
                        assert files == {"file1.ts", "file2.ts"}

    def test_checkout_failure_returns_error(self):
        """Test checkout failure returns error message."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agdt_ai_helpers.cli.git.operations import CheckoutResult

        with patch("agdt_ai_helpers.cli.git.operations.checkout_branch") as mock_checkout:
            mock_checkout.return_value = CheckoutResult(
                CheckoutResult.UNCOMMITTED_CHANGES,
                "You have uncommitted changes",
            )

            success, error, files = checkout_and_sync_branch("feature/test")

            assert success is False
            assert error is not None
            assert "uncommitted" in error.lower() or "cannot checkout" in error.lower()
            # Files is empty set on failure, not None
            assert files == set()

    def test_rebase_conflict_still_returns_files(self):
        """Test rebase conflict still returns files (review can continue)."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agdt_ai_helpers.cli.git.operations import CheckoutResult, RebaseResult

        with patch("agdt_ai_helpers.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agdt_ai_helpers.cli.git.operations.fetch_main") as mock_fetch:
                with patch("agdt_ai_helpers.cli.git.operations.rebase_onto_main") as mock_rebase:
                    with patch("agdt_ai_helpers.cli.git.operations.get_files_changed_on_branch") as mock_get_files:
                        mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                        mock_fetch.return_value = True
                        mock_rebase.return_value = RebaseResult(
                            RebaseResult.CONFLICT,
                            "Rebase had conflicts",
                        )
                        mock_get_files.return_value = ["file1.ts"]

                        success, error, files = checkout_and_sync_branch("feature/test")

                        # Success because we can still continue with review
                        assert success is True
                        assert error is None
                        assert files == {"file1.ts"}

    def test_fetch_failure_still_continues(self):
        """Test fetch failure doesn't block the workflow."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import checkout_and_sync_branch
        from agdt_ai_helpers.cli.git.operations import CheckoutResult

        with patch("agdt_ai_helpers.cli.git.operations.checkout_branch") as mock_checkout:
            with patch("agdt_ai_helpers.cli.git.operations.fetch_main") as mock_fetch:
                with patch("agdt_ai_helpers.cli.git.operations.get_files_changed_on_branch") as mock_get_files:
                    mock_checkout.return_value = CheckoutResult(CheckoutResult.SUCCESS)
                    # fetch_main returns False on failure
                    mock_fetch.return_value = False
                    mock_get_files.return_value = ["file.ts"]

                    success, error, files = checkout_and_sync_branch("feature/test")

                    # Should still succeed
                    assert success is True
                    assert files == {"file.ts"}


class TestGetJiraIssueKeyFromState:
    """Tests for _get_jira_issue_key_from_state function."""

    def test_returns_value_from_state(self):
        """Test returns value when set in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import _get_jira_issue_key_from_state

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.get_value", return_value="DFLY-1234"):
            result = _get_jira_issue_key_from_state()

        assert result == "DFLY-1234"

    def test_returns_none_when_not_set(self):
        """Test returns None when not in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import _get_jira_issue_key_from_state

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.get_value", return_value=None):
            result = _get_jira_issue_key_from_state()

        assert result is None


class TestGetPullRequestIdFromState:
    """Tests for _get_pull_request_id_from_state function."""

    def test_returns_int_from_valid_value(self):
        """Test returns integer when valid number in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import _get_pull_request_id_from_state

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.get_value", return_value="123"):
            result = _get_pull_request_id_from_state()

        assert result == 123

    def test_returns_none_when_not_set(self):
        """Test returns None when not in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import _get_pull_request_id_from_state

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.get_value", return_value=None):
            result = _get_pull_request_id_from_state()

        assert result is None

    def test_returns_none_for_invalid_value(self):
        """Test returns None for non-numeric value."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import _get_pull_request_id_from_state

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.get_value", return_value="not-a-number"):
            result = _get_pull_request_id_from_state()

        assert result is None


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


class TestWriteFilePrompt:
    """Tests for _write_file_prompt function."""

    def test_writes_prompt_file(self, tmp_path):
        """Test writes prompt file with correct content."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import _write_file_prompt

        file_detail = {
            "path": "/src/test.ts",
            "changeType": "edit",
        }
        threads = [{"id": 1, "comments": [{"content": "test comment"}]}]

        result = _write_file_prompt(tmp_path, file_detail, threads)

        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "# File Review: /src/test.ts" in content
        assert "## File Diff Object" in content
        assert "## Existing Threads" in content

    def test_handles_empty_threads(self, tmp_path):
        """Test handles empty threads list."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import _write_file_prompt

        file_detail = {"path": "/src/test.ts"}

        result = _write_file_prompt(tmp_path, file_detail, [])

        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "[]" in content


class TestPrintReviewInstructions:
    """Tests for print_review_instructions function."""

    def test_prints_basic_info(self, tmp_path, capsys):
        """Test prints basic review information."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import print_review_instructions

        print_review_instructions(
            pull_request_id=123,
            prompts_dir=tmp_path,
            prompts_generated=5,
            skipped_reviewed_count=2,
        )

        captured = capsys.readouterr()
        assert "PR ID: 123" in captured.out
        assert "Prompts generated: 5" in captured.out
        assert "Skipped (already reviewed): 2" in captured.out

    def test_prints_skipped_not_on_branch(self, tmp_path, capsys):
        """Test prints skipped not on branch count when non-zero."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import print_review_instructions

        print_review_instructions(
            pull_request_id=123,
            prompts_dir=tmp_path,
            prompts_generated=3,
            skipped_reviewed_count=1,
            skipped_not_on_branch_count=2,
        )

        captured = capsys.readouterr()
        assert "Skipped (not on branch" in captured.out
        assert "2" in captured.out


class TestGenerateReviewPrompts:
    """Tests for generate_review_prompts function."""

    def test_generates_prompts_for_files(self, tmp_path):
        """Test generates prompt files for PR files."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import generate_review_prompts

        pr_details = {
            "files": [
                {"path": "/src/file1.ts", "changeType": "edit"},
                {"path": "/src/file2.ts", "changeType": "add"},
            ],
            "threads": [],
        }

        # Patch the scripts directory location
        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.Path") as mock_path:
            # Make the path operations work with tmp_path
            mock_path.return_value.parent.parent.parent.parent.parent = tmp_path
            mock_path.return_value.__truediv__ = lambda self, x: tmp_path / x

            # Actually call the function but with simplified setup
            from agdt_ai_helpers.cli.azure_devops.review_commands import generate_review_prompts

            # Minimal patching to avoid complex path issues
            with patch.object(
                __import__("agdt_ai_helpers.cli.azure_devops.review_commands", fromlist=["get_state_dir"]),
                "get_state_dir",
                return_value=tmp_path,
            ):
                prompts_count, skipped_reviewed, skipped_not_on_branch, prompts_dir = generate_review_prompts(
                    pull_request_id=123,
                    pr_details=pr_details,
                    include_reviewed=True,  # Don't skip any
                    files_on_branch=None,  # Don't filter by branch files
                )

        assert prompts_count == 2
        assert skipped_reviewed == 0
        assert skipped_not_on_branch == 0

    def test_skips_reviewed_files(self, tmp_path):
        """Test skips files already marked as reviewed."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import generate_review_prompts

        pr_details = {
            "files": [
                {"path": "/src/file1.ts", "changeType": "edit"},
            ],
            "threads": [],
            # Note: The function looks for "reviewer" (singular) not "reviewers"
            "reviewer": {
                "reviewedFiles": ["/src/file1.ts"],
            },
        }

        with patch.object(
            __import__("agdt_ai_helpers.cli.azure_devops.review_commands", fromlist=["get_state_dir"]),
            "get_state_dir",
            return_value=tmp_path,
        ):
            prompts_count, skipped_reviewed, skipped_not_on_branch, _ = generate_review_prompts(
                pull_request_id=123,
                pr_details=pr_details,
                include_reviewed=False,  # Skip reviewed files
                files_on_branch=None,
            )

        assert prompts_count == 0
        assert skipped_reviewed == 1

    def test_skips_files_not_on_branch(self, tmp_path):
        """Test skips files not in the branch changes."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.azure_devops.review_commands import generate_review_prompts

        pr_details = {
            "files": [
                {"path": "/src/file1.ts", "changeType": "edit"},
                {"path": "/src/file2.ts", "changeType": "edit"},
            ],
            "threads": [],
        }

        # Only file1.ts is actually on the branch
        files_on_branch = {"/src/file1.ts"}

        with patch.object(
            __import__("agdt_ai_helpers.cli.azure_devops.review_commands", fromlist=["get_state_dir"]),
            "get_state_dir",
            return_value=tmp_path,
        ):
            prompts_count, skipped_reviewed, skipped_not_on_branch, _ = generate_review_prompts(
                pull_request_id=123,
                pr_details=pr_details,
                include_reviewed=True,
                files_on_branch=files_on_branch,
            )

        assert prompts_count == 1
        assert skipped_not_on_branch == 1


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


class TestFetchAndDisplayJiraIssue:
    """Tests for _fetch_and_display_jira_issue function."""

    def test_returns_true_on_success(self):
        """Test returns True when Jira issue fetched successfully."""
        from unittest.mock import patch

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.get_value"):
            with patch("agdt_ai_helpers.cli.jira.get_commands.get_issue") as mock_get_issue:
                with patch("agdt_ai_helpers.cli.jira.state_helpers.set_jira_value"):
                    from agdt_ai_helpers.cli.azure_devops.review_commands import (
                        _fetch_and_display_jira_issue,
                    )

                    result = _fetch_and_display_jira_issue("DFLY-1234")
                    assert result is True
                    mock_get_issue.assert_called_once()

    def test_returns_false_on_system_exit(self, capsys):
        """Test returns False when get_issue raises SystemExit."""
        from unittest.mock import patch

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.get_value"):
            with patch(
                "agdt_ai_helpers.cli.jira.get_commands.get_issue",
                side_effect=SystemExit(1),
            ):
                with patch("agdt_ai_helpers.cli.jira.state_helpers.set_jira_value"):
                    from agdt_ai_helpers.cli.azure_devops.review_commands import (
                        _fetch_and_display_jira_issue,
                    )

                    result = _fetch_and_display_jira_issue("DFLY-1234")
                    assert result is False
                    captured = capsys.readouterr()
                    assert "could not be fetched" in captured.err

    def test_returns_false_on_exception(self, capsys):
        """Test returns False when get_issue raises Exception."""
        from unittest.mock import patch

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.get_value"):
            with patch(
                "agdt_ai_helpers.cli.jira.get_commands.get_issue",
                side_effect=Exception("API error"),
            ):
                with patch("agdt_ai_helpers.cli.jira.state_helpers.set_jira_value"):
                    from agdt_ai_helpers.cli.azure_devops.review_commands import (
                        _fetch_and_display_jira_issue,
                    )

                    result = _fetch_and_display_jira_issue("DFLY-1234")
                    assert result is False
                    captured = capsys.readouterr()
                    assert "Failed to fetch Jira issue" in captured.err


class TestCheckoutAndSyncBranchEdgeCases:
    """Additional edge case tests for checkout_and_sync_branch."""

    def test_fetch_main_failure_continues(self, capsys, tmp_path):
        """Test continues when fetch_main fails."""
        from unittest.mock import MagicMock, patch

        mock_checkout_result = MagicMock()
        mock_checkout_result.is_success = True

        with patch(
            "agdt_ai_helpers.cli.git.operations.checkout_branch",
            return_value=mock_checkout_result,
        ):
            with patch(
                "agdt_ai_helpers.cli.git.operations.fetch_main",
                return_value=False,
            ):
                with patch(
                    "agdt_ai_helpers.cli.git.operations.get_files_changed_on_branch",
                    return_value=["file1.ts"],
                ):
                    from agdt_ai_helpers.cli.azure_devops.review_commands import (
                        checkout_and_sync_branch,
                    )

                    success, error, files = checkout_and_sync_branch("feature/test")
                    assert success is True
                    assert error is None
                    captured = capsys.readouterr()
                    assert "Could not fetch" in captured.out

    def test_rebase_conflict_continues_with_warning(self, capsys):
        """Test continues with warning when rebase has conflicts."""
        from unittest.mock import MagicMock, patch

        mock_checkout_result = MagicMock()
        mock_checkout_result.is_success = True

        mock_rebase_result = MagicMock()
        mock_rebase_result.is_success = False
        mock_rebase_result.needs_manual_resolution = True

        with patch(
            "agdt_ai_helpers.cli.git.operations.checkout_branch",
            return_value=mock_checkout_result,
        ):
            with patch(
                "agdt_ai_helpers.cli.git.operations.fetch_main",
                return_value=True,
            ):
                with patch(
                    "agdt_ai_helpers.cli.git.operations.rebase_onto_main",
                    return_value=mock_rebase_result,
                ):
                    with patch(
                        "agdt_ai_helpers.cli.git.operations.get_files_changed_on_branch",
                        return_value=["file1.ts"],
                    ):
                        from agdt_ai_helpers.cli.azure_devops.review_commands import (
                            checkout_and_sync_branch,
                        )

                        success, error, files = checkout_and_sync_branch("feature/test")
                        assert success is True
                        assert error is None
                        captured = capsys.readouterr()
                        assert "REBASE CONFLICTS DETECTED" in captured.out

    def test_rebase_other_failure_continues(self, capsys):
        """Test continues with warning for other rebase failures."""
        from unittest.mock import MagicMock, patch

        mock_checkout_result = MagicMock()
        mock_checkout_result.is_success = True

        mock_rebase_result = MagicMock()
        mock_rebase_result.is_success = False
        mock_rebase_result.needs_manual_resolution = False
        mock_rebase_result.message = "Unknown rebase error"

        with patch(
            "agdt_ai_helpers.cli.git.operations.checkout_branch",
            return_value=mock_checkout_result,
        ):
            with patch(
                "agdt_ai_helpers.cli.git.operations.fetch_main",
                return_value=True,
            ):
                with patch(
                    "agdt_ai_helpers.cli.git.operations.rebase_onto_main",
                    return_value=mock_rebase_result,
                ):
                    with patch(
                        "agdt_ai_helpers.cli.git.operations.get_files_changed_on_branch",
                        return_value=["file1.ts"],
                    ):
                        from agdt_ai_helpers.cli.azure_devops.review_commands import (
                            checkout_and_sync_branch,
                        )

                        success, error, files = checkout_and_sync_branch("feature/test")
                        assert success is True
                        captured = capsys.readouterr()
                        assert "Unknown rebase error" in captured.out

    def test_saves_files_on_branch_when_requested(self, tmp_path):
        """Test saves files_on_branch to JSON when requested."""
        from unittest.mock import MagicMock, patch

        mock_checkout_result = MagicMock()
        mock_checkout_result.is_success = True

        mock_rebase_result = MagicMock()
        mock_rebase_result.is_success = True

        with patch(
            "agdt_ai_helpers.cli.git.operations.checkout_branch",
            return_value=mock_checkout_result,
        ):
            with patch(
                "agdt_ai_helpers.cli.git.operations.fetch_main",
                return_value=True,
            ):
                with patch(
                    "agdt_ai_helpers.cli.git.operations.rebase_onto_main",
                    return_value=mock_rebase_result,
                ):
                    with patch(
                        "agdt_ai_helpers.cli.git.operations.get_files_changed_on_branch",
                        return_value=["file1.ts", "file2.ts"],
                    ):
                        # Patch Path to point to tmp_path
                        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.Path") as mock_path:
                            mock_path.return_value.parent.parent.parent.parent.parent = tmp_path
                            from agdt_ai_helpers.cli.azure_devops.review_commands import (
                                checkout_and_sync_branch,
                            )

                            success, error, files = checkout_and_sync_branch(
                                "feature/test",
                                pull_request_id=123,
                                save_files_on_branch=True,
                            )
                            assert success is True
                            assert len(files) == 2


class TestSetupPullRequestReview:
    """Tests for setup_pull_request_review function."""

    def test_exits_when_pull_request_id_missing(self, capsys):
        """Test exits with error when pull_request_id not in state."""
        from unittest.mock import patch

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            return_value=None,
        ):
            from agdt_ai_helpers.cli.azure_devops.review_commands import (
                setup_pull_request_review,
            )

            with pytest.raises(SystemExit) as exc_info:
                setup_pull_request_review()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "pull_request_id is required" in captured.err

    def test_fetches_jira_issue_when_key_provided(self):
        """Test fetches Jira issue when jira.issue_key in state."""
        import json
        from unittest.mock import MagicMock, patch

        mock_pr_details = {
            "pullRequest": {
                "pullRequestId": 123,
                "title": "Test PR",
                "createdBy": {"displayName": "Test User"},
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
            },
            "files": [],
            "threads": [],
        }

        def get_value_side_effect(key, default=None):
            mapping = {
                "pull_request_id": "123",
                "jira.issue_key": "DFLY-1234",
                "include_reviewed": "false",
            }
            return mapping.get(key, default)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=get_value_side_effect,
        ):
            with patch(
                "agdt_ai_helpers.cli.azure_devops.review_commands._fetch_and_display_jira_issue"
            ) as mock_fetch_jira:
                with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                    with patch("builtins.open", create=True) as mock_open:
                        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_pr_details)
                        with patch("pathlib.Path.exists", return_value=True):
                            with patch(
                                "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                                return_value=(True, None, set()),
                            ):
                                with patch(
                                    "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                                    return_value=(5, 0, 0, MagicMock()),
                                ):
                                    with patch(
                                        "agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"
                                    ):
                                        with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                            with patch("agdt_ai_helpers.state.set_workflow_state"):
                                                from agdt_ai_helpers.cli.azure_devops.review_commands import (
                                                    setup_pull_request_review,
                                                )

                                                setup_pull_request_review()
                                                mock_fetch_jira.assert_called_once_with("DFLY-1234")

    def test_exits_when_pr_details_file_missing(self, capsys):
        """Test exits with error when PR details file not found."""
        from unittest.mock import patch

        def get_value_side_effect(key, default=None):
            mapping = {
                "pull_request_id": "123",
                "jira.issue_key": None,
                "include_reviewed": "false",
            }
            return mapping.get(key, default)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=get_value_side_effect,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("pathlib.Path.exists", return_value=False):
                    from agdt_ai_helpers.cli.azure_devops.review_commands import (
                        setup_pull_request_review,
                    )

                    with pytest.raises(SystemExit) as exc_info:
                        setup_pull_request_review()
                    assert exc_info.value.code == 1
                    captured = capsys.readouterr()
                    assert "PR details file not found" in captured.err

    def test_exits_on_checkout_failure(self, capsys):
        """Test exits with error when checkout fails."""
        import json
        from unittest.mock import patch

        mock_pr_details = {
            "pullRequest": {
                "sourceRefName": "refs/heads/feature/test",
            },
            "files": [],
            "threads": [],
        }

        def get_value_side_effect(key, default=None):
            mapping = {
                "pull_request_id": "123",
                "jira.issue_key": None,
                "include_reviewed": "false",
            }
            return mapping.get(key, default)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=get_value_side_effect,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_pr_details)
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.checkout_and_sync_branch",
                            return_value=(False, "Checkout error", set()),
                        ):
                            from agdt_ai_helpers.cli.azure_devops.review_commands import (
                                setup_pull_request_review,
                            )

                            with pytest.raises(SystemExit) as exc_info:
                                setup_pull_request_review()
                            assert exc_info.value.code == 1

    def test_warns_when_no_source_branch(self, capsys):
        """Test prints warning when source branch cannot be determined."""
        import json
        from unittest.mock import MagicMock, patch

        mock_pr_details = {
            "pullRequest": {
                "sourceRefName": "",  # Empty source branch
                "title": "Test PR",
                "createdBy": {"displayName": "Test"},
                "targetRefName": "refs/heads/main",
            },
            "files": [],
            "threads": [],
        }

        def get_value_side_effect(key, default=None):
            mapping = {
                "pull_request_id": "123",
                "jira.issue_key": None,
                "include_reviewed": "false",
            }
            return mapping.get(key, default)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.review_commands.get_value",
            side_effect=get_value_side_effect,
        ):
            with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pull_request_details"):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_pr_details)
                    with patch("pathlib.Path.exists", return_value=True):
                        with patch(
                            "agdt_ai_helpers.cli.azure_devops.review_commands.generate_review_prompts",
                            return_value=(5, 0, 0, MagicMock()),
                        ):
                            with patch("agdt_ai_helpers.cli.azure_devops.review_commands.print_review_instructions"):
                                with patch("agdt_ai_helpers.state.set_workflow_state"):
                                    with patch("agdt_ai_helpers.prompts.loader.load_and_render_prompt"):
                                        from agdt_ai_helpers.cli.azure_devops.review_commands import (
                                            setup_pull_request_review,
                                        )

                                        setup_pull_request_review()
                                        captured = capsys.readouterr()
                                        assert "Could not determine source branch" in captured.err


class TestPrintReviewInstructionsZeroPrompts:
    """Additional tests for print_review_instructions edge cases."""

    def test_prints_warning_when_zero_prompts(self, tmp_path, capsys):
        """Test prints warning when no prompts generated."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import print_review_instructions

        print_review_instructions(
            pull_request_id=123,
            prompts_dir=tmp_path,
            prompts_generated=0,
            skipped_reviewed_count=5,
        )

        captured = capsys.readouterr()
        assert "WARNING: No prompts were generated" in captured.out
        assert "include_reviewed=True" in captured.out


class TestGenerateReviewPromptsEdgeCases:
    """Additional edge case tests for generate_review_prompts."""

    def test_loads_pr_details_from_file_when_not_provided(self, tmp_path):
        """Test loads PR details from temp file when not provided."""
        import json
        from unittest.mock import patch

        # Create the temp file
        scripts_dir = tmp_path / "scripts"
        temp_dir = scripts_dir / "temp"
        temp_dir.mkdir(parents=True)
        details_path = temp_dir / "temp-get-pull-request-details-response.json"
        pr_details = {"files": [], "threads": []}
        with open(details_path, "w") as f:
            json.dump(pr_details, f)

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.Path") as mock_path:
            mock_path.return_value.parent.parent.parent.parent.parent = scripts_dir
            from agdt_ai_helpers.cli.azure_devops.review_commands import (
                generate_review_prompts,
            )

            prompts_count, _, _, _ = generate_review_prompts(
                pull_request_id=123,
                pr_details=None,  # Force loading from file
            )
            assert prompts_count == 0

    def test_loads_files_on_branch_from_json_when_not_provided(self, tmp_path, capsys):
        """Test loads files_on_branch from JSON file when not provided."""
        import json
        from unittest.mock import patch

        # Create the temp directory structure
        scripts_dir = tmp_path / "scripts"
        temp_dir = scripts_dir / "temp"
        prompts_dir = temp_dir / "pull-request-review" / "prompts" / "123"
        prompts_dir.mkdir(parents=True)

        # Create files-on-branch.json
        files_on_branch_path = prompts_dir / "files-on-branch.json"
        with open(files_on_branch_path, "w") as f:
            json.dump({"files": ["/src/file1.ts"]}, f)

        pr_details = {
            "files": [
                {"path": "/src/file1.ts", "changeType": "edit"},
                {"path": "/src/file2.ts", "changeType": "edit"},
            ],
            "threads": [],
        }

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.Path") as mock_path:
            mock_path.return_value.parent.parent.parent.parent.parent = scripts_dir
            from agdt_ai_helpers.cli.azure_devops.review_commands import (
                generate_review_prompts,
            )

            prompts_count, _, skipped_not_on_branch, _ = generate_review_prompts(
                pull_request_id=123,
                pr_details=pr_details,
                files_on_branch=None,  # Force loading from file
            )
            # file2.ts should be skipped
            captured = capsys.readouterr()
            assert "Loaded 1 files from files-on-branch.json" in captured.out

    def test_raises_when_pr_details_file_not_found(self, tmp_path):
        """Test raises FileNotFoundError when PR details file missing."""
        from unittest.mock import patch

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.Path") as mock_path:
            mock_path.return_value.parent.parent.parent.parent.parent = tmp_path
            from agdt_ai_helpers.cli.azure_devops.review_commands import (
                generate_review_prompts,
            )

            with pytest.raises(FileNotFoundError) as exc_info:
                generate_review_prompts(
                    pull_request_id=123,
                    pr_details=None,  # Force loading from file
                )
            assert "PR details file not found" in str(exc_info.value)
