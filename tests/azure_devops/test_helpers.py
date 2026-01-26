"""
Tests for Azure DevOps helper functions.
"""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import azure_devops


class TestParseBoolFromState:
    """Tests for parse_bool_from_state helper."""

    def test_none_returns_default_false(self, temp_state_dir, clear_state_before):
        """Test None value returns default False."""
        result = azure_devops.parse_bool_from_state("nonexistent")
        assert result is False

    def test_none_returns_custom_default(self, temp_state_dir, clear_state_before):
        """Test None value returns custom default."""
        result = azure_devops.parse_bool_from_state("nonexistent", default=True)
        assert result is True

    def test_bool_true(self, temp_state_dir, clear_state_before):
        """Test boolean True is returned as-is."""
        state.set_value("test_key", True)
        result = azure_devops.parse_bool_from_state("test_key")
        assert result is True

    def test_bool_false(self, temp_state_dir, clear_state_before):
        """Test boolean False is returned as-is."""
        state.set_value("test_key", False)
        result = azure_devops.parse_bool_from_state("test_key")
        assert result is False

    def test_string_true_variations(self, temp_state_dir, clear_state_before):
        """Test various truthy string values."""
        for truthy in ["1", "true", "True", "TRUE", "yes", "Yes", "YES"]:
            state.set_value("test_key", truthy)
            result = azure_devops.parse_bool_from_state("test_key")
            assert result is True, f"Expected True for '{truthy}'"

    def test_string_false_variations(self, temp_state_dir, clear_state_before):
        """Test various falsy string values."""
        for falsy in ["0", "false", "False", "FALSE", "no", "No", "NO", "anything"]:
            state.set_value("test_key", falsy)
            result = azure_devops.parse_bool_from_state("test_key")
            assert result is False, f"Expected False for '{falsy}'"


