"""Tests for _get_queue_path function."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.azure_devops.file_review_commands import _get_queue_path


class TestGetQueuePath:
    """Tests for _get_queue_path function."""

    def test_returns_expected_path_layout(self, tmp_path):
        """Should return <state_dir>/pull-request-review/prompts/<pr_id>/queue.json."""
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_state_dir",
            return_value=tmp_path,
        ):
            result = _get_queue_path(25524)

        expected = tmp_path / "pull-request-review" / "prompts" / "25524" / "queue.json"
        assert result == expected

    def test_uses_get_state_dir_not_file_traversal(self, tmp_path):
        """Should derive path from get_state_dir(), not Path(__file__) traversal."""
        fake_state_dir = tmp_path / "custom" / "state"
        fake_state_dir.mkdir(parents=True)

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_state_dir",
            return_value=fake_state_dir,
        ):
            result = _get_queue_path(12345)

        assert result == fake_state_dir / "pull-request-review" / "prompts" / "12345" / "queue.json"
        assert "site-packages" not in str(result)

    def test_pr_id_is_stringified_in_path(self, tmp_path):
        """Should convert pull_request_id to string for path segment."""
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_state_dir",
            return_value=tmp_path,
        ):
            result = _get_queue_path(99999)

        assert "99999" in str(result)
        assert isinstance(result, Path)
