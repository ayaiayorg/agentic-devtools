"""
Tests for Jira CLI commands (create_epic, create_issue, create_subtask, add_comment, get_issue).

These tests validate the command-line interface functions that create and manage Jira issues.
They use mocked API calls to avoid network dependencies.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from dfly_ai_helpers import state
from dfly_ai_helpers.cli import jira
from dfly_ai_helpers.cli.jira import (
    comment_commands,
    create_commands,
    get_commands,
)


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state.clear_state()
    yield


@pytest.fixture
def mock_jira_env():
    """Set up environment for Jira API calls."""
    with patch.dict("os.environ", {"JIRA_COPILOT_PAT": "test-token"}):
        yield


@pytest.fixture
def mock_requests_module():
    """Mock the requests module for API calls."""
    mock_module = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"key": "DFLY-9999", "id": "12345"}
    mock_response.raise_for_status = MagicMock()
    mock_module.post.return_value = mock_response
    mock_module.get.return_value = mock_response
    # Patch in all implementation modules where _get_requests is imported
    with patch.object(create_commands, "_get_requests", return_value=mock_module):
        with patch.object(comment_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "_get_requests", return_value=mock_module):
                yield mock_module


class TestCreateIssueSyncWithMock:
    """Tests for create_issue_sync with mocked API calls."""

    def test_create_issue_sync_success(self, mock_jira_env, mock_requests_module):
        """Test successful issue creation."""
        result = jira.create_issue_sync(
            project_key="DFLY",
            summary="Test Issue",
            issue_type="Task",
            description="Test description",
            labels=["test-label"],
        )

        assert result["key"] == "DFLY-9999"
        mock_requests_module.post.assert_called_once()
        call_args = mock_requests_module.post.call_args
        assert "issue" in call_args[0][0]

    def test_create_issue_sync_with_epic_name(self, mock_jira_env, mock_requests_module):
        """Test issue creation with epic name field."""
        jira.create_issue_sync(
            project_key="DFLY",
            summary="Test Epic",
            issue_type="Epic",
            description="Epic description",
            labels=["epic-label"],
            epic_name="TEST-EPIC",
        )

        call_args = mock_requests_module.post.call_args
        payload = call_args[1]["json"]
        assert jira.EPIC_NAME_FIELD in payload["fields"]
        assert payload["fields"][jira.EPIC_NAME_FIELD] == "TEST-EPIC"

    def test_create_issue_sync_with_parent_key(self, mock_jira_env, mock_requests_module):
        """Test subtask creation with parent key."""
        jira.create_issue_sync(
            project_key="DFLY",
            summary="Test Subtask",
            issue_type="Sub-task",
            description="Subtask description",
            labels=["subtask-label"],
            parent_key="DFLY-1234",
        )

        call_args = mock_requests_module.post.call_args
        payload = call_args[1]["json"]
        assert payload["fields"]["parent"]["key"] == "DFLY-1234"

    def test_create_issue_sync_subtask_variant(self, mock_jira_env, mock_requests_module):
        """Test subtask creation with lowercase 'subtask' type."""
        jira.create_issue_sync(
            project_key="DFLY",
            summary="Test Subtask",
            issue_type="subtask",
            description="Subtask description",
            labels=[],
            parent_key="DFLY-5678",
        )

        call_args = mock_requests_module.post.call_args
        payload = call_args[1]["json"]
        assert payload["fields"]["parent"]["key"] == "DFLY-5678"


class TestCreateEpicDryRun:
    """Tests for create_epic command in dry run mode."""

    def test_create_epic_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test create_epic in dry run mode."""
        jira.set_jira_value("summary", "Test Epic")
        jira.set_jira_value("epic_name", "TEST-EPIC")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "test functionality")
        jira.set_jira_value("benefit", "test coverage")
        jira.set_jira_value("dry_run", True)

        jira.create_epic()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Test Epic" in captured.out
        assert "TEST-EPIC" in captured.out

    def test_create_epic_missing_summary(self, temp_state_dir, clear_state_before):
        """Test create_epic fails with missing summary."""
        jira.set_jira_value("epic_name", "TEST")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_epic()
        assert exc_info.value.code == 1

    def test_create_epic_missing_epic_name(self, temp_state_dir, clear_state_before):
        """Test create_epic fails with missing epic_name."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_epic()
        assert exc_info.value.code == 1

    def test_create_epic_missing_role(self, temp_state_dir, clear_state_before):
        """Test create_epic fails with missing role."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("epic_name", "TEST")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_epic()
        assert exc_info.value.code == 1

    def test_create_epic_missing_desired_outcome(self, temp_state_dir, clear_state_before):
        """Test create_epic fails with missing desired_outcome."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("epic_name", "TEST")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_epic()
        assert exc_info.value.code == 1

    def test_create_epic_missing_benefit(self, temp_state_dir, clear_state_before):
        """Test create_epic fails with missing benefit."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("epic_name", "TEST")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "feature")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_epic()
        assert exc_info.value.code == 1


class TestCreateEpicWithMock:
    """Tests for create_epic with mocked API calls."""

    def test_create_epic_success(
        self,
        temp_state_dir,
        clear_state_before,
        mock_jira_env,
        mock_requests_module,
        capsys,
    ):
        """Test successful epic creation."""
        jira.set_jira_value("summary", "Test Epic")
        jira.set_jira_value("epic_name", "TEST-EPIC")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "test functionality")
        jira.set_jira_value("benefit", "test coverage")

        jira.create_epic()

        captured = capsys.readouterr()
        assert "DFLY-9999" in captured.out
        assert "Epic created successfully" in captured.out

    def test_create_epic_api_error(self, temp_state_dir, clear_state_before, mock_jira_env):
        """Test create_epic handles API error."""
        jira.set_jira_value("summary", "Test Epic")
        jira.set_jira_value("epic_name", "TEST-EPIC")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "test")
        jira.set_jira_value("benefit", "test")

        mock_module = MagicMock()
        mock_module.post.side_effect = Exception("API Error")
        with patch.object(create_commands, "_get_requests", return_value=mock_module):
            with pytest.raises(SystemExit) as exc_info:
                jira.create_epic()
            assert exc_info.value.code == 1