class TestRequireRequests:
    """Tests for require_requests helper."""

    def test_returns_requests_when_available(self):
        """Test returns requests module when import succeeds."""
        requests = azure_devops.require_requests()
        assert requests is not None
        assert hasattr(requests, "get")
        assert hasattr(requests, "post")

    def test_exits_when_requests_not_available(self, capsys):
        """Test exits when requests import fails."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "requests":
                raise ImportError("No module named 'requests'")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            with pytest.raises(SystemExit) as exc_info:
                azure_devops.require_requests()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "requests library required" in captured.err


class TestRequireContent:
    """Tests for require_content helper."""

    def test_returns_content_when_set(self, temp_state_dir, clear_state_before):
        """Test returns content when available."""
        state.set_value("content", "Test content")
        result = azure_devops.require_content()
        assert result == "Test content"

    def test_exits_when_content_missing(self, temp_state_dir, clear_state_before):
        """Test exits when content not set."""
        with pytest.raises(SystemExit) as exc_info:
            azure_devops.require_content()
        assert exc_info.value.code == 1


class TestBuildThreadContext:
    """Tests for build_thread_context helper."""

    def test_returns_none_when_no_path(self):
        """Test returns None when path is not set."""
        result = azure_devops.build_thread_context(None, None, None)
        assert result is None

    def test_returns_file_path_only(self):
        """Test returns just file path when no line."""
        result = azure_devops.build_thread_context("src/main.py", None, None)
        assert result == {"filePath": "src/main.py"}

    def test_returns_single_line_context(self):
        """Test returns single line context."""
        result = azure_devops.build_thread_context("src/main.py", 42, None)
        assert result["filePath"] == "src/main.py"
        assert result["rightFileStart"] == {"line": 42, "offset": 1}
        assert result["rightFileEnd"] == {"line": 42, "offset": 1}

    def test_returns_range_context(self):
        """Test returns line range context."""
        result = azure_devops.build_thread_context("src/main.py", 10, 20)
        assert result["filePath"] == "src/main.py"
        assert result["rightFileStart"] == {"line": 10, "offset": 1}
        assert result["rightFileEnd"] == {"line": 20, "offset": 1}

    def test_handles_string_line_numbers(self):
        """Test converts string line numbers to int."""
        result = azure_devops.build_thread_context("src/main.py", "10", "20")
        assert result["rightFileStart"]["line"] == 10
        assert result["rightFileEnd"]["line"] == 20


class TestConvertToPullRequestTitle:
    """Tests for convert_to_pull_request_title helper function."""

    def test_strips_markdown_links(self):
        """Test that Markdown links are converted to plain text."""
        title = "feature([DFLY-1234](https://jira.swica.ch/browse/DFLY-1234)): summary"
        result = azure_devops.convert_to_pull_request_title(title)
        assert result == "feature(DFLY-1234): summary"

    def test_strips_multiple_markdown_links(self):
        """Test multiple Markdown links are converted."""
        title = (
            "feature([DFLY-1234](https://jira.swica.ch/browse/DFLY-1234) / "
            "[DFLY-1235](https://jira.swica.ch/browse/DFLY-1235)): summary"
        )
        result = azure_devops.convert_to_pull_request_title(title)
        assert result == "feature(DFLY-1234/DFLY-1235): summary"

    def test_returns_plain_title_unchanged(self):
        """Test plain titles without links are unchanged."""
        title = "feature(DFLY-1234): summary"
        result = azure_devops.convert_to_pull_request_title(title)
        assert result == "feature(DFLY-1234): summary"

    def test_empty_string(self):
        """Test empty string returns empty string."""
        assert azure_devops.convert_to_pull_request_title("") == ""

    def test_handles_complex_urls(self):
        """Test handles URLs with query params."""
        title = "fix([BUG-123](https://example.com/issues?id=123&foo=bar)): fix bug"
        result = azure_devops.convert_to_pull_request_title(title)
        assert result == "fix(BUG-123): fix bug"


class TestFormatApprovalContent:
    """Tests for format_approval_content helper."""

    def test_adds_sentinel_to_content(self):
        """Test that approval sentinel is added to content."""
        content = "LGTM! All tests pass."
        result = azure_devops.format_approval_content(content)
        assert result.startswith(azure_devops.APPROVAL_SENTINEL)
        assert result.strip().endswith(azure_devops.APPROVAL_SENTINEL)
        assert "LGTM! All tests pass." in result

    def test_already_formatted_unchanged(self):
        """Test already formatted content is unchanged."""
        formatted = f"{azure_devops.APPROVAL_SENTINEL}\n\nContent\n\n{azure_devops.APPROVAL_SENTINEL}"
        result = azure_devops.format_approval_content(formatted)
        assert result == formatted

    def test_empty_string(self):
        """Test empty string gets wrapped."""
        result = azure_devops.format_approval_content("")
        assert azure_devops.APPROVAL_SENTINEL in result


class TestGetRepositoryId:
    """Tests for get_repository_id function."""

    def test_successful_repo_id_fetch(self):
        """Test successful repository ID fetch."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "repo-guid-123\n"

        with patch("subprocess.run", return_value=mock_result):
            repo_id = azure_devops.get_repository_id()
            assert repo_id == "repo-guid-123"

    def test_raises_on_command_failure(self):
        """Test raises RuntimeError on command failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Command failed"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="Failed to get repository ID"):
                azure_devops.get_repository_id()

    def test_raises_on_empty_result(self):
        """Test raises RuntimeError on empty result."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="Empty repository ID"):
                azure_devops.get_repository_id()


