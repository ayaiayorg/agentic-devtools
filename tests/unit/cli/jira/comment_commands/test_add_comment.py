"""Tests for add_comment CLI command."""

from unittest.mock import MagicMock, patch

import pytest

from agdt_ai_helpers.cli import jira
from agdt_ai_helpers.cli.jira import comment_commands, get_commands


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

    def test_add_comment_with_explicit_params_stores_in_state(
        self, temp_state_dir, clear_state_before, mock_jira_env, mock_requests_module, capsys
    ):
        """Test add_comment stores explicit params in state."""
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {"id": "comment-456"}
        mock_post_response.raise_for_status = MagicMock()
        mock_requests_module.post.return_value = mock_post_response

        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {
            "key": "DFLY-5678",
            "fields": {
                "summary": "Test Issue",
                "description": "Test description",
                "issuetype": {"name": "Task"},
                "labels": [],
                "comment": {"comments": []},
            },
        }
        mock_get_response.raise_for_status = MagicMock()
        mock_requests_module.get.return_value = mock_get_response

        with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
            jira.add_comment(comment="Explicit comment", issue_key="DFLY-5678")

        assert jira.get_jira_value("issue_key") == "DFLY-5678"
        assert jira.get_jira_value("comment") == "Explicit comment"
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