class TestCreateIssueDryRun:
    """Tests for create_issue command in dry run mode."""

    def test_create_issue_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test create_issue in dry run mode."""
        jira.set_jira_value("summary", "Test Issue")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "functionality")
        jira.set_jira_value("benefit", "value")
        jira.set_jira_value("dry_run", True)

        jira.create_issue()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Test Issue" in captured.out

    def test_create_issue_custom_type(self, temp_state_dir, clear_state_before, capsys):
        """Test create_issue with custom issue type."""
        jira.set_jira_value("summary", "Test Bug")
        jira.set_jira_value("issue_type", "Bug")
        jira.set_jira_value("role", "tester")
        jira.set_jira_value("desired_outcome", "bug fix")
        jira.set_jira_value("benefit", "stability")
        jira.set_jira_value("dry_run", True)

        jira.create_issue()

        captured = capsys.readouterr()
        assert "Bug" in captured.out

    def test_create_issue_missing_summary(self, temp_state_dir, clear_state_before):
        """Test create_issue fails with missing summary."""
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_issue()
        assert exc_info.value.code == 1

    def test_create_issue_missing_role(self, temp_state_dir, clear_state_before):
        """Test create_issue fails with missing role."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_issue()
        assert exc_info.value.code == 1

    def test_create_issue_missing_desired_outcome(self, temp_state_dir, clear_state_before):
        """Test create_issue fails with missing desired_outcome."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_issue()
        assert exc_info.value.code == 1

    def test_create_issue_missing_benefit(self, temp_state_dir, clear_state_before):
        """Test create_issue fails with missing benefit."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "feature")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_issue()
        assert exc_info.value.code == 1


class TestCreateIssueWithMock:
    """Tests for create_issue with mocked API calls."""

    def test_create_issue_success(
        self,
        temp_state_dir,
        clear_state_before,
        mock_jira_env,
        mock_requests_module,
        capsys,
    ):
        """Test successful issue creation."""
        jira.set_jira_value("summary", "Test Issue")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        jira.create_issue()

        captured = capsys.readouterr()
        assert "DFLY-9999" in captured.out
        assert "created successfully" in captured.out

    def test_create_issue_api_error(self, temp_state_dir, clear_state_before, mock_jira_env):
        """Test create_issue handles API error."""
        jira.set_jira_value("summary", "Test Issue")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        mock_module = MagicMock()
        mock_module.post.side_effect = Exception("API Error")
        with patch.object(create_commands, "_get_requests", return_value=mock_module):
            with pytest.raises(SystemExit) as exc_info:
                jira.create_issue()
            assert exc_info.value.code == 1


class TestCreateSubtaskDryRun:
    """Tests for create_subtask command in dry run mode."""

    def test_create_subtask_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test create_subtask in dry run mode."""
        jira.set_jira_value("parent_key", "DFLY-1234")
        jira.set_jira_value("summary", "Test Subtask")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "subtask work")
        jira.set_jira_value("benefit", "progress")
        jira.set_jira_value("dry_run", True)

        jira.create_subtask()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "DFLY-1234" in captured.out
        assert "Test Subtask" in captured.out

    def test_create_subtask_missing_parent(self, temp_state_dir, clear_state_before):
        """Test create_subtask fails with missing parent_key."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "work")
        jira.set_jira_value("benefit", "progress")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_subtask()
        assert exc_info.value.code == 1

    def test_create_subtask_missing_summary(self, temp_state_dir, clear_state_before):
        """Test create_subtask fails with missing summary."""
        jira.set_jira_value("parent_key", "DFLY-1234")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "work")
        jira.set_jira_value("benefit", "progress")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_subtask()
        assert exc_info.value.code == 1

    def test_create_subtask_missing_role(self, temp_state_dir, clear_state_before):
        """Test create_subtask fails with missing role."""
        jira.set_jira_value("parent_key", "DFLY-1234")
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("desired_outcome", "work")
        jira.set_jira_value("benefit", "progress")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_subtask()
        assert exc_info.value.code == 1

    def test_create_subtask_missing_desired_outcome(self, temp_state_dir, clear_state_before):
        """Test create_subtask fails with missing desired_outcome."""
        jira.set_jira_value("parent_key", "DFLY-1234")
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("benefit", "progress")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_subtask()
        assert exc_info.value.code == 1

    def test_create_subtask_missing_benefit(self, temp_state_dir, clear_state_before):
        """Test create_subtask fails with missing benefit."""
        jira.set_jira_value("parent_key", "DFLY-1234")
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "work")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_subtask()
        assert exc_info.value.code == 1


