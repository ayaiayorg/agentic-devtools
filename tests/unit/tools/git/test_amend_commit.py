"""Tests for agentic_devtools.tools.git.amend_commit."""

from unittest.mock import patch

from agentic_devtools.tools.git import amend_commit


class TestAmendCommit:
    """Tests for the amend_commit tool function."""

    @patch("agentic_devtools.tools.git._capture")
    def test_returns_success_result(self, mock_capture):
        mock_capture.return_value = "Commit amended successfully."

        result = amend_commit("feat: update feature", dry_run=False)

        assert result["success"] is True
        assert "amended" in result["message"].lower()

    @patch("agentic_devtools.cli.git.operations.amend_commit", side_effect=SystemExit(1))
    def test_returns_failure_on_system_exit(self, _mock):
        result = amend_commit("msg", dry_run=False)

        assert result["success"] is False
