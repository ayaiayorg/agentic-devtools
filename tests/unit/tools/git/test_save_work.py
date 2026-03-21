"""Tests for agentic_devtools.tools.git.save_work."""

from unittest.mock import patch

from agentic_devtools.tools.git import save_work


class TestSaveWork:
    """Tests for the save_work composite tool function."""

    @patch("agentic_devtools.tools.git.push")
    @patch("agentic_devtools.tools.git.create_commit")
    @patch("agentic_devtools.tools.git.stage_changes")
    def test_full_workflow(self, mock_stage, mock_commit, mock_push):
        mock_stage.return_value = {"success": True, "message": "Staged"}
        mock_commit.return_value = {"success": True, "message": "Committed"}
        mock_push.return_value = {"success": True, "message": "Pushed"}

        result = save_work(commit_message="feat: test")

        assert result["success"] is True
        assert result["operations"] == ["stage_changes", "create_commit", "push"]
        mock_stage.assert_called_once_with(dry_run=False)
        mock_commit.assert_called_once_with("feat: test", dry_run=False)
        mock_push.assert_called_once_with(dry_run=False)

    @patch("agentic_devtools.tools.git.force_push")
    @patch("agentic_devtools.tools.git.amend_commit")
    @patch("agentic_devtools.tools.git.stage_changes")
    def test_amend_workflow(self, mock_stage, mock_amend, mock_force_push):
        mock_stage.return_value = {"success": True, "message": "Staged"}
        mock_amend.return_value = {"success": True, "message": "Amended"}
        mock_force_push.return_value = {"success": True, "message": "Force pushed"}

        result = save_work(commit_message="feat: update", amend=True)

        assert result["success"] is True
        assert result["operations"] == ["stage_changes", "amend_commit", "force_push"]

    @patch("agentic_devtools.tools.git.push")
    @patch("agentic_devtools.tools.git.create_commit")
    def test_skip_stage(self, mock_commit, mock_push):
        mock_commit.return_value = {"success": True, "message": "Committed"}
        mock_push.return_value = {"success": True, "message": "Pushed"}

        result = save_work(commit_message="feat: test", skip_stage=True)

        assert result["success"] is True
        assert "stage_changes" not in result["operations"]

    @patch("agentic_devtools.tools.git.create_commit")
    @patch("agentic_devtools.tools.git.stage_changes")
    def test_skip_push(self, mock_stage, mock_commit):
        mock_stage.return_value = {"success": True, "message": "Staged"}
        mock_commit.return_value = {"success": True, "message": "Committed"}

        result = save_work(commit_message="feat: test", skip_push=True)

        assert result["success"] is True
        assert "push" not in result["operations"]
        assert "force_push" not in result["operations"]

    @patch("agentic_devtools.tools.git.stage_changes")
    def test_fails_on_stage_error(self, mock_stage):
        mock_stage.return_value = {"success": False, "message": "Stage failed"}

        result = save_work(commit_message="feat: test")

        assert result["success"] is False
        assert result["operations"] == ["stage_changes"]

    @patch("agentic_devtools.tools.git.create_commit")
    @patch("agentic_devtools.tools.git.stage_changes")
    def test_fails_on_commit_error(self, mock_stage, mock_commit):
        mock_stage.return_value = {"success": True, "message": "Staged"}
        mock_commit.return_value = {"success": False, "message": "Commit failed"}

        result = save_work(commit_message="feat: test")

        assert result["success"] is False
        assert result["operations"] == ["stage_changes", "create_commit"]

    @patch("agentic_devtools.tools.git.push")
    @patch("agentic_devtools.tools.git.create_commit")
    @patch("agentic_devtools.tools.git.stage_changes")
    def test_fails_on_push_error(self, mock_stage, mock_commit, mock_push):
        mock_stage.return_value = {"success": True, "message": "Staged"}
        mock_commit.return_value = {"success": True, "message": "Committed"}
        mock_push.return_value = {"success": False, "message": "Push failed"}

        result = save_work(commit_message="feat: test")

        assert result["success"] is False
        assert "push" in result["operations"]

    @patch("agentic_devtools.tools.git.push")
    @patch("agentic_devtools.tools.git.create_commit")
    @patch("agentic_devtools.tools.git.stage_changes")
    def test_dry_run_threads_through(self, mock_stage, mock_commit, mock_push):
        """Verify that dry_run=True is passed to all sub-operations."""
        mock_stage.return_value = {"success": True, "message": "Staged (dry)"}
        mock_commit.return_value = {"success": True, "message": "Committed (dry)"}
        mock_push.return_value = {"success": True, "message": "Pushed (dry)"}

        result = save_work(commit_message="feat: test", dry_run=True)

        assert result["success"] is True
        mock_stage.assert_called_once_with(dry_run=True)
        mock_commit.assert_called_once_with("feat: test", dry_run=True)
        mock_push.assert_called_once_with(dry_run=True)

    @patch("agentic_devtools.tools.git.force_push")
    @patch("agentic_devtools.tools.git.amend_commit")
    @patch("agentic_devtools.tools.git.stage_changes")
    def test_dry_run_threads_through_amend(self, mock_stage, mock_amend, mock_force_push):
        """Verify that dry_run=True is passed through amend + force-push path."""
        mock_stage.return_value = {"success": True, "message": "Staged (dry)"}
        mock_amend.return_value = {"success": True, "message": "Amended (dry)"}
        mock_force_push.return_value = {"success": True, "message": "Force pushed (dry)"}

        result = save_work(commit_message="feat: update", amend=True, dry_run=True)

        assert result["success"] is True
        mock_stage.assert_called_once_with(dry_run=True)
        mock_amend.assert_called_once_with("feat: update", dry_run=True)
        mock_force_push.assert_called_once_with(dry_run=True)