class TestCreateSubtaskWithMock:
    """Tests for create_subtask with mocked API calls."""

    def test_create_subtask_success(
        self,
        temp_state_dir,
        clear_state_before,
        mock_jira_env,
        mock_requests_module,
        capsys,
    ):
        """Test successful subtask creation."""
        jira.set_jira_value("parent_key", "DFLY-1234")
        jira.set_jira_value("summary", "Test Subtask")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "subtask work")
        jira.set_jira_value("benefit", "progress")

        jira.create_subtask()

        captured = capsys.readouterr()
        assert "DFLY-9999" in captured.out
        assert "Sub-task created successfully" in captured.out

    def test_create_subtask_api_error(self, temp_state_dir, clear_state_before, mock_jira_env):
        """Test create_subtask handles API error."""
        jira.set_jira_value("parent_key", "DFLY-1234")
        jira.set_jira_value("summary", "Test Subtask")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "subtask work")
        jira.set_jira_value("benefit", "progress")

        mock_module = MagicMock()
        mock_module.post.side_effect = Exception("API Error")
        with patch.object(create_commands, "_get_requests", return_value=mock_module):
            with pytest.raises(SystemExit) as exc_info:
                jira.create_subtask()
            assert exc_info.value.code == 1


class TestAddCommentDryRun:
    """Tests for add_comment command in dry run mode."""

    def test_add_comment_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test add_comment in dry run mode."""
        jira.set_jira_value("issue_key", "DFLY-1234")
        jira.set_jira_value("comment", "This is a test comment")
        jira.set_jira_value("dry_run", True)

        jira.add_comment()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "DFLY-1234" in captured.out

    def test_add_comment_missing_issue_key(self, temp_state_dir, clear_state_before):
        """Test add_comment fails with missing issue_key."""
        jira.set_jira_value("comment", "Test comment")

        with pytest.raises(SystemExit) as exc_info:
            jira.add_comment()
        assert exc_info.value.code == 1

    def test_add_comment_missing_comment(self, temp_state_dir, clear_state_before):
        """Test add_comment fails with missing comment."""
        jira.set_jira_value("issue_key", "DFLY-1234")

        with pytest.raises(SystemExit) as exc_info:
            jira.add_comment()
        assert exc_info.value.code == 1


class TestAddCommentWithMock:
    """Tests for add_comment with mocked API calls."""

    def test_add_comment_success(self, temp_state_dir, clear_state_before, mock_jira_env, capsys):
        """Test successful comment addition."""
        jira.set_jira_value("issue_key", "DFLY-1234")
        jira.set_jira_value("comment", "Test comment")

        mock_module = MagicMock()
        # Mock the POST response for adding comment
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {"id": "comment-123"}
        mock_post_response.raise_for_status = MagicMock()
        mock_module.post.return_value = mock_post_response

        # Mock the GET response for refreshing issue details
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Test Issue",
                "description": "Test description",
                "issuetype": {"name": "Task"},
                "labels": ["test"],
                "comment": {"comments": []},
            },
        }
        mock_get_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_get_response

        with patch.object(comment_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "_get_requests", return_value=mock_module):
                with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                    jira.add_comment()

        captured = capsys.readouterr()
        assert "Comment added successfully" in captured.out

    def test_add_comment_api_error(self, temp_state_dir, clear_state_before, mock_jira_env):
        """Test add_comment handles API error."""
        jira.set_jira_value("issue_key", "DFLY-1234")
        jira.set_jira_value("comment", "Test comment")

        mock_module = MagicMock()
        mock_module.post.side_effect = Exception("API Error")
        with patch.object(comment_commands, "_get_requests", return_value=mock_module):
            with pytest.raises(SystemExit) as exc_info:
                jira.add_comment()
            assert exc_info.value.code == 1


class TestGetIssueDryRun:
    """Tests for get_issue command validation."""

    def test_get_issue_missing_key(self, temp_state_dir, clear_state_before):
        """Test get_issue fails without issue key."""
        with pytest.raises(SystemExit) as exc_info:
            jira.get_issue()
        assert exc_info.value.code == 1


class TestGetIssueWithMock:
    """Tests for get_issue with mocked API calls."""

    def test_get_issue_success(self, temp_state_dir, clear_state_before, mock_jira_env, capsys):
        """Test successful issue retrieval."""
        jira.set_jira_value("issue_key", "DFLY-1234")

        mock_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Test Issue",
                "description": "Test description",
                "issuetype": {"name": "Task"},
                "labels": ["test-label"],
                "comment": {"comments": []},
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        assert "DFLY-1234" in captured.out
        assert "Test Issue" in captured.out

    def test_get_issue_with_adf_description(self, temp_state_dir, clear_state_before, mock_jira_env, capsys):
        """Test get_issue handles ADF description format."""
        jira.set_jira_value("issue_key", "DFLY-1234")

        mock_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Test Issue",
                "description": {
                    "type": "doc",
                    "content": [{"type": "paragraph", "content": [{"text": "ADF paragraph"}]}],
                },
                "issuetype": {"name": "Task"},
                "labels": [],
                "comment": {"comments": []},
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        assert "ADF paragraph" in captured.out

    def test_get_issue_with_comments(self, temp_state_dir, clear_state_before, mock_jira_env, capsys):
        """Test get_issue displays comments."""
        jira.set_jira_value("issue_key", "DFLY-1234")

        mock_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Test Issue",
                "description": "Description",
                "issuetype": {"name": "Task"},
                "labels": [],
                "comment": {
                    "comments": [
                        {
                            "id": "123",
                            "body": "First comment",
                            "author": {"displayName": "Test User"},
                            "created": "2024-01-01T12:00:00Z",
                        }
                    ]
                },
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        assert "First comment" in captured.out
        assert "Test User" in captured.out

    def test_get_issue_with_adf_comments(self, temp_state_dir, clear_state_before, mock_jira_env, capsys):
        """Test get_issue handles ADF format in comments."""
        jira.set_jira_value("issue_key", "DFLY-1234")

        mock_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Test Issue",
                "description": "Description",
                "issuetype": {"name": "Task"},
                "labels": [],
                "comment": {
                    "comments": [
                        {
                            "id": "456",
                            "body": {
                                "type": "doc",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"text": "ADF comment"}],
                                    }
                                ],
                            },
                            "author": {"name": "user1"},
                            "created": "2024-01-02T12:00:00Z",
                        }
                    ]
                },
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        assert "ADF comment" in captured.out

    def test_get_issue_no_description(self, temp_state_dir, clear_state_before, mock_jira_env, capsys):
        """Test get_issue handles missing description."""
        jira.set_jira_value("issue_key", "DFLY-1234")

        mock_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Test Issue",
                "description": None,
                "issuetype": {"name": "Task"},
                "labels": [],
                "comment": {"comments": []},
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        assert "No description" in captured.out

    def test_get_issue_saves_json_file(self, temp_state_dir, clear_state_before, mock_jira_env):
        """Test get_issue saves JSON response to file."""
        jira.set_jira_value("issue_key", "DFLY-1234")

        mock_module = MagicMock()
        mock_response = MagicMock()
        response_data = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Test",
                "description": "Desc",
                "issuetype": {"name": "Task"},
                "labels": [],
                "comment": {"comments": []},
            },
        }
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        json_file = temp_state_dir / "temp-get-issue-details-response.json"
        assert json_file.exists()
        content = json.loads(json_file.read_text(encoding="utf-8"))
        assert content["key"] == "DFLY-1234"

    def test_get_issue_api_error(self, temp_state_dir, clear_state_before, mock_jira_env):
        """Test get_issue handles API error."""
        jira.set_jira_value("issue_key", "DFLY-1234")

        mock_module = MagicMock()
        mock_module.get.side_effect = Exception("API Error")
        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with pytest.raises(SystemExit) as exc_info:
                jira.get_issue()
            assert exc_info.value.code == 1

    def test_get_issue_empty_issuetype(self, temp_state_dir, clear_state_before, mock_jira_env, capsys):
        """Test get_issue handles empty issuetype."""
        jira.set_jira_value("issue_key", "DFLY-1234")

        mock_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Test",
                "description": "Desc",
                "issuetype": {},
                "labels": [],
                "comment": {"comments": []},
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        assert "Issue Type: none" in captured.out

    def test_get_issue_non_string_description(self, temp_state_dir, clear_state_before, mock_jira_env, capsys):
        """Test get_issue handles non-string, non-dict description."""
        jira.set_jira_value("issue_key", "DFLY-1234")

        mock_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Test",
                "description": 12345,  # Integer description
                "issuetype": {"name": "Task"},
                "labels": [],
                "comment": {"comments": []},
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        assert "12345" in captured.out

    def test_get_issue_with_linked_pull_requests(self, temp_state_dir, clear_state_before, mock_jira_env, capsys):
        """Test get_issue displays linked pull requests."""
        jira.set_jira_value("issue_key", "DFLY-1234")

        mock_module = MagicMock()

        # Main issue response
        mock_issue_response = MagicMock()
        mock_issue_response.json.return_value = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Test Issue",
                "description": "Test description",
                "issuetype": {"name": "Task"},
                "labels": [],
                "comment": {"comments": []},
            },
        }
        mock_issue_response.raise_for_status = MagicMock()

        # Remote links response with PR link
        mock_links_response = MagicMock()
        mock_links_response.json.return_value = [
            {
                "object": {
                    "title": "PR #123: Fix the bug",
                    "url": "https://dev.azure.com/org/project/_git/repo/pullrequest/123",
                    "icon": {"url16x16": "https://dev.azure.com/pullrequest-icon.png"},
                    "status": {"resolved": False},
                }
            }
        ]
        mock_links_response.raise_for_status = MagicMock()

        # First call is issue, second is remote links
        mock_module.get.side_effect = [mock_issue_response, mock_links_response]

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        assert "Linked Pull Requests:" in captured.out
        assert "PR #123: Fix the bug" in captured.out
        assert "(open)" in captured.out

    def test_get_issue_with_merged_pull_request(self, temp_state_dir, clear_state_before, mock_jira_env, capsys):
        """Test get_issue displays merged PR status correctly."""
        jira.set_jira_value("issue_key", "DFLY-1234")

        mock_module = MagicMock()

        mock_issue_response = MagicMock()
        mock_issue_response.json.return_value = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Test Issue",
                "description": "Test",
                "issuetype": {"name": "Task"},
                "labels": [],
                "comment": {"comments": []},
            },
        }
        mock_issue_response.raise_for_status = MagicMock()

        # Remote links with merged PR
        mock_links_response = MagicMock()
        mock_links_response.json.return_value = [
            {
                "object": {
                    "title": "Merged PR",
                    "url": "https://example.com/pullrequest/456",
                    "status": {"resolved": True},
                }
            }
        ]
        mock_links_response.raise_for_status = MagicMock()

        mock_module.get.side_effect = [mock_issue_response, mock_links_response]

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        assert "(merged)" in captured.out

    def test_get_issue_with_non_pr_remote_links(self, temp_state_dir, clear_state_before, mock_jira_env, capsys):
        """Test get_issue displays non-PR remote links."""
        jira.set_jira_value("issue_key", "DFLY-1234")

        mock_module = MagicMock()

        mock_issue_response = MagicMock()
        mock_issue_response.json.return_value = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Test Issue",
                "description": "Test",
                "issuetype": {"name": "Task"},
                "labels": [],
                "comment": {"comments": []},
            },
        }
        mock_issue_response.raise_for_status = MagicMock()

        # Remote links without PR indicators
        mock_links_response = MagicMock()
        mock_links_response.json.return_value = [
            {
                "object": {
                    "title": "Confluence Page",
                    "url": "https://confluence.example.com/page/123",
                }
            }
        ]
        mock_links_response.raise_for_status = MagicMock()

        mock_module.get.side_effect = [mock_issue_response, mock_links_response]

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        assert "Linked Items:" in captured.out
        assert "Confluence Page" in captured.out

    def test_get_issue_no_remote_links(self, temp_state_dir, clear_state_before, mock_jira_env, capsys):
        """Test get_issue handles no remote links."""
        jira.set_jira_value("issue_key", "DFLY-1234")

        mock_module = MagicMock()

        mock_issue_response = MagicMock()
        mock_issue_response.json.return_value = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Test Issue",
                "description": "Test",
                "issuetype": {"name": "Task"},
                "labels": [],
                "comment": {"comments": []},
            },
        }
        mock_issue_response.raise_for_status = MagicMock()

        mock_links_response = MagicMock()
        mock_links_response.json.return_value = []
        mock_links_response.raise_for_status = MagicMock()

        mock_module.get.side_effect = [mock_issue_response, mock_links_response]

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        assert "Linked Pull Requests: none" in captured.out


class TestFetchRemoteLinks:
    """Tests for _fetch_remote_links function."""

    def test_returns_empty_list_on_exception(self, mock_jira_env):
        """Test _fetch_remote_links returns empty list on API error."""
        mock_module = MagicMock()
        mock_module.get.side_effect = Exception("Network error")

        result = get_commands._fetch_remote_links(
            mock_module, "https://jira.example.com", "DFLY-1234", {"Authorization": "Basic xxx"}
        )

        assert result == []

    def test_returns_empty_list_for_non_list_response(self, mock_jira_env):
        """Test _fetch_remote_links handles non-list response."""
        mock_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "not a list"}
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        result = get_commands._fetch_remote_links(
            mock_module, "https://jira.example.com", "DFLY-1234", {"Authorization": "Basic xxx"}
        )

        assert result == []

    def test_returns_list_of_remote_links(self, mock_jira_env):
        """Test _fetch_remote_links returns list of links."""
        mock_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"object": {"title": "Link 1"}},
            {"object": {"title": "Link 2"}},
        ]
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        result = get_commands._fetch_remote_links(
            mock_module, "https://jira.example.com", "DFLY-1234", {"Authorization": "Basic xxx"}
        )

        assert len(result) == 2


class TestGetIssueSubtaskParentDetection:
    """Tests for automatic subtask parent detection and retrieval."""

    def test_get_issue_detects_subtask_and_fetches_parent(
        self, temp_state_dir, clear_state_before, mock_jira_env, capsys
    ):
        """Test get_issue automatically fetches parent when issue is a subtask."""
        jira.set_jira_value("issue_key", "DFLY-5678")

        mock_module = MagicMock()

        # Subtask issue response
        mock_subtask_response = MagicMock()
        mock_subtask_response.json.return_value = {
            "key": "DFLY-5678",
            "fields": {
                "summary": "Subtask to fix bug",
                "description": "Subtask description",
                "issuetype": {"name": "Sub-task", "subtask": True},
                "labels": [],
                "comment": {"comments": []},
                "parent": {"key": "DFLY-1234"},
            },
        }
        mock_subtask_response.raise_for_status = MagicMock()

        # Parent issue response
        mock_parent_response = MagicMock()
        mock_parent_response.json.return_value = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Parent story for the bug fix",
                "description": "Parent description",
                "issuetype": {"name": "Story", "subtask": False},
                "labels": ["parent-label"],
                "comment": {"comments": []},
            },
        }
        mock_parent_response.raise_for_status = MagicMock()

        # Remote links response (empty)
        mock_links_response = MagicMock()
        mock_links_response.json.return_value = []
        mock_links_response.raise_for_status = MagicMock()

        # Order: subtask issue, parent issue, remote links
        mock_module.get.side_effect = [mock_subtask_response, mock_parent_response, mock_links_response]

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        assert "Detected subtask of DFLY-1234" in captured.out
        assert "Parent issue details saved to:" in captured.out
        assert "Parent Issue: DFLY-1234 - Parent story for the bug fix" in captured.out

    def test_get_issue_saves_parent_json_file(self, temp_state_dir, clear_state_before, mock_jira_env):
        """Test get_issue saves parent issue to separate JSON file."""
        jira.set_jira_value("issue_key", "DFLY-5678")

        mock_module = MagicMock()

        mock_subtask_response = MagicMock()
        mock_subtask_response.json.return_value = {
            "key": "DFLY-5678",
            "fields": {
                "summary": "Subtask",
                "description": "Desc",
                "issuetype": {"name": "Sub-task", "subtask": True},
                "labels": [],
                "comment": {"comments": []},
                "parent": {"key": "DFLY-1234"},
            },
        }
        mock_subtask_response.raise_for_status = MagicMock()

        mock_parent_response = MagicMock()
        parent_data = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Parent Issue",
                "description": "Parent desc",
                "issuetype": {"name": "Story"},
                "labels": [],
                "comment": {"comments": []},
            },
        }
        mock_parent_response.json.return_value = parent_data
        mock_parent_response.raise_for_status = MagicMock()

        mock_links_response = MagicMock()
        mock_links_response.json.return_value = []
        mock_links_response.raise_for_status = MagicMock()

        mock_module.get.side_effect = [mock_subtask_response, mock_parent_response, mock_links_response]

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        # Check both files exist
        issue_file = temp_state_dir / "temp-get-issue-details-response.json"
        parent_file = temp_state_dir / "temp-get-parent-issue-details-response.json"
        assert issue_file.exists()
        assert parent_file.exists()

        # Verify parent file contents
        parent_content = json.loads(parent_file.read_text(encoding="utf-8"))
        assert parent_content["key"] == "DFLY-1234"
        assert parent_content["fields"]["summary"] == "Parent Issue"

    def test_get_issue_sets_parent_key_in_state(self, temp_state_dir, clear_state_before, mock_jira_env):
        """Test get_issue stores parent key in state for follow-up."""
        jira.set_jira_value("issue_key", "DFLY-5678")

        mock_module = MagicMock()

        mock_subtask_response = MagicMock()
        mock_subtask_response.json.return_value = {
            "key": "DFLY-5678",
            "fields": {
                "summary": "Subtask",
                "description": "Desc",
                "issuetype": {"name": "Sub-task", "subtask": True},
                "labels": [],
                "comment": {"comments": []},
                "parent": {"key": "DFLY-1234"},
            },
        }
        mock_subtask_response.raise_for_status = MagicMock()

        mock_parent_response = MagicMock()
        mock_parent_response.json.return_value = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Parent",
                "description": "Desc",
                "issuetype": {"name": "Story"},
                "labels": [],
                "comment": {"comments": []},
            },
        }
        mock_parent_response.raise_for_status = MagicMock()

        mock_links_response = MagicMock()
        mock_links_response.json.return_value = []
        mock_links_response.raise_for_status = MagicMock()

        mock_module.get.side_effect = [mock_subtask_response, mock_parent_response, mock_links_response]

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        # Verify parent metadata reference was stored in state (not raw key)
        parent_details = state.get_value("jira.parent_issue_details")
        assert parent_details is not None
        assert parent_details["key"] == "DFLY-1234"
        assert "location" in parent_details
        assert "retrievalTimestamp" in parent_details

    def test_get_issue_non_subtask_no_parent_fetch(self, temp_state_dir, clear_state_before, mock_jira_env, capsys):
        """Test get_issue does not fetch parent for non-subtask issues."""
        jira.set_jira_value("issue_key", "DFLY-1234")

        mock_module = MagicMock()

        mock_issue_response = MagicMock()
        mock_issue_response.json.return_value = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Regular Story",
                "description": "Description",
                "issuetype": {"name": "Story", "subtask": False},
                "labels": [],
                "comment": {"comments": []},
            },
        }
        mock_issue_response.raise_for_status = MagicMock()

        mock_links_response = MagicMock()
        mock_links_response.json.return_value = []
        mock_links_response.raise_for_status = MagicMock()

        # Only two calls: issue and remote links (no parent fetch)
        mock_module.get.side_effect = [mock_issue_response, mock_links_response]

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        assert "Detected subtask" not in captured.out
        assert "Parent issue" not in captured.out

        # Verify parent file does not exist
        parent_file = temp_state_dir / "temp-get-parent-issue-details-response.json"
        assert not parent_file.exists()

    def test_get_issue_subtask_parent_fetch_failure(self, temp_state_dir, clear_state_before, mock_jira_env, capsys):
        """Test get_issue handles parent fetch failure gracefully."""
        jira.set_jira_value("issue_key", "DFLY-5678")

        mock_module = MagicMock()

        mock_subtask_response = MagicMock()
        mock_subtask_response.json.return_value = {
            "key": "DFLY-5678",
            "fields": {
                "summary": "Subtask",
                "description": "Desc",
                "issuetype": {"name": "Sub-task", "subtask": True},
                "labels": [],
                "comment": {"comments": []},
                "parent": {"key": "DFLY-1234"},
            },
        }
        mock_subtask_response.raise_for_status = MagicMock()

        # Parent fetch fails
        mock_parent_response = MagicMock()
        mock_parent_response.raise_for_status.side_effect = Exception("Parent not found")

        mock_links_response = MagicMock()
        mock_links_response.json.return_value = []
        mock_links_response.raise_for_status = MagicMock()

        mock_module.get.side_effect = [mock_subtask_response, mock_parent_response, mock_links_response]

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        # Should still complete without crashing
        assert "DFLY-5678" in captured.out
        assert "Subtask" in captured.out

    def test_get_issue_subtask_missing_parent_key(self, temp_state_dir, clear_state_before, mock_jira_env, capsys):
        """Test get_issue handles subtask with missing parent key field."""
        jira.set_jira_value("issue_key", "DFLY-5678")

        mock_module = MagicMock()

        mock_subtask_response = MagicMock()
        mock_subtask_response.json.return_value = {
            "key": "DFLY-5678",
            "fields": {
                "summary": "Orphan Subtask",
                "description": "Desc",
                "issuetype": {"name": "Sub-task", "subtask": True},
                "labels": [],
                "comment": {"comments": []},
                "parent": {},  # Missing key
            },
        }
        mock_subtask_response.raise_for_status = MagicMock()

        mock_links_response = MagicMock()
        mock_links_response.json.return_value = []
        mock_links_response.raise_for_status = MagicMock()

        mock_module.get.side_effect = [mock_subtask_response, mock_links_response]

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        # Should complete without attempting parent fetch
        assert "DFLY-5678" in captured.out
        assert "Detected subtask" not in captured.out


class TestFetchParentIssue:
    """Tests for _fetch_parent_issue helper function."""

    def test_fetch_parent_issue_success(self, mock_jira_env):
        """Test _fetch_parent_issue returns parent data on success."""
        mock_module = MagicMock()
        mock_response = MagicMock()
        parent_data = {
            "key": "DFLY-1234",
            "fields": {"summary": "Parent Issue"},
        }
        mock_response.json.return_value = parent_data
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        result = get_commands._fetch_parent_issue(
            mock_module, "https://jira.example.com", "DFLY-1234", {"Authorization": "Basic xxx"}
        )

        assert result == parent_data

    def test_fetch_parent_issue_returns_none_on_error(self, mock_jira_env, capsys):
        """Test _fetch_parent_issue returns None on API error."""
        mock_module = MagicMock()
        mock_module.get.side_effect = Exception("Network error")

        result = get_commands._fetch_parent_issue(
            mock_module, "https://jira.example.com", "DFLY-1234", {"Authorization": "Basic xxx"}
        )

        assert result is None
        captured = capsys.readouterr()
        assert "Warning: Could not fetch parent issue DFLY-1234" in captured.err


class TestFetchEpic:
    """Tests for _fetch_epic helper function."""

    def test_fetch_epic_success(self, mock_jira_env):
        """Test _fetch_epic returns epic data on success."""
        mock_module = MagicMock()
        mock_response = MagicMock()
        epic_data = {
            "key": "DFLY-100",
            "fields": {"summary": "Epic for Testing", "issuetype": {"name": "Epic"}},
        }
        mock_response.json.return_value = epic_data
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        result = get_commands._fetch_epic(
            mock_module, "https://jira.example.com", "DFLY-100", {"Authorization": "Basic xxx"}
        )

        assert result == epic_data
        mock_module.get.assert_called_once()
        call_url = mock_module.get.call_args[0][0]
        assert "DFLY-100" in call_url
        assert "customfield_10008" in call_url

    def test_fetch_epic_returns_none_on_error(self, mock_jira_env, capsys):
        """Test _fetch_epic returns None on API error."""
        mock_module = MagicMock()
        mock_module.get.side_effect = Exception("Network error")

        result = get_commands._fetch_epic(
            mock_module, "https://jira.example.com", "DFLY-100", {"Authorization": "Basic xxx"}
        )

        assert result is None
        captured = capsys.readouterr()
        assert "Warning: Could not fetch epic DFLY-100" in captured.err


class TestGetIssueEpicDetection:
    """Tests for automatic epic link detection in get_issue."""

    def test_get_issue_fetches_epic_when_linked(self, temp_state_dir, mock_jira_env, capsys, clear_state_before):
        """Test that get_issue fetches epic when customfield_10008 is populated."""
        state.set_value("jira.issue_key", "DFLY-2000")

        # Main issue with epic link
        issue_data = {
            "key": "DFLY-2000",
            "fields": {
                "summary": "Story with Epic",
                "description": "Description",
                "issuetype": {"name": "Story", "subtask": False},
                "customfield_10008": "DFLY-100",
                "labels": [],
            },
        }

        # Epic data
        epic_data = {
            "key": "DFLY-100",
            "fields": {
                "summary": "Parent Epic",
                "issuetype": {"name": "Epic"},
            },
        }

        mock_module = MagicMock()
        call_count = [0]

        def mock_get(url, **kwargs):
            response = MagicMock()
            response.raise_for_status = MagicMock()
            call_count[0] += 1
            if "DFLY-2000" in url:
                response.json.return_value = issue_data
            elif "DFLY-100" in url:
                response.json.return_value = epic_data
            else:
                response.json.return_value = []  # remote links
            return response

        mock_module.get.side_effect = mock_get

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        assert "Detected epic link DFLY-100, fetching epic" in captured.out
        assert "Epic details saved to" in captured.out
        assert "Epic: DFLY-100 - Parent Epic" in captured.out

        # Verify epic file was saved
        epic_file = temp_state_dir / "temp-get-epic-details-response.json"
        assert epic_file.exists()
        epic_content = json.loads(epic_file.read_text())
        assert epic_content["key"] == "DFLY-100"

        # Verify state has metadata reference (not full JSON)
        epic_details = state.get_value("jira.epic_details")
        assert epic_details is not None
        assert epic_details["key"] == "DFLY-100"
        assert "location" in epic_details
        assert "retrievalTimestamp" in epic_details

    def test_get_issue_skips_epic_fetch_for_subtasks(self, temp_state_dir, mock_jira_env, capsys, clear_state_before):
        """Test that get_issue does NOT fetch epic for subtasks (they use parent hierarchy)."""
        state.set_value("jira.issue_key", "DFLY-3000")

        # Subtask with epic link (edge case - should not fetch epic)
        issue_data = {
            "key": "DFLY-3000",
            "fields": {
                "summary": "Subtask with Epic Link",
                "description": "Description",
                "issuetype": {"name": "Sub-task", "subtask": True},
                "parent": {"key": "DFLY-2000"},
                "customfield_10008": "DFLY-100",
                "labels": [],
            },
        }

        parent_data = {
            "key": "DFLY-2000",
            "fields": {"summary": "Parent Story", "issuetype": {"name": "Story"}},
        }

        mock_module = MagicMock()

        def mock_get(url, **kwargs):
            response = MagicMock()
            response.raise_for_status = MagicMock()
            if "DFLY-3000" in url:
                response.json.return_value = issue_data
            elif "DFLY-2000" in url:
                response.json.return_value = parent_data
            else:
                response.json.return_value = []
            return response

        mock_module.get.side_effect = mock_get

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        # Should fetch parent, not epic
        assert "Detected subtask of DFLY-2000" in captured.out
        assert "Detected epic link" not in captured.out

    def test_get_issue_skips_epic_fetch_for_epics(self, temp_state_dir, mock_jira_env, capsys, clear_state_before):
        """Test that get_issue does NOT fetch epic for issues that ARE epics."""
        state.set_value("jira.issue_key", "DFLY-100")

        # Epic issue
        issue_data = {
            "key": "DFLY-100",
            "fields": {
                "summary": "This is an Epic",
                "description": "Epic description",
                "issuetype": {"name": "Epic", "subtask": False},
                "customfield_10008": None,  # Epics don't have epic links
                "labels": [],
            },
        }

        mock_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = issue_data
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        assert "Issue Type: Epic" in captured.out
        assert "Detected epic link" not in captured.out

    def test_get_issue_handles_epic_fetch_failure(self, temp_state_dir, mock_jira_env, capsys, clear_state_before):
        """Test that get_issue continues gracefully when epic fetch fails."""
        state.set_value("jira.issue_key", "DFLY-4000")

        issue_data = {
            "key": "DFLY-4000",
            "fields": {
                "summary": "Story with Bad Epic Link",
                "description": "Description",
                "issuetype": {"name": "Story", "subtask": False},
                "customfield_10008": "DFLY-NOTEXIST",
                "labels": [],
            },
        }

        mock_module = MagicMock()

        def mock_get(url, **kwargs):
            response = MagicMock()
            response.raise_for_status = MagicMock()
            if "DFLY-4000" in url:
                response.json.return_value = issue_data
            elif "DFLY-NOTEXIST" in url:
                raise Exception("404 Not Found")
            else:
                response.json.return_value = []
            return response

        mock_module.get.side_effect = mock_get

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        captured = capsys.readouterr()
        assert "Detected epic link DFLY-NOTEXIST, fetching epic" in captured.out
        # Should show epic fetch failed notice
        assert "Epic: DFLY-NOTEXIST (fetch failed)" in captured.out


class TestGetIssueMetadataReferences:
    """Tests for metadata reference storage (not full JSON in state)."""

    def test_get_issue_stores_issue_metadata_not_full_json(
        self, temp_state_dir, mock_jira_env, capsys, clear_state_before
    ):
        """Test that get_issue stores metadata reference, not full issue JSON."""
        state.set_value("jira.issue_key", "DFLY-5000")

        issue_data = {
            "key": "DFLY-5000",
            "fields": {
                "summary": "Test Issue",
                "description": "Large description that should not be in state",
                "issuetype": {"name": "Task", "subtask": False},
                "labels": [],
            },
        }

        mock_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = issue_data
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        # Verify state has metadata reference
        issue_details = state.get_value("jira.issue_details")
        assert issue_details is not None
        assert "location" in issue_details
        assert "retrievalTimestamp" in issue_details
        # Ensure full JSON is NOT stored
        assert "fields" not in issue_details
        assert "summary" not in issue_details

        # Verify old "last_issue" key is NOT set
        last_issue = state.get_value("jira.last_issue")
        assert last_issue is None

    def test_get_issue_stores_parent_metadata_not_full_json(
        self, temp_state_dir, mock_jira_env, capsys, clear_state_before
    ):
        """Test that get_issue stores parent metadata reference, not full JSON."""
        state.set_value("jira.issue_key", "DFLY-6000")

        # Subtask
        issue_data = {
            "key": "DFLY-6000",
            "fields": {
                "summary": "Subtask",
                "description": "Subtask desc",
                "issuetype": {"name": "Sub-task", "subtask": True},
                "parent": {"key": "DFLY-5000"},
                "labels": [],
            },
        }

        parent_data = {
            "key": "DFLY-5000",
            "fields": {
                "summary": "Parent Issue with lots of data",
                "description": "This should not be in state either",
            },
        }

        mock_module = MagicMock()

        def mock_get(url, **kwargs):
            response = MagicMock()
            response.raise_for_status = MagicMock()
            if "DFLY-6000" in url:
                response.json.return_value = issue_data
            elif "DFLY-5000" in url:
                response.json.return_value = parent_data
            else:
                response.json.return_value = []
            return response

        mock_module.get.side_effect = mock_get

        with patch.object(get_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                jira.get_issue()

        # Verify parent metadata reference
        parent_details = state.get_value("jira.parent_issue_details")
        assert parent_details is not None
        assert parent_details["key"] == "DFLY-5000"
        assert "location" in parent_details
        assert "retrievalTimestamp" in parent_details
        # Ensure full JSON is NOT stored
        assert "fields" not in parent_details
        assert "summary" not in parent_details

        # Verify old parent_issue_key is NOT set (replaced by parent_issue_details)
        old_parent_key = state.get_value("jira.parent_issue_key")
        assert old_parent_key is None


class TestCreateIssueSyncEdgeCases:
    """Edge case tests for create_issue_sync."""

    def test_create_issue_sync_no_epic_name_for_epic(self, mock_jira_env, mock_requests_module):
        """Test creating Epic without epic_name doesn't add field."""
        jira.create_issue_sync(
            project_key="DFLY",
            summary="Test Epic",
            issue_type="Epic",
            description="Epic description",
            labels=[],
            epic_name=None,
        )

        call_args = mock_requests_module.post.call_args
        payload = call_args[1]["json"]
        assert jira.EPIC_NAME_FIELD not in payload["fields"]

    def test_create_issue_sync_no_parent_for_task(self, mock_jira_env, mock_requests_module):
        """Test creating Task with parent_key doesn't add parent field."""
        jira.create_issue_sync(
            project_key="DFLY",
            summary="Test Task",
            issue_type="Task",
            description="Task description",
            labels=[],
            parent_key="DFLY-1234",  # Should be ignored for non-subtask
        )

        call_args = mock_requests_module.post.call_args
        payload = call_args[1]["json"]
        assert "parent" not in payload["fields"]
