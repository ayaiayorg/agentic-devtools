"""
Tests for Jira update_commands module.

Tests for dfly-update-jira-issue command and payload building.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from agdt_ai_helpers.cli.jira.update_commands import update_issue


class TestUpdateIssue:
    """Tests for update_issue command."""

    @pytest.fixture
    def mock_state_dir(self, tmp_path):
        """Mock the state directory."""
        with patch("agdt_ai_helpers.state.get_state_dir", return_value=tmp_path):
            yield tmp_path

    def test_requires_issue_key(self, mock_state_dir):
        """Test update_issue exits if no issue_key provided."""
        with patch(
            "agdt_ai_helpers.cli.jira.update_commands.get_jira_value",
            return_value=None,
        ):
            with pytest.raises(SystemExit) as exc_info:
                update_issue()
            assert exc_info.value.code == 1

    def test_requires_at_least_one_field(self, mock_state_dir):
        """Test update_issue exits if no fields to update."""
        with patch(
            "agdt_ai_helpers.cli.jira.update_commands.get_jira_value",
            side_effect=lambda k: "DFLY-123" if k == "issue_key" else None,
        ):
            with pytest.raises(SystemExit) as exc_info:
                update_issue()
            assert exc_info.value.code == 1

    def test_dry_run_mode(self, mock_state_dir, capsys):
        """Test dry run mode shows what would be updated."""
        with patch(
            "agdt_ai_helpers.cli.jira.update_commands.get_jira_value",
            side_effect=lambda k: {
                "issue_key": "DFLY-123",
                "summary": "New Summary",
                "dry_run": "true",
            }.get(k),
        ):
            with patch(
                "agdt_ai_helpers.cli.jira.update_commands.is_dry_run",
                return_value=True,
            ):
                update_issue()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "DFLY-123" in captured.out

    def test_successful_update(self, mock_state_dir, capsys):
        """Test successful issue update."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status = MagicMock()

        with patch(
            "agdt_ai_helpers.cli.jira.update_commands.get_jira_value",
            side_effect=lambda k: {
                "issue_key": "DFLY-123",
                "summary": "Updated Summary",
            }.get(k),
        ):
            with patch(
                "agdt_ai_helpers.cli.jira.update_commands.is_dry_run",
                return_value=False,
            ):
                with patch("agdt_ai_helpers.cli.jira.update_commands._get_requests") as mock_requests:
                    mock_requests.return_value.put.return_value = mock_response
                    with patch(
                        "agdt_ai_helpers.cli.jira.update_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch(
                            "agdt_ai_helpers.cli.jira.update_commands.get_jira_headers",
                            return_value={},
                        ):
                            with patch("agdt_ai_helpers.cli.jira.get_commands.get_issue"):
                                update_issue()

        captured = capsys.readouterr()
        assert "updated successfully" in captured.out

    def test_parses_labels_from_comma_separated(self, mock_state_dir, capsys):
        """Test labels are parsed from comma-separated string."""
        with patch(
            "agdt_ai_helpers.cli.jira.update_commands.get_jira_value",
            side_effect=lambda k: {
                "issue_key": "DFLY-123",
                "labels": "label1,label2,label3",
            }.get(k),
        ):
            with patch(
                "agdt_ai_helpers.cli.jira.update_commands.is_dry_run",
                return_value=True,
            ):
                update_issue()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        # Labels should be parsed into list
        assert "label1" in captured.out

    def test_parses_custom_fields_json(self, mock_state_dir, capsys):
        """Test custom fields are parsed from JSON string."""
        custom_json = json.dumps({"customfield_10001": "value"})
        with patch(
            "agdt_ai_helpers.cli.jira.update_commands.get_jira_value",
            side_effect=lambda k: {
                "issue_key": "DFLY-123",
                "custom_fields": custom_json,
            }.get(k),
        ):
            with patch(
                "agdt_ai_helpers.cli.jira.update_commands.is_dry_run",
                return_value=True,
            ):
                update_issue()

        captured = capsys.readouterr()
        assert "customfield_10001" in captured.out

    def test_invalid_custom_fields_json(self, mock_state_dir):
        """Test invalid JSON in custom_fields causes exit."""
        with patch(
            "agdt_ai_helpers.cli.jira.update_commands.get_jira_value",
            side_effect=lambda k: {
                "issue_key": "DFLY-123",
                "custom_fields": "not valid json",
            }.get(k),
        ):
            with pytest.raises(SystemExit) as exc_info:
                update_issue()
            assert exc_info.value.code == 1

    def test_custom_fields_must_be_object(self, mock_state_dir):
        """Test custom_fields must be a JSON object, not array."""
        with patch(
            "agdt_ai_helpers.cli.jira.update_commands.get_jira_value",
            side_effect=lambda k: {
                "issue_key": "DFLY-123",
                "custom_fields": '["not", "an", "object"]',
            }.get(k),
        ):
            with pytest.raises(SystemExit) as exc_info:
                update_issue()
            assert exc_info.value.code == 1