class TestPrintThreads:
    """Tests for print_threads helper."""

    def test_prints_basic_thread(self, capsys):
        """Test printing basic thread information."""
        threads = [
            {
                "id": 123,
                "status": "active",
                "threadContext": {},
                "comments": [
                    {
                        "id": 1,
                        "author": {"displayName": "Test User"},
                        "content": "Test comment",
                    }
                ],
            }
        ]

        azure_devops.print_threads(threads)

        captured = capsys.readouterr()
        assert "123" in captured.out
        assert "active" in captured.out
        assert "Test User" in captured.out
        assert "Test comment" in captured.out

    def test_prints_file_context(self, capsys):
        """Test printing thread with file context."""
        threads = [
            {
                "id": 123,
                "status": "active",
                "threadContext": {"filePath": "src/main.py"},
                "comments": [],
            }
        ]

        azure_devops.print_threads(threads)

        captured = capsys.readouterr()
        assert "src/main.py" in captured.out

    def test_truncates_long_content(self, capsys):
        """Test that long content is truncated."""
        long_content = "x" * 200
        threads = [
            {
                "id": 123,
                "status": "active",
                "threadContext": {},
                "comments": [
                    {
                        "id": 1,
                        "author": {"displayName": "User"},
                        "content": long_content,
                    }
                ],
            }
        ]

        azure_devops.print_threads(threads)

        captured = capsys.readouterr()
        assert "..." in captured.out
        assert long_content[:100] in captured.out
        assert long_content[:101] not in captured.out

    def test_prints_multiple_threads(self, capsys):
        """Test printing multiple threads."""
        threads = [
            {"id": 1, "status": "active", "threadContext": {}, "comments": []},
            {"id": 2, "status": "closed", "threadContext": {}, "comments": []},
        ]

        azure_devops.print_threads(threads)

        captured = capsys.readouterr()
        assert "2 thread(s)" in captured.out

    def test_handles_missing_author(self, capsys):
        """Test handles comments without author."""
        threads = [
            {
                "id": 123,
                "status": "active",
                "threadContext": {},
                "comments": [{"id": 1, "content": "Test"}],
            }
        ]

        azure_devops.print_threads(threads)

        captured = capsys.readouterr()
        assert "Unknown" in captured.out


class TestVerifyAzCli:
    """Tests for verify_az_cli helper function."""

    def test_missing_az_cli(self, capsys):
        """Test error when az CLI is not installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            with pytest.raises(SystemExit):
                azure_devops.verify_az_cli()

    def test_missing_devops_extension(self, capsys):
        """Test error when azure-devops extension is not installed."""
        mock_version_result = MagicMock()
        mock_version_result.returncode = 0

        mock_ext_result = MagicMock()
        mock_ext_result.stdout = ""  # No extension found

        with patch("subprocess.run", side_effect=[mock_version_result, mock_ext_result]):
            with pytest.raises(SystemExit):
                azure_devops.verify_az_cli()


class TestParseJsonResponse:
    """Tests for parse_json_response helper function."""

    def test_valid_json(self):
        """Test parsing valid JSON."""
        result = azure_devops.parse_json_response('{"id": 123}', "test")
        assert result == {"id": 123}

    def test_invalid_json(self, capsys):
        """Test error on invalid JSON."""
        with pytest.raises(SystemExit):
            azure_devops.parse_json_response("not valid json", "test")


class TestResolveThreadById:
    """Tests for the resolve_thread_by_id helper function."""

    def test_successful_resolve(self):
        """Test successful thread resolution via helper."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_requests.patch.return_value = mock_response

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        azure_devops.resolve_thread_by_id(mock_requests, headers, config, "repo-123", 456, 789, "fixed")

        mock_requests.patch.assert_called_once()
        call_args = mock_requests.patch.call_args
        assert "threads/789" in call_args[0][0]
        assert call_args[1]["json"]["status"] == "fixed"


