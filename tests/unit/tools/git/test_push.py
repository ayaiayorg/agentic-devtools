"""Tests for agentic_devtools.tools.git.push."""

from unittest.mock import patch

from agentic_devtools.tools.git import push


class TestPush:
    """Tests for the push tool function."""

    @patch("agentic_devtools.tools.git._capture")
    def test_returns_success_result(self, mock_capture):
        mock_capture.return_value = "Changes pushed successfully."

        result = push(dry_run=False)

        assert result["success"] is True
        assert "pushed" in result["message"].lower()

    @patch("agentic_devtools.cli.git.operations.push", side_effect=SystemExit(1))
    def test_returns_failure_on_system_exit(self, _mock):
        result = push(dry_run=False)

        assert result["success"] is False
