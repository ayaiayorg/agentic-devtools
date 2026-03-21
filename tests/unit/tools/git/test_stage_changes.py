"""Tests for agentic_devtools.tools.git.stage_changes."""

from unittest.mock import patch

from agentic_devtools.tools.git import stage_changes


class TestStageChanges:
    """Tests for the stage_changes tool function."""

    @patch("agentic_devtools.tools.git._capture")
    def test_returns_success_result(self, mock_capture):
        mock_capture.return_value = "Changes staged."

        result = stage_changes(dry_run=False)

        assert result["success"] is True
        assert "staged" in result["message"].lower()

    @patch("agentic_devtools.tools.git._capture")
    def test_returns_dry_run_message(self, mock_capture):
        mock_capture.return_value = "[DRY RUN] Would stage all changes (git add .)"

        result = stage_changes(dry_run=True)

        assert result["success"] is True
        assert "DRY RUN" in result["message"]

    @patch("agentic_devtools.cli.git.operations.stage_changes", side_effect=SystemExit(1))
    def test_returns_failure_on_system_exit(self, _mock):
        result = stage_changes(dry_run=False)

        assert result["success"] is False

    @patch("agentic_devtools.cli.git.operations.stage_changes", side_effect=RuntimeError("git error"))
    def test_returns_failure_on_exception(self, _mock):
        result = stage_changes(dry_run=False)

        assert result["success"] is False
        assert "git error" in result["message"]