class TestFindPullRequestByIssueKey:
    """Tests for find_pull_request_by_issue_key function."""

    def test_finds_pr_by_branch_name(self):
        """Test finding PR by issue key in source branch."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "pullRequestId": 123,
                    "title": "Some feature",
                    "sourceRefName": "refs/heads/feature/DFLY-1234/my-feature",
                    "description": "Description without issue key",
                    "creationDate": "2024-01-01T00:00:00Z",
                }
            ]
        }
        mock_requests.get.return_value = mock_response

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with patch.object(azure_devops.helpers, "require_requests", return_value=mock_requests):
            with patch.object(azure_devops.helpers, "get_repository_id", return_value="repo-id-123"):
                result = azure_devops.find_pull_request_by_issue_key("DFLY-1234", config=config, headers=headers)

        assert result is not None
        assert result["pullRequestId"] == 123

    def test_finds_pr_by_title(self):
        """Test finding PR by issue key in title."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "pullRequestId": 456,
                    "title": "feature(DFLY-1234): Implement feature",
                    "sourceRefName": "refs/heads/feature/other-branch",
                    "description": "",
                    "creationDate": "2024-01-01T00:00:00Z",
                }
            ]
        }
        mock_requests.get.return_value = mock_response

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with patch.object(azure_devops.helpers, "require_requests", return_value=mock_requests):
            with patch.object(azure_devops.helpers, "get_repository_id", return_value="repo-id-123"):
                result = azure_devops.find_pull_request_by_issue_key("DFLY-1234", config=config, headers=headers)

        assert result is not None
        assert result["pullRequestId"] == 456

    def test_finds_pr_by_description(self):
        """Test finding PR by issue key in description."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "pullRequestId": 789,
                    "title": "Some feature",
                    "sourceRefName": "refs/heads/feature/other-branch",
                    "description": "Related to DFLY-1234",
                    "creationDate": "2024-01-01T00:00:00Z",
                }
            ]
        }
        mock_requests.get.return_value = mock_response

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with patch.object(azure_devops.helpers, "require_requests", return_value=mock_requests):
            with patch.object(azure_devops.helpers, "get_repository_id", return_value="repo-id-123"):
                result = azure_devops.find_pull_request_by_issue_key("DFLY-1234", config=config, headers=headers)

        assert result is not None
        assert result["pullRequestId"] == 789

    def test_case_insensitive_matching(self):
        """Test case-insensitive issue key matching."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "pullRequestId": 111,
                    "title": "feature(dfly-1234): lowercase",
                    "sourceRefName": "refs/heads/main",
                    "description": "",
                    "creationDate": "2024-01-01T00:00:00Z",
                }
            ]
        }
        mock_requests.get.return_value = mock_response

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with patch.object(azure_devops.helpers, "require_requests", return_value=mock_requests):
            with patch.object(azure_devops.helpers, "get_repository_id", return_value="repo-id-123"):
                result = azure_devops.find_pull_request_by_issue_key("DFLY-1234", config=config, headers=headers)

        assert result is not None
        assert result["pullRequestId"] == 111

    def test_returns_most_recent_when_multiple_matches(self, capsys):
        """Test returns most recently created PR when multiple match."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "pullRequestId": 100,
                    "title": "Old PR for DFLY-1234",
                    "sourceRefName": "refs/heads/old-branch",
                    "description": "",
                    "creationDate": "2024-01-01T00:00:00Z",
                },
                {
                    "pullRequestId": 200,
                    "title": "Newer PR for DFLY-1234",
                    "sourceRefName": "refs/heads/new-branch",
                    "description": "",
                    "creationDate": "2024-06-01T00:00:00Z",
                },
            ]
        }
        mock_requests.get.return_value = mock_response

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with patch.object(azure_devops.helpers, "require_requests", return_value=mock_requests):
            with patch.object(azure_devops.helpers, "get_repository_id", return_value="repo-id-123"):
                result = azure_devops.find_pull_request_by_issue_key("DFLY-1234", config=config, headers=headers)

        assert result is not None
        assert result["pullRequestId"] == 200  # Most recent

        # Check it printed a warning about multiple matches
        captured = capsys.readouterr()
        assert "Found 2 PRs matching" in captured.out

    def test_returns_none_when_no_matches(self):
        """Test returns None when no PRs match the issue key."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "pullRequestId": 999,
                    "title": "Unrelated PR",
                    "sourceRefName": "refs/heads/other-feature",
                    "description": "No matching key here",
                    "creationDate": "2024-01-01T00:00:00Z",
                }
            ]
        }
        mock_requests.get.return_value = mock_response

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with patch.object(azure_devops.helpers, "require_requests", return_value=mock_requests):
            with patch.object(azure_devops.helpers, "get_repository_id", return_value="repo-id-123"):
                result = azure_devops.find_pull_request_by_issue_key("DFLY-1234", config=config, headers=headers)

        assert result is None

    def test_returns_none_on_api_error(self, capsys):
        """Test returns None on API error."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_requests.get.return_value = mock_response

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with patch.object(azure_devops.helpers, "require_requests", return_value=mock_requests):
            with patch.object(azure_devops.helpers, "get_repository_id", return_value="repo-id-123"):
                result = azure_devops.find_pull_request_by_issue_key("DFLY-1234", config=config, headers=headers)

        assert result is None
        captured = capsys.readouterr()
        assert "Failed to search PRs" in captured.err

    def test_handles_null_description(self):
        """Test handles PR with null description."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "pullRequestId": 123,
                    "title": "DFLY-1234 feature",
                    "sourceRefName": "refs/heads/main",
                    "description": None,
                    "creationDate": "2024-01-01T00:00:00Z",
                }
            ]
        }
        mock_requests.get.return_value = mock_response

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with patch.object(azure_devops.helpers, "require_requests", return_value=mock_requests):
            with patch.object(azure_devops.helpers, "get_repository_id", return_value="repo-id-123"):
                result = azure_devops.find_pull_request_by_issue_key("DFLY-1234", config=config, headers=headers)

        assert result is not None
        assert result["pullRequestId"] == 123


