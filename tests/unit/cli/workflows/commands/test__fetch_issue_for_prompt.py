"""Tests for _fetch_issue_for_prompt helper function."""

import json
from unittest.mock import patch

import pytest

from agentic_devtools.cli.workflows import commands


@pytest.fixture
def _sample_issue_json():
    """Return a sample Jira issue JSON fixture."""
    return {
        "key": "PROJECT-1234",
        "fields": {
            "summary": "Implement webhook support",
            "issuetype": {"name": "Story"},
            "labels": ["backend", "api"],
            "description": "As a user I want webhook notifications.",
            "comment": {
                "comments": [
                    {
                        "author": {"displayName": "Alice"},
                        "body": "Initial implementation plan posted.",
                    },
                    {
                        "author": {"displayName": "Bob"},
                        "body": "LGTM, let's proceed.",
                    },
                ]
            },
        },
    }


class TestFetchIssueForPromptSuccess:
    """Tests for successful pre-fetch scenarios."""

    def test_extracts_all_fields_correctly(self, temp_state_dir, _sample_issue_json):
        """Verify all 5 output keys are correctly populated from sample JSON."""
        issue_file = temp_state_dir / "temp-get-issue-details-response.json"
        issue_file.write_text(json.dumps(_sample_issue_json), encoding="utf-8")

        with patch("agentic_devtools.cli.workflows.commands.get_state_dir", return_value=temp_state_dir):
            with patch("agentic_devtools.cli.jira.get_commands.get_issue"):
                with patch("agentic_devtools.cli.jira.state_helpers.set_jira_value"):
                    result = commands._fetch_issue_for_prompt("PROJECT-1234")

        assert result["jira_issue_summary"] == "Implement webhook support"
        assert result["jira_issue_type"] == "Story"
        assert result["jira_issue_labels"] == "backend, api"
        assert result["jira_issue_description"] == "As a user I want webhook notifications."
        assert "**Alice**: Initial implementation plan posted...." in result["jira_issue_comments"]
        assert "**Bob**: LGTM, let's proceed...." in result["jira_issue_comments"]

    def test_empty_comments_returns_no_comments(self, temp_state_dir):
        """Verify jira_issue_comments is 'No comments' when there are no comments."""
        issue_data = {
            "fields": {
                "summary": "Test",
                "issuetype": {"name": "Task"},
                "labels": [],
                "description": "Desc",
                "comment": {"comments": []},
            }
        }
        issue_file = temp_state_dir / "temp-get-issue-details-response.json"
        issue_file.write_text(json.dumps(issue_data), encoding="utf-8")

        with patch("agentic_devtools.cli.workflows.commands.get_state_dir", return_value=temp_state_dir):
            with patch("agentic_devtools.cli.jira.get_commands.get_issue"):
                with patch("agentic_devtools.cli.jira.state_helpers.set_jira_value"):
                    result = commands._fetch_issue_for_prompt("PROJECT-1234")

        assert result["jira_issue_comments"] == "No comments"

    def test_empty_labels_returns_none_string(self, temp_state_dir):
        """Verify jira_issue_labels is 'None' when labels list is empty."""
        issue_data = {
            "fields": {
                "summary": "Test",
                "issuetype": {"name": "Bug"},
                "labels": [],
                "description": "Desc",
                "comment": {"comments": []},
            }
        }
        issue_file = temp_state_dir / "temp-get-issue-details-response.json"
        issue_file.write_text(json.dumps(issue_data), encoding="utf-8")

        with patch("agentic_devtools.cli.workflows.commands.get_state_dir", return_value=temp_state_dir):
            with patch("agentic_devtools.cli.jira.get_commands.get_issue"):
                with patch("agentic_devtools.cli.jira.state_helpers.set_jira_value"):
                    result = commands._fetch_issue_for_prompt("PROJECT-1234")

        assert result["jira_issue_labels"] == "None"

    def test_missing_fields_use_defaults(self, temp_state_dir):
        """Verify default values are used when fields are missing."""
        issue_data = {"fields": {}}
        issue_file = temp_state_dir / "temp-get-issue-details-response.json"
        issue_file.write_text(json.dumps(issue_data), encoding="utf-8")

        with patch("agentic_devtools.cli.workflows.commands.get_state_dir", return_value=temp_state_dir):
            with patch("agentic_devtools.cli.jira.get_commands.get_issue"):
                with patch("agentic_devtools.cli.jira.state_helpers.set_jira_value"):
                    result = commands._fetch_issue_for_prompt("PROJECT-1234")

        assert result["jira_issue_summary"] == "No summary available"
        assert result["jira_issue_type"] == "Unknown"
        assert result["jira_issue_labels"] == "None"
        assert result["jira_issue_description"] == "No description available"
        assert result["jira_issue_comments"] == "No comments"

    def test_comments_truncated_to_200_chars(self, temp_state_dir):
        """Verify long comment bodies are truncated to 200 chars."""
        long_body = "x" * 300
        issue_data = {
            "fields": {
                "summary": "Test",
                "issuetype": {"name": "Task"},
                "labels": [],
                "description": "Desc",
                "comment": {
                    "comments": [
                        {"author": {"displayName": "Alice"}, "body": long_body},
                    ]
                },
            }
        }
        issue_file = temp_state_dir / "temp-get-issue-details-response.json"
        issue_file.write_text(json.dumps(issue_data), encoding="utf-8")

        with patch("agentic_devtools.cli.workflows.commands.get_state_dir", return_value=temp_state_dir):
            with patch("agentic_devtools.cli.jira.get_commands.get_issue"):
                with patch("agentic_devtools.cli.jira.state_helpers.set_jira_value"):
                    result = commands._fetch_issue_for_prompt("PROJECT-1234")

        # Body should be truncated at 200 chars + "..." suffix + author prefix
        assert "x" * 200 in result["jira_issue_comments"]
        assert "x" * 201 not in result["jira_issue_comments"]

    def test_only_last_five_comments_included(self, temp_state_dir):
        """Verify only last 5 comments are included."""
        comments = [{"author": {"displayName": f"User{i}"}, "body": f"Comment {i}"} for i in range(8)]
        issue_data = {
            "fields": {
                "summary": "Test",
                "issuetype": {"name": "Task"},
                "labels": [],
                "description": "Desc",
                "comment": {"comments": comments},
            }
        }
        issue_file = temp_state_dir / "temp-get-issue-details-response.json"
        issue_file.write_text(json.dumps(issue_data), encoding="utf-8")

        with patch("agentic_devtools.cli.workflows.commands.get_state_dir", return_value=temp_state_dir):
            with patch("agentic_devtools.cli.jira.get_commands.get_issue"):
                with patch("agentic_devtools.cli.jira.state_helpers.set_jira_value"):
                    result = commands._fetch_issue_for_prompt("PROJECT-1234")

        # Comments 0-2 should NOT be present; comments 3-7 should be present
        assert "User0" not in result["jira_issue_comments"]
        assert "User1" not in result["jira_issue_comments"]
        assert "User2" not in result["jira_issue_comments"]
        assert "User3" in result["jira_issue_comments"]
        assert "User7" in result["jira_issue_comments"]


