"""Tests for agentic_devtools.tools.git.create_commit."""

from unittest.mock import patch

from agentic_devtools.tools.git import create_commit


class TestCreateCommit:
    """Tests for the create_commit tool function."""

    @patch("agentic_devtools.tools.git._capture")
    def test_returns_success_result(self, mock_capture):
        mock_capture.return_value = "Commit created successfully."

        result = create_commit("feat: add feature", dry_run=False)

        assert result["success"] is True
        assert "Commit created" in result["message"]

    @patch("agentic_devtools.tools.git._capture")
    def test_dry_run(self, mock_capture):
        mock_capture.return_value = "[DRY RUN] Would create commit"

        result = create_commit("feat: test", dry_run=True)

        assert result["success"] is True

    @patch("agentic_devtools.cli.git.operations.create_commit", side_effect=SystemExit(1))
    def test_returns_failure_on_system_exit(self, _mock):
        result = create_commit("msg", dry_run=False)

        assert result["success"] is False