class TestGetPullRequestSourceBranch:
    """Tests for get_pull_request_source_branch function."""

    def test_returns_branch_name_without_refs_prefix(self):
        """Test returns clean branch name without refs/heads/ prefix."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pullRequestId": 123,
            "sourceRefName": "refs/heads/feature/DFLY-1234/implementation",
        }
        mock_requests.get.return_value = mock_response

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with patch.object(azure_devops.helpers, "require_requests", return_value=mock_requests):
            with patch.object(azure_devops.helpers, "get_repository_id", return_value="repo-id-123"):
                result = azure_devops.get_pull_request_source_branch(123, config=config, headers=headers)

        assert result == "feature/DFLY-1234/implementation"

    def test_handles_simple_branch_name(self):
        """Test handles branch names without nested paths."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pullRequestId": 456,
            "sourceRefName": "refs/heads/main",
        }
        mock_requests.get.return_value = mock_response

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with patch.object(azure_devops.helpers, "require_requests", return_value=mock_requests):
            with patch.object(azure_devops.helpers, "get_repository_id", return_value="repo-id-123"):
                result = azure_devops.get_pull_request_source_branch(456, config=config, headers=headers)

        assert result == "main"

    def test_returns_none_on_api_error(self):
        """Test returns None when API returns error."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with patch.object(azure_devops.helpers, "require_requests", return_value=mock_requests):
            with patch.object(azure_devops.helpers, "get_repository_id", return_value="repo-id-123"):
                result = azure_devops.get_pull_request_source_branch(999, config=config, headers=headers)

        assert result is None

    def test_returns_none_when_no_source_ref(self):
        """Test returns None when PR response has no sourceRefName."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pullRequestId": 123,
        }
        mock_requests.get.return_value = mock_response

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with patch.object(azure_devops.helpers, "require_requests", return_value=mock_requests):
            with patch.object(azure_devops.helpers, "get_repository_id", return_value="repo-id-123"):
                result = azure_devops.get_pull_request_source_branch(123, config=config, headers=headers)

        assert result is None

    def test_returns_none_on_generic_exception(self):
        """Test returns None when a generic exception occurs."""
        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("Network timeout")

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with patch.object(azure_devops.helpers, "require_requests", return_value=mock_requests):
            with patch.object(azure_devops.helpers, "get_repository_id", return_value="repo-id-123"):
                result = azure_devops.get_pull_request_source_branch(123, config=config, headers=headers)

        assert result is None

    def test_returns_none_when_repository_id_fails(self):
        """Test returns None when get_repository_id fails."""
        mock_requests = MagicMock()

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with patch.object(azure_devops.helpers, "require_requests", return_value=mock_requests):
            with patch.object(azure_devops.helpers, "get_repository_id", side_effect=RuntimeError("Failed")):
                result = azure_devops.get_pull_request_source_branch(123, config=config, headers=headers)

        assert result is None


class TestGetPullRequestDetails:
    """Tests for get_pull_request_details helper."""

    def test_returns_full_pr_data(self):
        """Test returns full PR data on successful request."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pullRequestId": 123,
            "sourceRefName": "refs/heads/feature/DFLY-1234/test",
            "title": "feature(DFLY-1234): Test PR",
            "description": "Description here",
        }
        mock_requests.get.return_value = mock_response

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with patch.object(azure_devops.helpers, "require_requests", return_value=mock_requests):
            with patch.object(azure_devops.helpers, "get_repository_id", return_value="repo-id-123"):
                result = azure_devops.helpers.get_pull_request_details(123, config=config, headers=headers)

        assert result is not None
        assert result["pullRequestId"] == 123
        assert result["title"] == "feature(DFLY-1234): Test PR"
        assert "DFLY-1234" in result["sourceRefName"]

    def test_returns_none_on_http_error(self):
        """Test returns None on HTTP error."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response

        config = azure_devops.AzureDevOpsConfig(
            organization="https://dev.azure.com/test",
            project="TestProject",
            repository="test-repo",
        )
        headers = {"Authorization": "Basic xyz"}

        with patch.object(azure_devops.helpers, "require_requests", return_value=mock_requests):
            with patch.object(azure_devops.helpers, "get_repository_id", return_value="repo-id-123"):
                result = azure_devops.helpers.get_pull_request_details(123, config=config, headers=headers)

        assert result is None


