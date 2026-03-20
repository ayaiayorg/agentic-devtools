"""Tests for agentic_devtools.tools.git.force_push."""

from unittest.mock import patch

from agentic_devtools.tools.git import force_push


class TestForcePush:
    """Tests for the force_push tool function."""

    @patch("agentic_devtools.tools.git._capture")
    def test_returns_success_result(self, mock_capture):
        mock_capture.return_value = "Changes pushed successfully."

        result = force_push(dry_run=False)

        assert result["success"] is True

    @patch("agentic_devtools.cli.git.operations.force_push", side_effect=SystemExit(1))
    def test_returns_failure_on_system_exit(self, _mock):
        result = force_push(dry_run=False)

        assert result["success"] is False
