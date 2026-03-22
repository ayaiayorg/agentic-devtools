"""Tests for _get_queue_path function."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.azure_devops.file_review_commands import _get_queue_path


class TestGetQueuePath:
    """Tests for _get_queue_path function."""

    def test_returns_expected_path_layout(self, tmp_path):
        """Should return <state_dir>/pull-request-review/<commit_hash_short>/queue.json."""
        with (
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_state_dir",
                return_value=tmp_path,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_value",
                side_effect=lambda key, *args, **kwargs: "abc12345" if key == "review.commit_hash_short" else None,
            ),
        ):
            result = _get_queue_path(25524)

        expected = tmp_path / "pull-request-review" / "abc12345" / "queue.json"
        assert result == expected

    def test_uses_get_state_dir_not_file_traversal(self, tmp_path):
        """Should derive path from get_state_dir(), not Path(__file__) traversal."""
        fake_state_dir = tmp_path / "custom" / "state"
        fake_state_dir.mkdir(parents=True)

        with (
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_state_dir",
                return_value=fake_state_dir,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_value",
                side_effect=lambda key, *args, **kwargs: "deadbeef" if key == "review.commit_hash_short" else None,
            ),
        ):
            result = _get_queue_path(12345)

        assert result == fake_state_dir / "pull-request-review" / "deadbeef" / "queue.json"
        assert "site-packages" not in str(result)

    def test_falls_back_to_pr_id_when_no_commit_hash(self, tmp_path, capsys):
        """Should fall back to 'PR<pull_request_id>' when review.commit_hash_short is not set."""
        with (
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_state_dir",
                return_value=tmp_path,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_value",
                return_value=None,
            ),
        ):
            result = _get_queue_path(99999)

        assert result == tmp_path / "pull-request-review" / "PR99999" / "queue.json"
        assert isinstance(result, Path)
        # _get_queue_path passes warn=False to avoid stderr spam on every queue op
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_falls_back_to_pr_id_when_commit_hash_is_unsafe(self, tmp_path, capsys):
        """Should fall back to 'PR<id>' when review.commit_hash_short contains path traversal chars."""
        with (
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_state_dir",
                return_value=tmp_path,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_value",
                side_effect=lambda key, *a, **kw: "../evil" if key == "review.commit_hash_short" else None,
            ),
        ):
            result = _get_queue_path(12345)

        assert result == tmp_path / "pull-request-review" / "PR12345" / "queue.json"
        # warn=False: no warning emitted
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_normalizes_non_str_commit_hash_to_str(self, tmp_path):
        """Should coerce a valid non-str value (e.g., int) to str without raising TypeError."""
        with (
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_state_dir",
                return_value=tmp_path,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_value",
                # Return an integer that would pass is_safe_dir_segment(str(...))
                side_effect=lambda key, *a, **kw: 12345678 if key == "review.commit_hash_short" else None,
            ),
        ):
            # Should not raise TypeError
            result = _get_queue_path(99)

        assert result == tmp_path / "pull-request-review" / "12345678" / "queue.json"

    def test_falls_back_to_legacy_path_when_new_path_missing(self, tmp_path):
        """Should use legacy queue path when new path absent but legacy exists."""
        # Create the legacy queue file but NOT the new-format file
        legacy_dir = tmp_path / "pull-request-review" / "prompts" / "12345"
        legacy_dir.mkdir(parents=True)
        legacy_queue = legacy_dir / "queue.json"
        legacy_queue.write_text("{}")

        with (
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_state_dir",
                return_value=tmp_path,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_value",
                return_value="abc12345",
            ),
        ):
            result = _get_queue_path(12345)

        assert result == legacy_queue

    def test_prefers_new_path_when_both_exist(self, tmp_path):
        """Should use new commit-hash-scoped path when it exists, even if legacy also exists."""
        # Create both new and legacy queue files
        new_dir = tmp_path / "pull-request-review" / "abc12345"
        new_dir.mkdir(parents=True)
        new_queue = new_dir / "queue.json"
        new_queue.write_text("{}")

        legacy_dir = tmp_path / "pull-request-review" / "prompts" / "12345"
        legacy_dir.mkdir(parents=True)
        legacy_queue = legacy_dir / "queue.json"
        legacy_queue.write_text("{}")

        with (
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_state_dir",
                return_value=tmp_path,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_value",
                return_value="abc12345",
            ),
        ):
            result = _get_queue_path(12345)

        assert result == new_queue

    def test_returns_new_path_when_neither_exist(self, tmp_path):
        """Should return the new path (not legacy) when neither file exists yet."""
        with (
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_state_dir",
                return_value=tmp_path,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_value",
                return_value="abc12345",
            ),
        ):
            result = _get_queue_path(12345)

        assert result == tmp_path / "pull-request-review" / "abc12345" / "queue.json"