class TestFindJiraIssueFromPr:
    """Tests for find_jira_issue_from_pr helper."""

    def test_finds_issue_key_in_branch(self):
        """Test extracts issue key from source branch."""
        pr_data = {
            "sourceRefName": "refs/heads/feature/DFLY-1234/my-feature",
            "title": "Some title",
            "description": "Some description",
        }

        with patch.object(azure_devops.helpers, "get_pull_request_details", return_value=pr_data):
            result = azure_devops.helpers.find_jira_issue_from_pr(123)

        assert result == "DFLY-1234"

    def test_finds_issue_key_in_title_when_not_in_branch(self):
        """Test extracts issue key from title when not in branch."""
        pr_data = {
            "sourceRefName": "refs/heads/feature/no-jira-key",
            "title": "feature(DFLY-5678): Fix bug",
            "description": "Some description",
        }

        with patch.object(azure_devops.helpers, "get_pull_request_details", return_value=pr_data):
            result = azure_devops.helpers.find_jira_issue_from_pr(123)

        assert result == "DFLY-5678"

    def test_finds_issue_key_in_description_when_not_elsewhere(self):
        """Test extracts issue key from description as fallback."""
        pr_data = {
            "sourceRefName": "refs/heads/feature/no-jira-key",
            "title": "Some generic title",
            "description": "This fixes DFLY-9999 bug",
        }

        with patch.object(azure_devops.helpers, "get_pull_request_details", return_value=pr_data):
            result = azure_devops.helpers.find_jira_issue_from_pr(123)

        assert result == "DFLY-9999"

    def test_returns_none_when_no_issue_key_found(self):
        """Test returns None when no issue key anywhere."""
        pr_data = {
            "sourceRefName": "refs/heads/feature/no-jira",
            "title": "Generic title",
            "description": "No issue key here",
        }

        with patch.object(azure_devops.helpers, "get_pull_request_details", return_value=pr_data):
            result = azure_devops.helpers.find_jira_issue_from_pr(123)

        assert result is None

    def test_returns_none_when_pr_details_none(self):
        """Test returns None when PR details can't be fetched."""
        with patch.object(azure_devops.helpers, "get_pull_request_details", return_value=None):
            result = azure_devops.helpers.find_jira_issue_from_pr(123)

        assert result is None

    def test_case_insensitive_match(self):
        """Test issue key match is case-insensitive."""
        pr_data = {
            "sourceRefName": "refs/heads/feature/dfly-1234/lowercase",
            "title": "",
            "description": "",
        }

        with patch.object(azure_devops.helpers, "get_pull_request_details", return_value=pr_data):
            result = azure_devops.helpers.find_jira_issue_from_pr(123)

        assert result == "DFLY-1234"  # Always uppercase


