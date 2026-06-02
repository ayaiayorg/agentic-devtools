"""Tests for segments_clean_command."""

from unittest.mock import patch

from agentic_devtools.cli.segments.commands import segments_clean_command
from agentic_devtools.segments import manager as mgr_module
from agentic_devtools.segments.cleanup import CleanupResult
from agentic_devtools.segments.manager import create_segment


class TestSegmentsCleanCommand:
    """Tests for segments_clean_command function."""

    def test_runs_cleanup(self, tmp_path, capsys):
        """Prints cleanup results."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            # Create segment — it will be "retained" since it's active and alive
            create_segment("w1")
            with patch("agentic_devtools.segments.cleanup._is_owner_alive", return_value=True):
                segments_clean_command()
            captured = capsys.readouterr()
            assert "Removed:" in captured.out
            assert "Retained:" in captured.out

    def test_empty_directory(self, tmp_path, capsys):
        """Works with no segments."""
        with patch.object(mgr_module, "get_state_dir", return_value=tmp_path):
            segments_clean_command()
            captured = capsys.readouterr()
            assert "Removed:  0" in captured.out

    def test_prints_orphans_and_errors(self, capsys):
        """Prints orphan IDs and errors when present."""
        result = CleanupResult(
            removed_count=1,
            retained_count=2,
            orphaned_count=1,
            orphan_segment_ids=["seg-123"],
            errors=["boom"],
        )
        with patch("agentic_devtools.cli.segments.commands.cleanup_segments", return_value=result):
            segments_clean_command()
        captured = capsys.readouterr()
        assert "Orphaned segments" in captured.out
        assert "seg-123" in captured.out
        assert "Errors:" in captured.err
        assert "boom" in captured.err
