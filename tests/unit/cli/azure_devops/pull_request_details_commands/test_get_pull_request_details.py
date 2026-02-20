"""Tests for get_pull_request_details function."""
import json
from unittest.mock import MagicMock, patch

import pytest

from agdt_ai_helpers.cli.azure_devops import get_pull_request_details


class TestGetPullRequestDetails:
    """Tests for get_pull_request_details command."""

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Should show dry run output when dry_run is set."""
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "23046")
        set_value("dry_run", "true")

        get_pull_request_details()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "23046" in captured.out
        assert "Organization" in captured.out
        assert "Project" in captured.out
        assert "Repository" in captured.out

    def test_dry_run_shows_output_path(self, temp_state_dir, clear_state_before, capsys):
        """Should show output file path in dry run."""
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "12345")
        set_value("dry_run", "true")

        get_pull_request_details()

        captured = capsys.readouterr()
        assert "Output" in captured.out
        assert "temp-get-pull-request-details-response.json" in captured.out

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before, capsys):
        """Should raise KeyError if pull_request_id is not set."""
        from agdt_ai_helpers.state import set_value

        set_value("dry_run", "true")  # Don't set pull_request_id

        with pytest.raises(KeyError, match="pull_request_id"):
            get_pull_request_details()

class TestGetPullRequestDetailsExecution:
    """Tests for get_pull_request_details when not in dry-run mode."""

    def test_exits_on_az_cli_failure(self, temp_state_dir, clear_state_before, capsys):
        """Should exit with error when az CLI command fails."""
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "12345")
        set_value("dry_run", "false")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Failed to find PR"

        with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.verify_az_cli"), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pat",
            return_value="fake-pat",
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.run_safe",
            return_value=mock_result,
        ):
            with pytest.raises(SystemExit) as exc_info:
                get_pull_request_details()

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error" in captured.err
        assert "Failed to get pull request details" in captured.err

    def test_exits_on_invalid_json_response(self, temp_state_dir, clear_state_before, capsys):
        """Should exit with error when az CLI returns invalid JSON."""
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "12345")
        set_value("dry_run", "false")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json {{"

        with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.verify_az_cli"), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pat",
            return_value="fake-pat",
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.run_safe",
            return_value=mock_result,
        ):
            with pytest.raises(SystemExit) as exc_info:
                get_pull_request_details()

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error" in captured.err
        assert "Failed to parse" in captured.err

    def test_successful_execution(self, temp_state_dir, clear_state_before, tmp_path, capsys):
        """Should successfully retrieve and save PR details."""
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "12345")
        set_value("dry_run", "false")

        # Mock PR data
        pr_data = {
            "pullRequestId": 12345,
            "title": "Test PR",
            "isDraft": False,
            "status": "active",
            "autoCompleteSetBy": None,
            "targetRefName": "refs/heads/main",
            "sourceRefName": "refs/heads/feature",
            "lastMergeTargetCommit": {"commitId": "abc123"},
            "lastMergeSourceCommit": {"commitId": "def456"},
            "repository": {
                "id": "repo-id-123",
                "project": {"id": "project-id-123"},
            },
        }

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(pr_data)

        with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.verify_az_cli"), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pat",
            return_value="fake-pat",
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.run_safe",
            return_value=mock_result,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_auth_headers",
            return_value={"Authorization": "Basic xxx"},
        ), patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.sync_git_ref"), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_diff_entries",
            return_value=[],
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_pull_request_threads",
            return_value=[],
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_pull_request_iterations",
            return_value=[{"id": 1}],
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_reviewer_payload",
            return_value={"reviewedFiles": []},
        ), patch("pathlib.Path.mkdir"), patch("builtins.open", MagicMock()):
            get_pull_request_details()

        captured = capsys.readouterr()
        assert "12345" in captured.out
        assert "Test PR" in captured.out
        assert "Pull request details retrieved successfully" in captured.out

    def test_handles_auto_complete_set_by(self, temp_state_dir, clear_state_before, capsys):
        """Should display auto-complete info when set."""
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "12345")
        set_value("dry_run", "false")

        pr_data = {
            "pullRequestId": 12345,
            "title": "Test PR",
            "isDraft": False,
            "status": "active",
            "autoCompleteSetBy": {"displayName": "John Doe"},
            "targetRefName": "refs/heads/main",
            "sourceRefName": "refs/heads/feature",
            "repository": {"id": "repo-id", "project": {"id": "project-id"}},
        }

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(pr_data)

        with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.verify_az_cli"), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pat",
            return_value="fake-pat",
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.run_safe",
            return_value=mock_result,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_auth_headers",
            return_value={},
        ), patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.sync_git_ref"), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_diff_entries",
            return_value=[],
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_pull_request_threads",
            return_value=None,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_pull_request_iterations",
            return_value=None,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_reviewer_payload",
            return_value=None,
        ), patch("pathlib.Path.mkdir"), patch("builtins.open", MagicMock()):
            get_pull_request_details()

        captured = capsys.readouterr()
        assert "Auto-Complete" in captured.out
        assert "John Doe" in captured.out

    def test_handles_org_without_https(self, temp_state_dir, clear_state_before):
        """Should prepend https://dev.azure.com/ when org doesn't start with http."""
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "12345")
        set_value("dry_run", "false")
        set_value("ado.organization", "my-org")  # No http prefix

        pr_data = {
            "pullRequestId": 12345,
            "title": "Test PR",
            "targetRefName": "refs/heads/main",
            "sourceRefName": "refs/heads/feature",
            "repository": {"id": "repo-id", "project": {"id": "project-id"}},
        }

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(pr_data)

        captured_args = []

        def capture_run_safe(args, **kwargs):
            captured_args.append(args)
            return mock_result

        with patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.verify_az_cli"), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_pat",
            return_value="fake-pat",
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.run_safe",
            side_effect=capture_run_safe,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_auth_headers",
            return_value={},
        ), patch("agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.sync_git_ref"), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands.get_diff_entries",
            return_value=[],
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_pull_request_threads",
            return_value=None,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_pull_request_iterations",
            return_value=None,
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.pull_request_details_commands._get_reviewer_payload",
            return_value=None,
        ), patch("pathlib.Path.mkdir"), patch("builtins.open", MagicMock()):
            get_pull_request_details()

        # Check that the org was prefixed with https
        assert len(captured_args) > 0
        org_index = captured_args[0].index("--organization") + 1
        assert captured_args[0][org_index].startswith("https://dev.azure.com/")
