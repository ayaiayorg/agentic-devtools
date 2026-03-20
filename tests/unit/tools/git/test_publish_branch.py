"""Tests for agentic_devtools.tools.git.publish_branch."""

from unittest.mock import patch

from agentic_devtools.tools.git import publish_branch


class TestPublishBranch:
    """Tests for the publish_branch tool function."""

    @patch("agentic_devtools.tools.git._capture")
    def test_returns_success_result(self, mock_capture):
        mock_capture.return_value = "Branch published successfully."

        result = publish_branch(dry_run=False)

        assert result["success"] is True
        assert "published" in result["message"].lower()

    @patch("agentic_devtools.cli.git.operations.publish_branch", side_effect=SystemExit(1))
    def test_returns_failure_on_system_exit(self, _mock):
        result = publish_branch(dry_run=False)

        assert result["success"] is False