class TestFetchIssueForPromptFailure:
    """Tests for failure/fallback scenarios."""

    def test_get_issue_raises_system_exit(self, temp_state_dir, capsys):
        """get_issue() calls sys.exit(1) — should return empty dict with warning."""
        with patch("agentic_devtools.cli.workflows.commands.get_state_dir", return_value=temp_state_dir):
            with patch("agentic_devtools.cli.jira.get_commands.get_issue", side_effect=SystemExit(1)):
                with patch("agentic_devtools.cli.jira.state_helpers.set_jira_value"):
                    result = commands._fetch_issue_for_prompt("PROJECT-1234")

        assert result == {}
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "Failed to fetch issue" in captured.err

    def test_get_issue_raises_exception(self, temp_state_dir, capsys):
        """get_issue() raises a generic exception — should return empty dict."""
        with patch("agentic_devtools.cli.workflows.commands.get_state_dir", return_value=temp_state_dir):
            with patch(
                "agentic_devtools.cli.jira.get_commands.get_issue",
                side_effect=ConnectionError("Network unreachable"),
            ):
                with patch("agentic_devtools.cli.jira.state_helpers.set_jira_value"):
                    result = commands._fetch_issue_for_prompt("PROJECT-1234")

        assert result == {}
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "Could not fetch Jira issue" in captured.err

    def test_temp_file_not_found(self, temp_state_dir, capsys):
        """get_issue() succeeds but temp file doesn't exist — should return empty dict."""
        # Don't create the temp file
        with patch("agentic_devtools.cli.workflows.commands.get_state_dir", return_value=temp_state_dir):
            with patch("agentic_devtools.cli.jira.get_commands.get_issue"):
                with patch("agentic_devtools.cli.jira.state_helpers.set_jira_value"):
                    result = commands._fetch_issue_for_prompt("PROJECT-1234")

        assert result == {}
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "not found" in captured.err

    def test_malformed_json(self, temp_state_dir, capsys):
        """Temp file contains malformed JSON — should return empty dict."""
        issue_file = temp_state_dir / "temp-get-issue-details-response.json"
        issue_file.write_text("not-valid-json{{{", encoding="utf-8")

        with patch("agentic_devtools.cli.workflows.commands.get_state_dir", return_value=temp_state_dir):
            with patch("agentic_devtools.cli.jira.get_commands.get_issue"):
                with patch("agentic_devtools.cli.jira.state_helpers.set_jira_value"):
                    result = commands._fetch_issue_for_prompt("PROJECT-1234")

        assert result == {}
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "Could not read issue file" in captured.err