class TestFindPrFromJiraIssue:
    """Tests for find_pr_from_jira_issue helper."""

    def test_finds_pr_from_development_panel_first(self):
        """Test finds PR from Jira Development panel first (highest priority)."""
        with patch(
            "agentic_devtools.cli.azure_devops.review_jira.get_pr_from_development_panel", return_value=99999
        ) as mock_dev_panel:
            result = azure_devops.helpers.find_pr_from_jira_issue("DFLY-1234")

        mock_dev_panel.assert_called_once_with("DFLY-1234", verbose=False)
        assert result == 99999

    def test_falls_back_to_ado_search_when_dev_panel_returns_none(self):
        """Test falls back to ADO search when Development panel returns None."""
        with patch("agentic_devtools.cli.azure_devops.review_jira.get_pr_from_development_panel", return_value=None):
            with patch.object(
                azure_devops.helpers, "find_pull_request_by_issue_key", return_value={"pullRequestId": 88888}
            ) as mock_ado:
                result = azure_devops.helpers.find_pr_from_jira_issue("DFLY-1234")

        mock_ado.assert_called_once()
        assert result == 88888

    def test_falls_back_to_ado_search_when_dev_panel_raises(self):
        """Test falls back to ADO search when Development panel raises exception."""
        with patch(
            "agentic_devtools.cli.azure_devops.review_jira.get_pr_from_development_panel",
            side_effect=Exception("Dev panel error"),
        ):
            with patch.object(
                azure_devops.helpers, "find_pull_request_by_issue_key", return_value={"pullRequestId": 77777}
            ) as mock_ado:
                result = azure_devops.helpers.find_pr_from_jira_issue("DFLY-1234")

        mock_ado.assert_called_once()
        assert result == 77777

    def test_falls_back_to_jira_text_patterns_when_ado_returns_none(self):
        """Test falls back to Jira text patterns when ADO search returns None."""
        with patch("agentic_devtools.cli.azure_devops.review_jira.get_pr_from_development_panel", return_value=None):
            with patch.object(azure_devops.helpers, "find_pull_request_by_issue_key", return_value=None):
                with patch(
                    "agentic_devtools.cli.azure_devops.review_jira.get_linked_pull_request_from_jira", return_value=66666
                ) as mock_jira:
                    result = azure_devops.helpers.find_pr_from_jira_issue("DFLY-1234")

        mock_jira.assert_called_once_with("DFLY-1234", verbose=False)
        assert result == 66666

    def test_returns_none_when_no_pr_found_anywhere(self):
        """Test returns None when no method finds a PR."""
        with patch("agentic_devtools.cli.azure_devops.review_jira.get_pr_from_development_panel", return_value=None):
            with patch.object(azure_devops.helpers, "find_pull_request_by_issue_key", return_value=None):
                with patch(
                    "agentic_devtools.cli.azure_devops.review_jira.get_linked_pull_request_from_jira", return_value=None
                ):
                    result = azure_devops.helpers.find_pr_from_jira_issue("DFLY-1234")

        assert result is None

    def test_priority_order_development_panel_over_ado(self):
        """Test Development panel has priority over ADO search."""
        with patch("agentic_devtools.cli.azure_devops.review_jira.get_pr_from_development_panel", return_value=11111):
            with patch.object(
                azure_devops.helpers, "find_pull_request_by_issue_key", return_value={"pullRequestId": 22222}
            ) as mock_ado:
                result = azure_devops.helpers.find_pr_from_jira_issue("DFLY-1234")

        # ADO search should not be called since dev panel found a PR
        mock_ado.assert_not_called()
        assert result == 11111

    def test_priority_order_ado_over_text_patterns(self):
        """Test ADO search has priority over text pattern matching."""
        with patch("agentic_devtools.cli.azure_devops.review_jira.get_pr_from_development_panel", return_value=None):
            with patch.object(
                azure_devops.helpers, "find_pull_request_by_issue_key", return_value={"pullRequestId": 33333}
            ):
                with patch(
                    "agentic_devtools.cli.azure_devops.review_jira.get_linked_pull_request_from_jira", return_value=44444
                ) as mock_jira:
                    result = azure_devops.helpers.find_pr_from_jira_issue("DFLY-1234")

        # Jira text pattern should not be called since ADO found a PR
        mock_jira.assert_not_called()
        assert result == 33333

    def test_verbose_flag_passed_to_all_methods(self, capsys):
        """Test verbose flag is passed to all lookup methods."""
        with patch(
            "agentic_devtools.cli.azure_devops.review_jira.get_pr_from_development_panel", return_value=None
        ) as mock_dev:
            with patch.object(azure_devops.helpers, "find_pull_request_by_issue_key", return_value=None):
                with patch(
                    "agentic_devtools.cli.azure_devops.review_jira.get_linked_pull_request_from_jira", return_value=None
                ) as mock_jira:
                    azure_devops.helpers.find_pr_from_jira_issue("DFLY-1234", verbose=True)

        mock_dev.assert_called_once_with("DFLY-1234", verbose=True)
        mock_jira.assert_called_once_with("DFLY-1234", verbose=True)
