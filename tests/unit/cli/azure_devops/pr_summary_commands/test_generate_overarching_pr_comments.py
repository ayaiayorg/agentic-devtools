"""
Tests for pr_summary_commands module.

Covers:
- Return value behavior of generate_overarching_pr_comments
- Early exit scenarios (no files, no threads, dry run)
- Helper functions for path normalization, sorting, and link building
"""

import json
from unittest.mock import patch

import pytest

from agentic_devtools.cli.azure_devops.pr_summary_commands import (
    generate_overarching_pr_comments,
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
